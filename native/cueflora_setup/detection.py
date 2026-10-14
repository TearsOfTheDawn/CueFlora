"""Conservative detection; no browser is selected or registered automatically."""
import os
from pathlib import Path
import platform
import shutil


def detected_browsers():
    system = platform.system()
    found = []
    if system == 'Windows':
        import winreg
        for name, executable in [('chrome', 'chrome.exe'), ('firefox', 'firefox.exe')]:
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                for view in (winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY):
                    try:
                        with winreg.OpenKey(hive, 'Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\' + executable,
                                            0, winreg.KEY_READ | view) as key:
                            path = winreg.QueryValueEx(key, None)[0]
                            if Path(path).is_file() and name not in found:
                                found.append(name)
                    except OSError:
                        pass
    elif system == 'Darwin':
        for name, app in [('chrome', 'Google Chrome.app'), ('firefox', 'Firefox.app')]:
            if any((root / app).is_dir() for root in [Path('/Applications'), Path.home() / 'Applications']):
                found.append(name)
    elif system == 'Linux':
        for name, executable in [('chrome', 'google-chrome'), ('firefox', 'firefox')]:
            path = shutil.which(executable)
            if path and not any(part in str(Path(path).resolve()).lower() for part in ('snap', 'flatpak')):
                found.append(name)
    return found
