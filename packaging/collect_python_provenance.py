"""One-time collection of the known 20260814 interpreter's official evidence."""
import hashlib
import json
from pathlib import Path
import sys
import tarfile
from release_inputs import ROOT, digest
from pin_inputs import fetch


def collect(cache):
    lock_file = ROOT/'packaging/inputs-windows.lock.json'
    lock = json.loads(lock_file.read_text())
    assets = [
        ('cpython-3.13.15-20260814-windows-install.tar.gz', 'https://github.com/astral-sh/python-build-standalone/releases/download/20260814/cpython-3.13.15%2B20260814-x86_64-pc-windows-msvc-install_only.tar.gz', '4ca61e4b09c2240cc50cc6910c90664051e93ab7caa2f48b3c6b3c070670c0bd'),
        ('cpython-3.13.15-20260814-windows-stripped.tar.gz', 'https://github.com/astral-sh/python-build-standalone/releases/download/20260814/cpython-3.13.15%2B20260814-x86_64-pc-windows-msvc-install_only_stripped.tar.gz', '07c977bbe4abad07e3bbc314608633e6c74eab482a7bae81f4361cda970b45e6'),
    ]
    comparisons = []
    for name, url, expected in assets:
        target = cache/name
        if fetch(url,target) != expected: raise ValueError('Official interpreter digest mismatch')
        if name not in {item['file'] for item in lock['files']}:
            lock['files'].append({'file':name,'sha256':expected,'url':url,'role':'official-interpreter-evidence'})
        with tarfile.open(target) as archive:
            names = {item.name:item for item in archive.getmembers() if item.isfile()}
            matching, different, missing = [], [], []
            for item in lock['interpreterFiles']:
                member = names.get('python/'+item['file'])
                if member is None: missing.append(item['file']); continue
                with archive.extractfile(member) as stream:
                    actual = hashlib.file_digest(stream,'sha256').hexdigest()
                (matching if actual == item['sha256'] else different).append(item['file'])
            comparisons.append({'archive':name,'matchingFiles':len(matching),'differentFiles':different,'missingFiles':missing,
                'allLockedFilesMatch':not different and not missing,
                'allUpstreamPayloadFilesMatch':not different and set(missing) <= {'BUILD','Lib/EXTERNALLY-MANAGED'},
                'localMetadataOnly':missing if not different and set(missing) <= {'BUILD','Lib/EXTERNALLY-MANAGED'} else []})
    for name, url in [
        ('CPython-3.13.15-source.zip','https://codeload.github.com/python/cpython/zip/refs/tags/v3.13.15'),
        ('python-build-standalone-20260814-source.zip','https://codeload.github.com/astral-sh/python-build-standalone/zip/refs/tags/20260814')]:
        value = fetch(url,cache/name)
        if name not in {item['file'] for item in lock['files']}:
            lock['files'].append({'file':name,'sha256':value,'url':url,'role':'licence-source-evidence'})
    lock['pythonArchiveComparison'] = comparisons
    lock['pythonOrigin'] = '2256 upstream payload files match the official hash-verified 20260814 stripped Windows x64 archive; BUILD and EXTERNALLY-MANAGED are separately hash-locked local uv metadata. Native-library licence closure still needs review.'
    lock_file.write_text(json.dumps(lock,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(comparisons,indent=2))


if __name__ == '__main__':
    collect(Path(sys.argv[1]).resolve())
