"""Per-user versioned installation with rollback and recoverable removal.

No services, provider configuration, browser profiles or evidence are touched.
Callers must explicitly select detected browsers before install/repair.
"""
import json
import os
from pathlib import Path
import platform
import shutil
import uuid
import threading
import time
import re
from functools import wraps
from .locking import installation_lock
from .bundle import verify_bundle, digest
from .manifests import manifest, manifest_path, validate_release
from .registration import Registration, atomic_json
from .package_policy import validate_package
from .maintenance import Maintenance
from .extension_pair import ExtensionPair


def default_root():
    if platform.system() == 'Windows':
        return Path(os.environ['LOCALAPPDATA']) / 'CueFlora'
    if platform.system() == 'Darwin':
        return Path.home() / 'Library/Application Support/CueFlora'
    return Path.home() / '.local/share/CueFlora'


def serialized(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self._thread_lock:
            return locked(self, *args, **kwargs)

    def locked(self, *args, **kwargs):
        self._safe_path(self.root / '.setup.lock')
        self._safe_path(self.root / 'pending-activation.json')
        if self._lock_depth:
            return method(self, *args, **kwargs)
        # Check ownership before creating even the lock file.
        if not (self.root / 'pending-activation.json').exists():
            self.state()
        from cueflora_host.activity import activity_gate,assert_no_native_jobs
        with installation_lock(self.root), activity_gate(self.root,install=True):
            assert_no_native_jobs(self.root)
            self._lock_depth += 1
            try:
                return method(self, *args, **kwargs)
            finally:
                self._lock_depth -= 1
    return call


class Setup:
    def __init__(self, root=None, home=None, system=None, registration=None, maintenance=None):
        self.root = Path(root or default_root()).absolute()
        self.home = Path(home or Path.home()).resolve()
        self.system = system or platform.system()
        if self.root.name != 'CueFlora' or self.root.is_symlink() or self.root.resolve() != self.root:
            raise ValueError('Expected a non-linked dedicated CueFlora install directory')
        self.registration = registration or Registration(self.system)
        self.maintenance = maintenance or Maintenance(self.home, self.system)
        self.state_path = self.root / 'setup-state.json'
        self._lock_depth = 0
        self._thread_lock = threading.RLock()
        self.extensions = ExtensionPair(self.root)

    def _safe_path(self, path):
        if path.is_symlink() or path.resolve() != path:
            raise ValueError('Linked Setup path rejected')
        return path

    def _rename_owned_directory(self, source, destination):
        # Windows can temporarily lock recently copied/executed payload files.
        # Retry only this local rename, never installation, registration or AI.
        for attempt in range(21):
            if source.parent != self.root or destination.parent != self.root:
                raise ValueError('Rename must remain within the owned install root')
            self._safe_path(source)
            self._safe_path(destination)
            if destination.exists():
                raise FileExistsError('Quarantine/recovery destination already exists')
            try:
                return source.rename(destination)
            except OSError as error:
                if self.system != 'Windows' or getattr(error, 'winerror', None) not in (5, 32, 33) or attempt == 20:
                    raise
                time.sleep(0.5)

    def _validate_state(self, state):
        if not isinstance(state, dict) or state.get('schema') != 1 or state.get('owner') != 'CueFlora Setup':
            raise ValueError('Invalid installation ownership record')
        validate_release(state.get('release'))
        browsers = state.get('browsers')
        if not isinstance(browsers, list) or any(b not in ('chrome', 'firefox') for b in browsers) or len(set(browsers)) != len(browsers):
            raise ValueError('Invalid installed browser selection')
        for key in ('current', 'previous'):
            if key not in state:
                raise ValueError('Missing installed version reference')
            if state[key] is not None:
                self._version(state[key])
        for key in ('maintenance', 'previousMaintenance'):
            if state.get(key) is not None:
                self._validate_maintenance(state[key])
        for key in ('extension','previousExtension'):
            if state.get(key) is not None:self.extensions.source(state[key])
        return state

    def _launcher(self, identifier):
        self._version(identifier)  # Reuse strict version-name validation.
        return self._safe_path(self.root / 'maintenance' / identifier / 'CueFlora Setup.exe')

    def _validate_maintenance(self, value):
        if not isinstance(value, dict) or set(value) != {'launcher', 'sha256', 'shortcutSha256'}:
            raise ValueError('Invalid maintenance ownership record')
        self._launcher(value['launcher'])
        for key in ('sha256', 'shortcutSha256'):
            if not isinstance(value[key], str) or len(value[key]) != 64 or any(c not in '0123456789abcdef' for c in value[key]):
                raise ValueError('Invalid maintenance ownership hash')
        return value

    def state(self):
        self._safe_path(self.state_path)
        if not self.state_path.exists():
            if self.root.exists() and any(path.name not in ('.setup.lock','.activity.lock') for path in self.root.iterdir()):
                raise ValueError('Unowned installation directory; refusing to modify it')
            return None
        state = json.loads(self.state_path.read_text(encoding='utf-8'))
        return self._validate_state(state)

    def _version(self, identifier):
        if not isinstance(identifier, str) or len(identifier) != 32 or any(c not in '0123456789abcdef' for c in identifier):
            raise ValueError('Invalid installed version reference')
        path = self.root / 'versions' / identifier
        if path.resolve() != path:
            raise ValueError('Linked installation path rejected')
        return path

    def _activate(self, identifier, release, browsers, previous, maintenance=None, extension=None, previous_extension=None, extension_change=None):
        folder = self._version(identifier)
        metadata = verify_bundle(folder)
        if release.get('mode') in ('private', 'public'):
            validate_package(folder, release, metadata, browsers)
        if release.get('extensionInventorySha256'):
            from .extension_pair import verify_extension
            if extension is None:raise ValueError('Matching extension/helper pair is required')
            ext,_=verify_extension(self.extensions.source(extension),release['extensionInventorySha256'])
            if ext['version']!=metadata['hostVersion'] or ext['chromeId']!=release['extensionIds']['chrome']:raise ValueError('Activation pair identity/version mismatch')
        executable = folder / ('cueflora-host.exe' if self.system == 'Windows' else 'cueflora-host')
        if not executable.is_file():
            raise ValueError('Native host executable missing')
        changes = []
        for browser in browsers:
            path = self._safe_path(manifest_path(browser, self.system, self.home, self.root))
            pointer = self.registration.read_pointer(browser)
            if pointer and Path(pointer) != path:
                raise ValueError('Existing browser registration belongs to another installation')
            old = path.read_bytes() if path.exists() else None
            if old:
                existing = json.loads(old)
                old_host = Path(existing.get('path', '')).resolve()
                if not old_host.is_relative_to(self.root / 'versions'):
                    raise ValueError('Existing native manifest is not owned by this installation')
            changes.append((browser, path, old, pointer, manifest(browser, executable, release)))
        # The journal is persisted before any external registration mutation.
        journal = {'schema': 1, 'previousState': previous, 'changes': [
            {'browser': b, 'old': old.decode('utf-8') if old else None, 'pointer': pointer}
            for b, _, old, pointer, _ in changes]}
        if extension is not None or previous.get('extension') is not None:
            journal['extension'] = extension_change or self.extensions.change(extension,previous.get('extension'))
            self.extensions.validate_change(journal['extension'])
        shortcut = None
        if maintenance or previous.get('maintenance'):
            launcher = self._launcher(maintenance['launcher']) if maintenance else None
            if maintenance and (not launcher.is_file() or digest(launcher) != maintenance['sha256']):
                raise ValueError('Maintenance launcher missing or modified')
            maintenance, shortcut, journal['maintenance'] = self.maintenance.prepare(previous.get('maintenance'), maintenance, launcher)
        atomic_json(self.root / 'pending-activation.json', journal)
        try:
            if 'extension' in journal:self.extensions.apply(journal['extension'])
            for browser, path, _, _, value in changes:
                atomic_json(path, value)
                self.registration.write_pointer(browser, path)
            if 'maintenance' in journal:
                self.maintenance.write(shortcut)
            state = {'schema': 1, 'owner': 'CueFlora Setup', 'current': identifier,
                     'previous': previous.get('current') if previous else None,
                     'release': release, 'previousRelease': previous.get('release') if previous else None,
                     'browsers': list(browsers), 'hostVersion': metadata.get('hostVersion'),
                     'maintenance': maintenance, 'previousMaintenance': previous.get('maintenance')}
            if 'extension' in journal:
                state['extension']=extension
                state['previousExtension']=previous_extension or previous.get('extension')
            atomic_json(self.state_path, state)
        except Exception:
            self.recover()
            raise
        (self.root / 'pending-activation.json').unlink()
        return state

    @serialized
    def recover(self):
        path = self.root / 'pending-activation.json'
        if not path.exists():
            return
        journal = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(journal, dict) or journal.get('schema') != 1:
            raise ValueError('Invalid recovery journal')
        previous = journal.get('previousState')
        if previous is None:
            raise ValueError('Recovery journal lacks ownership record')
        self._validate_state(previous)
        changes = journal.get('changes')
        if not isinstance(changes, list) or len(changes) > 2:
            raise ValueError('Invalid recovery changes')
        seen = set()
        # Validate the entire transaction before restoring even its first entry.
        for change in changes:
            if not isinstance(change, dict) or change.get('browser') not in ('chrome', 'firefox'):
                raise ValueError('Invalid recovery browser')
            browser = change['browser']
            if browser in seen:
                raise ValueError('Duplicate recovery browser')
            seen.add(browser)
            target = self._safe_path(manifest_path(browser, self.system, self.home, self.root))
            for pointer in (change.get('pointer'), self.registration.read_pointer(browser)):
                if pointer is not None and (not isinstance(pointer, str) or Path(pointer) != target):
                    raise ValueError('Foreign recovery registration')
            if 'old' not in change:
                raise ValueError('Missing recovery manifest')
            values = [change['old']]
            if target.exists():
                values.append(target.read_text(encoding='utf-8'))
            for raw in values:
                if raw is not None:
                    value = json.loads(raw)
                    host = Path(value.get('path', '')) if isinstance(value, dict) else Path()
                    if not host.is_absolute() or not host.resolve().is_relative_to(self.root / 'versions'):
                        raise ValueError('Foreign recovery manifest')
        removed_name = journal.get('movedVersions')
        shortcut = None
        if 'extension' in journal:self.extensions.validate_change(journal['extension'])
        if 'maintenance' in journal:
            shortcut = self.maintenance.validate_recovery(journal['maintenance'], previous.get('maintenance'))
        if removed_name:
            if not isinstance(removed_name, str) or not removed_name.startswith('removed-') or len(removed_name) != 40 or any(c not in '0123456789abcdef' for c in removed_name[8:]):
                raise ValueError('Invalid uninstall recovery location')
            removed = self.root / removed_name
            self._safe_path(removed)
            self._safe_path(self.root / 'versions')
            if removed.exists() and not (self.root / 'versions').exists():
                self._rename_owned_directory(removed, self.root / 'versions')
        if 'extension' in journal:self.extensions.recover(journal['extension'])
        for change in reversed(journal['changes']):
            target = manifest_path(change['browser'], self.system, self.home, self.root)
            if change['old'] is None:
                target.unlink(missing_ok=True)
            else:
                atomic_json(target, json.loads(change['old']))
            self.registration.write_pointer(change['browser'], change['pointer'])
        if 'maintenance' in journal:
            self.maintenance.write(shortcut)
        if journal['previousState'] is not None:
            atomic_json(self.state_path, journal['previousState'])
        else:
            self.state_path.unlink(missing_ok=True)
        path.unlink()

    @serialized
    def install(self, payload, release, browsers, *, allow_prototype=False, launcher=None, extension=None, adopt_extension=None, confirm_adoption=False):
        validate_release(release)
        browsers = sorted(set(browsers))
        if not browsers or any(browser not in ('chrome', 'firefox') for browser in browsers):
            raise ValueError('Select supported browsers explicitly')
        self.recover()
        previous = self.state()
        if previous and set(previous['browsers']) - set(browsers):
            raise ValueError('Upgrade must retain previously registered browsers; uninstall to change selection')
        metadata = verify_bundle(payload)
        if previous and previous.get('current') and previous.get('hostVersion'):
            from cueflora_host.updates import version
            if re.fullmatch(r'\d+\.\d+\.\d+',str(metadata.get('hostVersion',''))) and re.fullmatch(r'\d+\.\d+\.\d+',str(previous['hostVersion'])):
                if version(metadata['hostVersion']) < version(previous['hostVersion']):raise ValueError('Incompatible downgrade refused. Use a compatible paired rollback instead.')
            elif release.get('extensionInventorySha256') or previous.get('extension'):raise ValueError('Paired installation requires exact semantic versions')
        validate_package(payload, release, metadata, browsers, allow_prototype)
        if previous and previous['browsers'] and any(previous['release']['extensionIds'][b] != release['extensionIds'].get(b) for b in previous['browsers']):
            raise ValueError('Upgrade cannot change installed browser identities')
        if metadata.get('platform') != self.system:
            raise ValueError('Runtime platform does not match this computer')
        if metadata.get('architecture', '').lower() != platform.machine().lower():
            raise ValueError('Runtime architecture does not match this computer')
        if release.get('extensionInventorySha256') and extension is None:raise ValueError('Matching bundled Chrome extension required for this release')
        if previous and previous.get('extension') and extension is None:raise ValueError('Upgrade must retain the managed extension/helper pair')
        if extension is not None and previous and previous.get('current') and not previous.get('extension') and adopt_extension is None:
            raise ValueError('Select the currently loaded CueFlora extension folder for this one-time upgrade. Setup does not inspect Chrome profiles or remove the extension.')
        identifier = uuid.uuid4().hex
        folder = self._version(identifier)
        folder.parent.mkdir(parents=True, exist_ok=True)
        if previous is None:
            previous = {'schema': 1, 'owner': 'CueFlora Setup', 'current': None,
                        'previous': None, 'release': release, 'browsers': []}
            atomic_json(self.state_path, previous)
        shutil.copytree(payload, folder, symlinks=False)
        verify_bundle(folder)
        # Ensure the exact inventory did not change while copying.
        if digest(Path(payload) / 'runtime-manifest.json') != digest(folder / 'runtime-manifest.json'):
            raise ValueError('Payload changed during installation')
        maintenance = previous.get('maintenance')
        if launcher is not None:
            launcher = Path(launcher).absolute()
            if launcher.is_symlink() or launcher.resolve() != launcher or not launcher.is_file():
                raise ValueError('Invalid maintenance launcher source')
            target = self._launcher(identifier)
            target.parent.mkdir(parents=True, exist_ok=False)
            shutil.copy2(launcher, target)
            if digest(launcher) != digest(target):
                raise ValueError('Maintenance launcher changed during copy')
            maintenance = {'launcher': identifier, 'sha256': digest(target), 'shortcutSha256': '0' * 64}
        extension_record=old_extension=extension_change=None
        if extension is not None:
            extension_record,old_extension,extension_change=self.extensions.prepare(extension,release,previous.get('extension'),adopt_extension,confirm_adoption)
        return self._activate(identifier, release, browsers, previous, maintenance,extension_record,old_extension,extension_change)

    @serialized
    def repair(self, payload, *, allow_prototype=False, launcher=None, extension=None):
        self.recover()
        state = self.state()
        if not state:
            raise ValueError('No installation to repair')
        return self.install(payload, state['release'], state['browsers'], allow_prototype=allow_prototype, launcher=launcher,extension=extension)

    @serialized
    def rollback(self):
        self.recover()
        state = self.state()
        if not state or not state.get('previous'):
            raise ValueError('No previous runtime to restore')
        if state.get('extension') and not state.get('previousExtension'):raise ValueError('No compatible previous extension/helper pair is available')
        if state.get('previousExtension'):
            from cueflora_host.updates import version
            if version(state['previousExtension']['version']) < (0,2,0):raise ValueError('Rollback to 0.1.x cannot safely read 0.2 account settings. The recoverable files are preserved; downgrade refused.')
        return self._activate(state['previous'], state.get('previousRelease') or state['release'], state['browsers'], state, state.get('previousMaintenance'),state.get('previousExtension'))

    @serialized
    def uninstall(self):
        self.recover()
        state = self.state()
        if not state:
            raise ValueError('No owned installation')
        # Preflight every target before changing any registration.
        targets = []
        for browser in state['browsers']:
            path = self._safe_path(manifest_path(browser, self.system, self.home, self.root))
            pointer = self.registration.read_pointer(browser)
            if pointer and Path(pointer) != path:
                raise ValueError('Browser registration has changed; refusing removal')
            if path.exists():
                value = json.loads(path.read_text(encoding='utf-8'))
                if not Path(value['path']).resolve().is_relative_to(self.root / 'versions'):
                    raise ValueError('Manifest is no longer owned by this installation')
            targets.append((browser, path))
        removed = self.root / ('removed-' + uuid.uuid4().hex)
        journal = {'schema': 1, 'previousState': state, 'movedVersions': removed.name, 'changes': [
            {'browser': browser, 'old': path.read_text(encoding='utf-8') if path.exists() else None,
             'pointer': self.registration.read_pointer(browser)} for browser, path in targets]}
        if state.get('maintenance'):
            _, _, journal['maintenance'] = self.maintenance.prepare(state['maintenance'], None, None)
        if state.get('extension'):journal['extension']=self.extensions.change(None,state['extension'])
        atomic_json(self.root / 'pending-activation.json', journal)
        try:
            if 'extension' in journal:self.extensions.apply(journal['extension'])
            for browser, path in targets:
                self.registration.write_pointer(browser, None)
                path.unlink(missing_ok=True)
            if 'maintenance' in journal:
                self.maintenance.write(None)
            # Keep the locked root in place. Only owned version directories move.
            versions = self.root / 'versions'
            self._rename_owned_directory(versions, removed)
            atomic_json(self.state_path, {**state, 'current': None, 'previous': None, 'browsers': [],
                                         'maintenance': None, 'previousMaintenance': None, 'removedTo': str(removed),
                                         'extension':None,'previousExtension':None,
                                         'removedExtensionTo':journal.get('extension',{}).get('backup')})
        except Exception:
            if 'removed' in locals() and removed.exists() and not (self.root / 'versions').exists():
                self._rename_owned_directory(removed, self.root / 'versions')
            self.recover()
            raise
        (self.root / 'pending-activation.json').unlink()
        return removed
