"""Restore exact cached interpreter + wheels to a fresh developer build environment."""
import argparse
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import zipfile
from release_inputs import ROOT, obtain_inputs, digest


def bootstrap(cache, output, official=False,include_auth=True):
    lock = json.loads((ROOT / 'packaging/inputs-windows.lock.json').read_text())
    cache = obtain_inputs(lock, cache, offline=True, source_audio=official)
    if output.exists():
        raise ValueError('Fresh offline environment directory required')
    output.mkdir(parents=True)
    base = output / 'python'
    if official:
        base.mkdir()
        with tarfile.open(cache/'cpython-3.13.15-20260814-windows-stripped.tar.gz') as archive:
            for member in archive:
                path = PurePosixPath(member.name)
                if path.is_absolute() or '..' in path.parts or '\\' in member.name or ':' in member.name or not (member.isdir() or member.isfile()) or path.parts[0] != 'python':
                    raise ValueError('Unsafe official interpreter archive')
                relative = Path(*path.parts[1:])
                if not relative.parts: continue
                target = base/relative
                if member.isdir(): target.mkdir(parents=True,exist_ok=True)
                else:
                    target.parent.mkdir(parents=True,exist_ok=True)
                    with archive.extractfile(member) as source, target.open('xb') as stream:
                        import shutil
                        shutil.copyfileobj(source,stream)
        metadata = json.loads((ROOT/'packaging/python-bootstrap-metadata.json').read_text())
        for name, content in metadata.items():
            (base/name).write_bytes(content.encode('utf-8'))
        for item in lock['interpreterFiles']:
            if not (base/item['file']).is_file() or digest(base/item['file']) != item['sha256']:
                raise ValueError('Official interpreter payload does not match the lock')
    else:
        with zipfile.ZipFile(cache / 'python-3.13.15-local-base.zip') as archive:
            for name in archive.namelist():
                path = PurePosixPath(name)
                if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
                    raise ValueError('Unsafe interpreter archive')
            archive.extractall(base)
    subprocess.run([str(base / 'python.exe'), '-m', 'venv', str(output / 'venv')], check=True)
    python = output / 'venv/Scripts/python.exe'
    requirements=ROOT/'packaging/requirements-windows-hashed.lock'
    if not include_auth:
        # The downloader has its own complete optional-dependency policy. Do not
        # accidentally expand it when the host's auth dependencies grow.
        filtered=output/'build-requirements.lock'
        filtered.write_text('\n'.join(line for line in requirements.read_text().splitlines() if not line.lower().startswith(('pyjwt==','cryptography==','cffi==','pycparser==')))+'\n',encoding='utf-8')
        requirements=filtered
    subprocess.run([str(python), '-m', 'pip', 'install', '--no-index', '--find-links', str(cache), '--require-hashes', '-r', str(requirements)], check=True)
    print(python)
    return python


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--official',action='store_true',help='Use pinned official archive, not a private local snapshot')
    args = parser.parse_args()
    bootstrap(args.cache.resolve(), args.output.resolve(),args.official)
