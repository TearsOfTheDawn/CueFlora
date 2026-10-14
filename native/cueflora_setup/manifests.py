"""Central native manifest generation and per-user browser registration locations.

Chrome/Firefox adapters are implemented, not automatically certified on every OS.
"""
from pathlib import Path
import re

HOST = 'cueflora_host'
REGISTRY = {
    'chrome': r'Software\Google\Chrome\NativeMessagingHosts\cueflora_host',
    'firefox': r'Software\Mozilla\NativeMessagingHosts\cueflora_host',
}
DIRECTORIES = {
    'Darwin': {'chrome': 'Library/Application Support/Google/Chrome/NativeMessagingHosts',
               'firefox': 'Library/Application Support/Mozilla/NativeMessagingHosts'},
    'Linux': {'chrome': '.config/google-chrome/NativeMessagingHosts',
              'firefox': '.mozilla/native-messaging-hosts'},
}


def validate_release(value):
    if not isinstance(value, dict) or not isinstance(value.get('owner'), str) or not value['owner'].strip():
        raise ValueError('Explicit release owner is required')
    ids = value.get('extensionIds', {})
    if not isinstance(ids, dict) or not ids or set(ids) - set(REGISTRY):
        raise ValueError('Extension identities are required')
    if 'chrome' in ids and (not isinstance(ids['chrome'], str) or not re.fullmatch('[a-p]{32}', ids['chrome'])):
        raise ValueError('Exact Chrome release extension ID is required')
    if 'firefox' in ids and (not isinstance(ids['firefox'], str) or not re.fullmatch(r'(?:[^\s/\\"<>]+@[^\s/\\"<>]+|\{[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\})', ids['firefox'])):
        raise ValueError('Exact Firefox release extension ID is required')
    return value


def manifest(browser, executable, release):
    validate_release(release)
    if browser not in REGISTRY or browser not in release['extensionIds']:
        raise ValueError('Browser adapter is not supported')
    executable = Path(executable)
    if not executable.is_absolute():
        raise ValueError('Native executable path must be absolute')
    result = {'name': HOST, 'description': 'CueFlora native runtime', 'path': str(executable), 'type': 'stdio'}
    identity = release['extensionIds'][browser]
    result['allowed_extensions' if browser == 'firefox' else 'allowed_origins'] = [
        identity if browser == 'firefox' else f'chrome-extension://{identity}/']
    return result


def manifest_path(browser, system, home, install_root):
    if browser not in REGISTRY:
        raise ValueError('Unsupported browser')
    if system == 'Windows':
        return Path(install_root) / 'manifests' / f'{browser}.json'
    if system not in DIRECTORIES:
        raise ValueError('Unsupported operating system')
    return Path(home) / DIRECTORIES[system][browser] / f'{HOST}.json'
