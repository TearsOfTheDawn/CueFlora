"""Registration adapter. Constructing an adapter does not change browser state."""
import json
import os
from pathlib import Path
import uuid
from .manifests import REGISTRY


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


class Registration:
    def __init__(self, system):
        self.system = system

    def read_pointer(self, browser):
        if self.system != 'Windows':
            return None
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY[browser], 0, winreg.KEY_READ | winreg.KEY_WOW64_32KEY) as key:
                return winreg.QueryValueEx(key, None)[0]
        except FileNotFoundError:
            return None

    def write_pointer(self, browser, path):
        if self.system != 'Windows':
            return
        import winreg
        if path is None:
            try:
                winreg.DeleteKeyEx(winreg.HKEY_CURRENT_USER, REGISTRY[browser], winreg.KEY_WOW64_32KEY)
            except FileNotFoundError:
                pass
        else:
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, REGISTRY[browser], 0, winreg.KEY_WRITE | winreg.KEY_WOW64_32KEY) as key:
                winreg.SetValueEx(key, None, 0, winreg.REG_SZ, str(path))
