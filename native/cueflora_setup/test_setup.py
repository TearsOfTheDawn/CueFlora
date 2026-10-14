import json
from pathlib import Path
import platform
import tempfile
import unittest
from unittest.mock import patch
from .bundle import digest, verify_bundle
from .engine import Setup
from .manifests import manifest


class FakeRegistration:
    def __init__(self):
        self.values = {}
        self.fail_once = False

    def read_pointer(self, browser):
        return self.values.get(browser)

    def write_pointer(self, browser, path):
        if self.fail_once:
            self.fail_once = False
            raise OSError('Injected registration failure')
        self.values[browser] = str(path) if path else None


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cueflora-setup-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.payload = self.base / 'payload'
        self.payload.mkdir()
        (self.payload / 'cueflora-host.exe').write_bytes(b'fixture-not-executable')
        (self.payload / 'runtime-manifest.json').write_text(json.dumps({'schema': 1, 'prototype': True,
            'platform': 'Windows', 'architecture': platform.machine(), 'hostVersion': 'test',
            'files': {'cueflora-host.exe': digest(self.payload / 'cueflora-host.exe')}}))
        self.release = {'owner': 'Test only', 'extensionIds': {'chrome': 'a' * 32, 'firefox': 'test@example.invalid'}}
        self.registration = FakeRegistration()
        self.setup = Setup(self.base / 'CueFlora', self.base, 'Windows', self.registration)

    def install(self):
        return self.setup.install(self.payload, self.release, ['chrome','firefox'], allow_prototype=True)

    def private_config(self):
        return {'owner': 'Private local installation', 'mode': 'private',
                'extensionIds': {'chrome': 'b'*32},
                'runtimeInventorySha256': digest(self.payload / 'runtime-manifest.json'),
                'publicReleaseAuthorized': False, 'redistributionApproved': False}

    def test_private_chrome_lifecycle_without_override(self):
        config = self.private_config()
        first = self.setup.install(self.payload, config, ['chrome'])
        inventory = self.payload / 'runtime-manifest.json'
        inventory.write_text(json.dumps({**json.loads(inventory.read_text()), 'hostVersion': 'second'}))
        second = self.setup.install(self.payload, self.private_config(), ['chrome'])
        self.assertNotEqual(first['current'], second['current'])
        rolled = self.setup.rollback()
        self.assertEqual(rolled['release'], config)
        restored = self.setup.rollback()
        self.assertEqual(restored['current'], second['current'])
        repaired = self.setup.repair(self.payload)
        self.assertEqual(repaired['release']['extensionIds'], config['extensionIds'])
        self.assertTrue(self.setup.uninstall().exists())

    def test_private_rejects_binding_selection_mode_and_identity_changes(self):
        config = self.private_config()
        for invalid, browsers in [({**config, 'runtimeInventorySha256': 'a'*64}, ['chrome']),
                                  (config, ['firefox']), ({**config, 'mode': 'unknown'}, ['chrome']),
                                  ({**config, 'publicReleaseAuthorized': True}, ['chrome'])]:
            with self.assertRaises(ValueError):
                self.setup.install(self.payload, invalid, browsers)
        self.setup.install(self.payload, config, ['chrome'])
        with self.assertRaises(ValueError):
            self.setup.install(self.payload, {**config, 'extensionIds': {'chrome': 'a'*32}}, ['chrome'])

    def test_private_failure_recovers_without_override(self):
        config = self.private_config()
        first = self.setup.install(self.payload, config, ['chrome'])
        self.registration.fail_once = True
        with self.assertRaises(OSError):
            self.setup.install(self.payload, config, ['chrome'])
        self.assertEqual(self.setup.state()['current'], first['current'])

    def test_private_cli_install_and_repair_without_override(self):
        from unittest.mock import patch
        from .cli import main
        config = self.base / 'release.json'
        config.write_text(json.dumps(self.private_config()))
        with patch('cueflora_setup.cli.Setup', return_value=self.setup), patch('cueflora_setup.cli.detected_browsers', return_value=['chrome']), patch('builtins.print'):
            main(['install', '--payload', str(self.payload), '--release', str(config), '--browser', 'chrome', '--apply'])
            main(['repair', '--payload', str(self.payload), '--apply'])
        self.assertEqual(self.setup.state()['browsers'], ['chrome'])

    def test_install_upgrade_rollback_and_recoverable_uninstall(self):
        first = self.install()
        second = self.install()
        self.assertNotEqual(first['current'], second['current'])
        self.assertEqual(self.setup.rollback()['current'], first['current'])
        removed = self.setup.uninstall()
        self.assertTrue(removed.exists())
        self.assertIsNone(self.setup.state()['current'])
        self.assertTrue(all(value is None for value in self.registration.values.values()))

    def test_registration_failure_restores_previous_install(self):
        first = self.install()
        pointers = dict(self.registration.values)
        self.registration.fail_once = True
        with self.assertRaises(OSError):
            self.install()
        self.assertEqual(self.setup.state()['current'], first['current'])
        self.assertEqual(self.registration.values, pointers)

    def test_repair_replaces_corrupt_runtime_from_valid_payload(self):
        first = self.install()
        (self.setup._version(first['current']) / 'cueflora-host.exe').write_bytes(b'corrupt')
        repaired = self.setup.repair(self.payload, allow_prototype=True)
        verify_bundle(self.setup._version(repaired['current']))

    def test_rejects_tampering_and_prototype_without_opt_in(self):
        with self.assertRaises(ValueError):
            self.setup.install(self.payload, self.release, ['chrome'])
        (self.payload / 'extra').write_text('unexpected')
        with self.assertRaises(ValueError):
            self.install()

    def test_preserves_conflicting_registration(self):
        self.registration.values['chrome'] = str(self.base / 'other.json')
        with self.assertRaises(ValueError):
            self.install()
        self.assertEqual(self.registration.values['chrome'], str(self.base / 'other.json'))

    def test_nested_manifest_is_not_exempt_from_inventory(self):
        nested = self.payload / 'nested'
        nested.mkdir()
        (nested / 'runtime-manifest.json').write_text('unlisted')
        with self.assertRaises(ValueError):
            verify_bundle(self.payload)

    def test_rejects_noncanonical_inventory_paths_and_invalid_hashes(self):
        inventory = self.payload / 'runtime-manifest.json'
        original = json.loads(inventory.read_text())
        for name, checksum in [('./cueflora-host.exe', original['files']['cueflora-host.exe']),
                               ('nested//file', 'a' * 64), ('.', 'a' * 64),
                               ('cueflora-host.exe', 'invalid')]:
            with self.subTest(name=name, checksum=checksum):
                inventory.write_text(json.dumps({**original, 'files': {name: checksum}}))
                with self.assertRaises(ValueError):
                    verify_bundle(self.payload)

    def test_first_failed_install_can_be_retried(self):
        self.registration.fail_once = True
        with self.assertRaises(OSError):
            self.install()
        self.assertIsNone(self.setup.state()['current'])
        self.assertIsNotNone(self.install()['current'])

    def test_uninstall_failure_restores_registration(self):
        first = self.install()
        self.registration.fail_once = True
        with self.assertRaises(OSError):
            self.setup.uninstall()
        self.assertEqual(self.setup.state()['current'], first['current'])
        verify_bundle(self.setup._version(first['current']))

    def test_transient_windows_quarantine_lock_retries_only_rename(self):
        self.install()
        original = Path.rename
        attempts = []
        def transient(path, target):
            attempts.append(path)
            if len(attempts) <= 2:
                error = PermissionError('fixture transient lock'); error.winerror = 5
                raise error
            return original(path, target)
        with patch.object(Path, 'rename', transient), patch('cueflora_setup.engine.time.sleep') as sleep:
            quarantine = self.setup.uninstall()
        self.assertEqual(len(attempts), 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertTrue(quarantine.is_dir())
        self.assertIsNone(self.setup.state()['current'])

    def test_permanent_windows_lock_is_bounded_and_restores_registration(self):
        first = self.install()
        error = PermissionError('fixture permanent lock'); error.winerror = 32
        with patch.object(Path, 'rename', side_effect=error) as rename, patch('cueflora_setup.engine.time.sleep') as sleep:
            with self.assertRaises(PermissionError): self.setup.uninstall()
        self.assertEqual(rename.call_count, 21)
        self.assertEqual(sleep.call_count, 20)
        self.assertEqual(self.setup.state()['current'], first['current'])
        self.assertTrue(all(self.registration.values.values()))
        verify_bundle(self.setup._version(first['current']))

    def test_other_errors_and_foreign_destinations_are_not_retried(self):
        self.install()
        error = PermissionError('fixture nontransient error'); error.winerror = 123
        with patch.object(Path, 'rename', side_effect=error) as rename, patch('cueflora_setup.engine.time.sleep') as sleep:
            with self.assertRaises(PermissionError): self.setup.uninstall()
        self.assertEqual(rename.call_count, 1); sleep.assert_not_called()
        foreign = self.setup.root / 'existing'; foreign.mkdir()
        with self.assertRaises(FileExistsError): self.setup._rename_owned_directory(self.setup.root/'versions', foreign)
        with self.assertRaises(ValueError): self.setup._rename_owned_directory(self.setup.root/'versions', self.base/'foreign')

    def test_crash_after_quarantine_is_recoverable(self):
        first = self.install()
        removed_name = 'removed-' + 'a'*32
        journal = {'schema': 1, 'previousState': first, 'changes': [], 'movedVersions': removed_name}
        (self.setup.root / 'pending-activation.json').write_text(json.dumps(journal))
        (self.setup.root / 'versions').rename(self.setup.root / removed_name)
        self.setup.recover()
        verify_bundle(self.setup._version(first['current']))

    def test_concurrent_setup_is_rejected_by_os_lock(self):
        from .locking import installation_lock
        with installation_lock(self.setup.root):
            other = Setup(self.setup.root, self.base, 'Windows', self.registration)
            with self.assertRaises(OSError):
                other.install(self.payload, self.release, ['chrome'], allow_prototype=True)

    def test_invalid_journal_does_not_partially_restore(self):
        first = self.install()
        from .manifests import manifest_path
        target = manifest_path('chrome', 'Windows', self.base, self.setup.root)
        before = target.read_bytes()
        pointers = dict(self.registration.values)
        journal = {'schema': 1, 'previousState': first, 'changes': [
            {'browser': 'firefox', 'old': None, 'pointer': str(self.base / 'foreign.json')},
            {'browser': 'chrome', 'old': None, 'pointer': None}]}
        (self.setup.root / 'pending-activation.json').write_text(json.dumps(journal))
        with self.assertRaises(ValueError):
            self.setup.recover()
        self.assertEqual(target.read_bytes(), before)
        self.assertEqual(self.registration.values, pointers)

    def test_corrupt_state_is_rejected_before_uninstall(self):
        first = self.install()
        pointers = dict(self.registration.values)
        self.setup.state_path.write_text(json.dumps({**first, 'current': '../foreign'}))
        with self.assertRaises(ValueError):
            self.setup.uninstall()
        self.assertEqual(self.registration.values, pointers)

    def test_manifest_has_exact_identity_and_absolute_path(self):
        value = manifest('chrome', self.payload / 'cueflora-host.exe', self.release)
        self.assertEqual(value['allowed_origins'], ['chrome-extension://' + 'a'*32 + '/'])
        self.assertNotIn('allowed_extensions', value)
        with self.assertRaises(ValueError):
            manifest('firefox', Path('relative'), self.release)

    def test_manifest_paths_are_per_user_for_each_supported_os(self):
        from .manifests import manifest_path
        expected = {
            ('Windows', 'chrome'): self.setup.root / 'manifests/chrome.json',
            ('Windows', 'firefox'): self.setup.root / 'manifests/firefox.json',
            ('Darwin', 'chrome'): self.base / 'Library/Application Support/Google/Chrome/NativeMessagingHosts/cueflora_host.json',
            ('Darwin', 'firefox'): self.base / 'Library/Application Support/Mozilla/NativeMessagingHosts/cueflora_host.json',
            ('Linux', 'chrome'): self.base / '.config/google-chrome/NativeMessagingHosts/cueflora_host.json',
            ('Linux', 'firefox'): self.base / '.mozilla/native-messaging-hosts/cueflora_host.json',
        }
        for (system, browser), target in expected.items():
            self.assertEqual(manifest_path(browser, system, self.base, self.setup.root), target)
        with self.assertRaises(ValueError):
            manifest_path('safari', 'Darwin', self.base, self.setup.root)

    def test_malformed_identity_types_and_guids_fail_cleanly(self):
        from .manifests import validate_release
        for browser in ('chrome', 'firefox'):
            for value in (None, 12, [], {}, '', '{' + '-' * 36 + '}'):
                with self.subTest(browser=browser, value=value):
                    with self.assertRaises(ValueError):
                        validate_release({**self.release, 'extensionIds': {**self.release['extensionIds'], browser: value}})

    def test_linked_payload_entry_is_rejected_without_touching_target(self):
        sentinel = self.base / 'outside'
        sentinel.write_bytes(b'preserve')
        link = self.payload / 'linked'
        try:
            link.symlink_to(sentinel)
        except OSError as error:
            if getattr(error, 'winerror', None) == 1314:
                self.skipTest('Windows symlink privilege unavailable')
            raise
        with self.assertRaises(ValueError):
            verify_bundle(self.payload)
        self.assertEqual(sentinel.read_bytes(), b'preserve')

    def test_linked_state_is_rejected_without_touching_target(self):
        first = self.install()
        sentinel = self.base / 'outside-state.json'
        sentinel.write_text(json.dumps(first))
        before = sentinel.read_bytes()
        self.setup.state_path.unlink()
        try:
            self.setup.state_path.symlink_to(sentinel)
        except OSError as error:
            if getattr(error, 'winerror', None) == 1314:
                self.skipTest('Windows symlink privilege unavailable')
            raise
        with self.assertRaises(ValueError):
            self.setup.uninstall()
        self.assertEqual(sentinel.read_bytes(), before)
