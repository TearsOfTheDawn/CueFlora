"""An owned, per-user Start Menu shortcut; no persistent process."""
import base64
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import uuid


def checksum(data):
    return hashlib.sha256(data).hexdigest()


def atomic_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('xb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class Maintenance:
    def __init__(self, home, system):
        self.system = system
        self.path = Path(home) / 'AppData/Roaming/Microsoft/Windows/Start Menu/Programs/CueFlora Setup.lnk'

    def safe_path(self):
        if self.path.is_symlink() or self.path.resolve() != self.path:
            raise ValueError('Linked maintenance shortcut rejected')
        return self.path

    def build(self, launcher):
        if self.system != 'Windows':
            raise ValueError('Maintenance launcher is currently Windows-only')
        with tempfile.TemporaryDirectory(prefix='cueflora-shortcut-') as directory:
            temporary = Path(directory) / 'CueFlora Setup.lnk'
            environment = {**os.environ, 'CUEFLORA_SHORTCUT': str(temporary), 'CUEFLORA_LAUNCHER': str(launcher)}
            # Paths are data, never interpolated into executable shell text.
            command = "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:CUEFLORA_SHORTCUT);$s.TargetPath=$env:CUEFLORA_LAUNCHER;$s.WorkingDirectory=[IO.Path]::GetDirectoryName($env:CUEFLORA_LAUNCHER);$s.Description='CueFlora Setup and maintenance';$s.Save()"
            subprocess.run([str(Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'),
                            '-NoProfile', '-NonInteractive', '-WindowStyle', 'Hidden', '-Command', command],
                           env=environment, check=True, timeout=30, capture_output=True)
            data = temporary.read_bytes()
            if not data or len(data) > 65536:
                raise ValueError('Invalid maintenance shortcut')
            return data

    def prepare(self, old, new, launcher):
        path = self.safe_path()
        if path.exists() and path.stat().st_size > 65536:
            raise ValueError('Oversized maintenance shortcut rejected')
        existing = path.read_bytes() if path.exists() else None
        if existing is not None and (old is None or checksum(existing) != old['shortcutSha256']):
            raise ValueError('Existing Start Menu entry is not owned by this installation')
        data = self.build(launcher) if new else None
        if new:
            new = {**new, 'shortcutSha256': checksum(data)}
        return new, data, {'old': base64.b64encode(existing).decode('ascii') if existing is not None else None,
                           'newSha256': checksum(data) if data is not None else None}

    def validate_recovery(self, change, previous):
        if not isinstance(change, dict) or set(change) != {'old', 'newSha256'}:
            raise ValueError('Invalid maintenance recovery record')
        old = change['old']
        if old is not None and (not isinstance(old, str) or len(old) > 90000):
            raise ValueError('Invalid maintenance recovery bytes')
        try:
            data = base64.b64decode(old, validate=True) if old is not None else None
        except (ValueError, TypeError) as error:
            raise ValueError('Invalid maintenance recovery bytes') from error
        if data is not None and (not data or len(data) > 65536 or previous is None or checksum(data) != previous['shortcutSha256']):
            raise ValueError('Foreign maintenance recovery bytes')
        expected = change['newSha256']
        if expected is not None and (not isinstance(expected, str) or len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected)):
            raise ValueError('Invalid maintenance recovery hash')
        path = self.safe_path()
        if path.exists() and path.stat().st_size > 65536:
            raise ValueError('Oversized maintenance recovery shortcut rejected')
        if path.exists() and checksum(path.read_bytes()) not in {expected, checksum(data) if data is not None else None}:
            raise ValueError('Start Menu entry changed; refusing recovery')
        return data

    def write(self, data):
        path = self.safe_path()
        if data is None:
            path.unlink(missing_ok=True)
        else:
            atomic_bytes(path, data)
