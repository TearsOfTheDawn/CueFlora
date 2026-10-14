"""Maintainer-only, pinned source/origin evidence fetch. Never changes tools."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tomllib
import urllib.request
from urllib.parse import urlsplit
import zipfile
from release_inputs import ROOT, digest

TAG = 'autobuild-2026-07-31-14-10'
COMMIT = 'a99e8230eae00d1cee38f23076a7a1f55cd984e2'


def fetch(output, cache, resume=False):
    output.mkdir(parents=True, exist_ok=resume)
    if (output/'evidence-inputs.json').exists(): raise ValueError('Completed evidence is append-only; choose a fresh directory')
    entries = []

    def download(name, url, expected=None, role='source-evidence'):
        if Path(name).name != name or urlsplit(url).scheme != 'https' or urlsplit(url).hostname not in {'github.com','codeload.github.com','files.pythonhosted.org','static.crates.io'}:
            raise ValueError('Unapproved evidence location')
        target = output/name
        if target.exists():
            if not expected or digest(target)!=expected: raise ValueError('Existing evidence cannot be safely resumed')
        else:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'CueFlora-release-evidence'}),timeout=30) as response, target.open('xb') as stream:
                size=0
                for chunk in iter(lambda:response.read(1024*1024),b''):
                    size+=len(chunk)
                    if size > 256*1024*1024: raise ValueError('Evidence exceeds bound')
                    stream.write(chunk)
        checksum=digest(target)
        if expected and checksum!=expected: raise ValueError('Official evidence checksum mismatch')
        entries.append({'file':name,'url':url,'sha256':checksum,'role':role})
        return target

    checksums = download('BtbN-20260731-checksums.sha256',f'https://github.com/BtbN/FFmpeg-Builds/releases/download/{TAG}/checksums.sha256',
                         '8051fa7760c174bde7adedbf7b5e6a123d145846affc2a0e69c25b2c5cea7d54','origin-checksums')
    archive = download('BtbN-FFmpeg-20260731-win64-gpl.zip',f'https://github.com/BtbN/FFmpeg-Builds/releases/download/{TAG}/ffmpeg-N-125875-g5d4d3bdc61-win64-gpl.zip',
                       '68a5e966533002785c3e4b9a98327e21d5277802668bf889d94086cb6426cbb4','binary-origin-evidence')
    if '68a5e966533002785c3e4b9a98327e21d5277802668bf889d94086cb6426cbb4' not in checksums.read_text():
        raise ValueError('Published checksum listing does not corroborate archive')
    matches={}
    with zipfile.ZipFile(archive) as source:
        for name in ('ffmpeg.exe','ffprobe.exe'):
            entry=next(item for item in source.namelist() if item.endswith('/bin/'+name))
            checksum=hashlib.sha256()
            with source.open(entry) as stream:
                for chunk in iter(lambda:stream.read(1024*1024),b''): checksum.update(chunk)
            matches[name]={'sha256':checksum.hexdigest(),'matchesPreservedBinary':checksum.hexdigest()==digest(cache/name)}
    download('BtbN-FFmpeg-build-recipes-'+COMMIT+'.zip',f'https://codeload.github.com/BtbN/FFmpeg-Builds/zip/{COMMIT}',role='candidate-build-recipes')
    # Only distributions whose exact version is embedded in this executable.
    from PyInstaller.archive.readers import CArchiveReader
    yt=CArchiveReader(str(cache/'yt-dlp.exe'))
    for path in yt.toc:
        if not path.replace('\\','/').endswith('/METADATA'): continue
        fields=dict(line.split(': ',1) for line in yt.extract(path).decode(errors='replace').splitlines() if line.startswith(('Name: ','Version: ')))
        name,version=fields.get('Name'),fields.get('Version')
        if not name or not version: continue
        metadata_url=f'https://pypi.org/pypi/{name}/{version}/json'
        with urllib.request.urlopen(metadata_url,timeout=30) as response: data=json.load(response)
        item=next((item for item in data['urls'] if item['packagetype']=='sdist'),None)
        if item:
            download(item['filename'],item['url'],item['digests']['sha256'],'yt-dlp-observed-dependency-source')
    with zipfile.ZipFile(cache/'Deno-2.9.7-source.zip') as source:
        path=next(name for name in source.namelist() if name.count('/')==1 and name.endswith('Cargo.lock'))
        packages=tomllib.loads(source.read(path).decode())['package']
        v8=next(item for item in packages if item['name']=='v8' and item.get('checksum'))
        download('v8-'+v8['version']+'.crate',f'https://static.crates.io/crates/v8/v8-{v8["version"]}.crate',v8['checksum'],'deno-v8-binding-source')
    manifest={'schema':1,'files':entries,'ffmpegOrigin':{'candidatePublisher':'BtbN/FFmpeg-Builds','tag':TAG,'candidateBuildRecipeCommit':COMMIT,
              'binaryComparison':matches,'originVerified':all(item['matchesPreservedBinary'] for item in matches.values())},
              'redistributionApproved':False,'correspondingSourceComplete':False}
    (output/'evidence-inputs.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',type=Path,required=True); parser.add_argument('--cache',type=Path,default=ROOT/'artifacts/input-cache-v1')
    parser.add_argument('--resume',action='store_true',help='Reuse only verified complete pinned files from an interrupted fetch')
    args=parser.parse_args(); fetch(args.output.resolve(),args.cache.resolve(),args.resume)
