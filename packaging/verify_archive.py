"""Read-only verification of assembled archives; does not extract or execute files."""
import argparse
import hashlib
import json
from pathlib import PurePosixPath
import stat
import zipfile


def verify_archive(path):
    prefix = 'CueFlora Setup/'
    inventory_name = prefix + 'SHA256SUMS.json'
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if len(names) != len(set(names)) or len(names) != len({n.casefold() for n in names}):
            raise ValueError('Duplicate archive names')
        for entry in entries:
            name = entry.filename.rstrip('/')
            parsed = PurePosixPath(name)
            if (parsed.is_absolute() or '..' in parsed.parts or parsed.as_posix() != name
                    or '\\' in name or ':' in name or not entry.filename.startswith(prefix)
                    or stat.S_ISLNK(entry.external_attr >> 16)):
                raise ValueError('Unsafe archive entry')
        inventory_entry = archive.getinfo(inventory_name)
        if inventory_entry.file_size > 8 * 1024 * 1024:
            raise ValueError('Oversized archive inventory')
        inventory = json.loads(archive.read(inventory_name))
        if not isinstance(inventory, dict) or not inventory:
            raise ValueError('Invalid archive inventory')
        actual = {entry.filename for entry in entries if not entry.is_dir() and entry.filename != inventory_name}
        if actual != {prefix + name for name in inventory}:
            raise ValueError('Unexpected or missing archive files')
        total = 0
        for name, expected in inventory.items():
            checksum = hashlib.sha256()
            with archive.open(prefix + name) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    total += len(chunk)
                    checksum.update(chunk)
            if checksum.hexdigest() != expected:
                raise ValueError('Archive checksum mismatch')
        return {'verifiedFiles': len(inventory), 'uncompressedBytes': total,
                'extracted': False, 'signatureVerified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive')
    args = parser.parse_args()
    print(json.dumps(verify_archive(args.archive), indent=2))
