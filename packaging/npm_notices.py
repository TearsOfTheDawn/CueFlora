"""Hash-bound original release notices absent from exact npm tarballs."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def supplemental_notices(name, version, root=ROOT):
    root = Path(root)
    policy = json.loads((root/'packaging/npm-notices.lock.json').read_text(encoding='utf-8'))
    if policy.get('schema') != 1 or not isinstance(policy.get('packages'), list):
        raise ValueError('Invalid npm notice lock')
    matches = [item for item in policy['packages'] if item.get('name') == name]
    if not matches: return []
    if len(matches) != 1: raise ValueError('Duplicate npm notice binding')
    item = matches[0]
    lock = json.loads((root/'package-lock.json').read_text(encoding='utf-8'))
    pin = lock.get('packages', {}).get('node_modules/'+name, {})
    if (version != item.get('version') or pin.get('version') != version or pin.get('integrity') != item.get('integrity') or
            not re.fullmatch(r'sha512-[A-Za-z0-9+/]+=*', item.get('integrity', '')) or
            any(not re.fullmatch(r'[A-Za-z0-9._-]+', item.get(field, '')) or item[field] in ('.', '..') for field in ('file', 'entry')) or
            not re.fullmatch(r'[a-f0-9]{64}', item.get('sha256', '')) or
            not re.fullmatch(r'https://raw\.githubusercontent\.com/[^?#]+', item.get('origin', ''))):
        raise ValueError('Supplemental npm notice identity mismatch')
    path = root/'packaging/notices'/item['file']
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
        raise ValueError('Supplemental npm notice hash mismatch')
    return [{**item, 'path': path}]
