"""Strict local payload inventory verification. Signing is a separate release gate."""
import hashlib
import json
import re
from pathlib import Path, PurePosixPath


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def verify_bundle(root):
    root = Path(root).absolute()
    if root.is_symlink() or root.resolve() != root:
        raise ValueError('Linked runtime roots are not supported')
    # Inspect directories too: following a linked directory can bypass a file-only
    # inventory check. Reject links before opening any manifest or payload file.
    for target in root.rglob('*'):
        if target.is_symlink() or target.resolve() != target:
            raise ValueError('Linked runtime entries are not supported')
    value = json.loads((root / 'runtime-manifest.json').read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('Invalid runtime inventory')
    files = value.get('files')
    if value.get('schema') != 1 or not isinstance(files, dict) or not files:
        raise ValueError('Invalid runtime inventory')
    for relative, expected in files.items():
        path = PurePosixPath(relative)
        if (not relative or path.as_posix() != relative or relative == '.'
                or relative == 'runtime-manifest.json' or path.is_absolute()
                or '..' in path.parts or '\\' in relative or ':' in relative):
            raise ValueError('Unsafe runtime inventory path')
        if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected):
            raise ValueError('Invalid runtime inventory hash')
        target = root.joinpath(*path.parts)
        if not target.resolve().is_relative_to(root) or target.is_symlink() or not target.is_file() or digest(target) != expected:
            raise ValueError('Runtime inventory verification failed')
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p != root / 'runtime-manifest.json'}
    if actual != set(files):
        raise ValueError('Unexpected or missing runtime files')
    return value
