"""One-time maintainer lock generation from explicitly selected versions, never latest."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import shutil
import sys
import urllib.request
import zipfile
from packaging.tags import sys_tags
from packaging.utils import parse_wheel_filename
from release_inputs import ROOT, digest, inspect_ejs, validate_lock


def fetch(url, target):
    if not target.exists():
        with urllib.request.urlopen(url, timeout=60) as source, target.open('xb') as output:
            shutil.copyfileobj(source, output)
    return digest(target)


def pin(cache, old_tools, output):
    if output.exists():
        raise ValueError('Do not overwrite a reviewed lock')
    cache.mkdir(parents=True, exist_ok=True)
    entries, wheels = [], []
    old_lock = json.loads((ROOT / 'packaging/tools-windows.lock.json').read_text())
    for item in old_lock['tools']:
        file = item['name'] + '.exe'
        source = old_tools / file
        if digest(source) != item['sha256']:
            raise ValueError('Existing audio tool changed')
        if not (cache / file).exists():
            shutil.copy2(source, cache / file)
        entries.append({'file': file, 'sha256': item['sha256'], 'role': 'shipped-tool',
            **({'url': 'https://github.com/yt-dlp/yt-dlp/releases/download/2026.08.19/yt-dlp.exe', 'origin': 'matches official pinned SHA2-256SUMS'} if item['name'] == 'yt-dlp' else {'origin': 'preserved local binary; upstream binary provenance unresolved'})})
    deno_zip = cache / 'deno-2.9.7-windows-x64.zip'
    url = 'https://github.com/denoland/deno/releases/download/v2.9.7/deno-x86_64-pc-windows-msvc.zip'
    expected = 'a0c3101b4158d1dfb7d6a78a7bf0f3de80c96bb423c152beec8beb22786f2238'
    if fetch(url, deno_zip) != expected:
        raise ValueError('Official Deno archive digest mismatch')
    with zipfile.ZipFile(deno_zip) as archive:
        if archive.namelist() != ['deno.exe']:
            raise ValueError('Unexpected Deno archive inventory')
        if not (cache / 'deno.exe').exists():
            with (cache / 'deno.exe').open('xb') as target:
                target.write(archive.read('deno.exe'))
    entries += [{'file': deno_zip.name, 'sha256': expected, 'url': url, 'role': 'official-tool-archive'},
                {'file': 'deno.exe', 'sha256': 'e020f3e232bd16e33768dee528e5983349c962952051ced0a5d58ad42f5d9b33', 'role': 'shipped-tool', 'origin': 'extracted from locked official Deno archive'}]
    sources = {
        'Tcl-8.6.12-license.terms': 'https://raw.githubusercontent.com/tcltk/tcl/core-8-6-12/license.terms',
        'Deno-2.9.7-LICENSE.md': 'https://raw.githubusercontent.com/denoland/deno/v2.9.7/LICENSE.md',
        'yt-dlp-2026.08.19-THIRD_PARTY_LICENSES.txt': 'https://raw.githubusercontent.com/yt-dlp/yt-dlp/2026.08.19/THIRD_PARTY_LICENSES.txt',
        'yt-dlp-2026.08.19-source.zip': 'https://codeload.github.com/yt-dlp/yt-dlp/zip/refs/tags/2026.08.19',
        'Deno-2.9.7-source.zip': 'https://codeload.github.com/denoland/deno/zip/refs/tags/v2.9.7',
        'FFmpeg-5d4d3bdc61-source.zip': 'https://codeload.github.com/FFmpeg/FFmpeg/zip/5d4d3bdc61',
    }
    for name, source in sources.items():
        entries.append({'file': name, 'sha256': fetch(source, cache / name), 'url': source, 'role': 'licence-source-evidence'})
    tags = set(sys_tags())
    for line in (ROOT / 'packaging/requirements-windows.lock').read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        name, version = line.split('==')
        if importlib.metadata.version(name) != version:
            raise ValueError('Installed version differs from pinned requirement')
        with urllib.request.urlopen(f'https://pypi.org/pypi/{name}/{version}/json', timeout=30) as response:
            metadata = json.load(response)
        compatible = [file for file in metadata['urls'] if file['filename'].endswith('.whl') and set(parse_wheel_filename(file['filename'])[3]) & tags]
        if len(compatible) != 1:
            raise ValueError('Expected exactly one compatible wheel for ' + name)
        file = compatible[0]
        if fetch(file['url'], cache / file['filename']) != file['digests']['sha256']:
            raise ValueError('Wheel hash mismatch')
        entries.append({'file': file['filename'], 'sha256': file['digests']['sha256'], 'url': file['url'], 'role': 'build-wheel'})
        wheels.append({'name': name, 'version': version, 'file': file['filename'], 'sha256': file['digests']['sha256']})
    base = Path(sys.base_prefix)
    interpreter = [p for p in base.rglob('*') if p.is_file() and not any(v in p.parts for v in ('site-packages', '__pycache__', 'Scripts'))]
    bootstrap = cache / 'python-3.13.15-local-base.zip'
    if not bootstrap.exists():
        with zipfile.ZipFile(bootstrap, 'x', zipfile.ZIP_DEFLATED) as archive:
            for file in sorted(interpreter):
                archive.write(file, file.relative_to(base).as_posix())
    entries.append({'file': bootstrap.name, 'sha256': digest(bootstrap), 'role': 'local-interpreter-bootstrap', 'origin': 'hash-locked existing uv interpreter, not a verified official archive'})
    lock = {'schema': 1, 'platform': 'Windows-x64', 'pythonVersion': sys.version.split()[0],
        'pythonOrigin': 'Existing uv-managed CPython; exact binary inputs hash-locked below; bootstrap archive provenance is an outstanding release gate.',
        'interpreterFiles': [{'file': p.relative_to(base).as_posix(), 'sha256': digest(p)} for p in sorted(interpreter)],
        'tools': {name: name + '.exe' for name in ('yt-dlp', 'ffmpeg', 'ffprobe', 'deno')},
        'denoVersion': '2.9.7', 'ejs': inspect_ejs(cache / 'yt-dlp.exe'), 'pythonWheels': wheels, 'files': entries,
        'redistributionApproved': False, 'publicReleaseAuthorized': False}
    validate_lock(lock)
    output.write_text(json.dumps(lock, indent=2) + '\n', encoding='utf-8')
    (ROOT / 'packaging/requirements-windows-hashed.lock').write_text('\n'.join(w['name'] + '==' + w['version'] + ' --hash=sha256:' + w['sha256'] for w in wheels) + '\n', encoding='utf-8')
    print('Pinned inputs:', len(entries), 'Python wheels:', len(wheels))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--existing-tools', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    pin(args.cache, args.existing_tools, args.output)
