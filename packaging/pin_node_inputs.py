"""Obtain one exact official build-only Node archive; print lock for explicit review."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
from urllib.request import urlopen
import zipfile


def pin(cache,version):
    if not re.fullmatch(r'\d+\.\d+\.\d+',version): raise ValueError('Exact Node version required')
    cache.mkdir(parents=True,exist_ok=True)
    filename='node-v'+version+'-win-x64.zip'; base='https://nodejs.org/dist/v'+version+'/'
    with urlopen(base+'SHASUMS256.txt',timeout=60) as response: sums=response.read(1024*1024).decode()
    expected=next((line.split()[0] for line in sums.splitlines() if line.split()[1:]==[filename]),None)
    if not expected or not re.fullmatch('[0-9a-f]{64}',expected): raise ValueError('Official checksum missing')
    target=cache/filename
    if not target.exists():
        partial=target.with_suffix('.zip.partial')
        with urlopen(base+filename,timeout=60) as response,partial.open('xb') as stream: shutil.copyfileobj(response,stream)
        if hashlib.sha256(partial.read_bytes()).hexdigest()!=expected: raise ValueError('Node archive checksum mismatch')
        partial.rename(target)
    if target.is_symlink() or hashlib.sha256(target.read_bytes()).hexdigest()!=expected: raise ValueError('Cached Node archive mismatch')
    with zipfile.ZipFile(target) as archive:
        prefix='node-v'+version+'-win-x64/'
        executable=archive.read(prefix+'node.exe')
        npm=json.loads(archive.read(prefix+'node_modules/npm/package.json'))
        npm_files={name.removeprefix(prefix):hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist() if name.startswith(prefix+'node_modules/npm/') and not name.endswith('/')}
    return {'schema':1,'platform':'Windows-x64','nodeVersion':version,'npmVersion':npm['version'],
        'archive':{'file':filename,'url':base+filename,'sha256':expected},'checksumOrigin':base+'SHASUMS256.txt',
        'nodeExeSha256':hashlib.sha256(executable).hexdigest(),
        'npmFileInventorySha256':hashlib.sha256(json.dumps(npm_files,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        'npmFileCount':len(npm_files),'buildOnly':True}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,required=True); parser.add_argument('--version',required=True)
    args=parser.parse_args(); print(json.dumps(pin(args.cache.resolve(),args.version),indent=2))
