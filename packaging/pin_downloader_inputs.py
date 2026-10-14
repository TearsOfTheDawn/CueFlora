"""Select once from the exact yt-dlp source's pins, never package 'latest'."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tomllib
from urllib.request import urlopen
from urllib.parse import urlsplit
import zipfile
from packaging.requirements import Requirement
from packaging.tags import sys_tags
from packaging.utils import parse_wheel_filename
from release_inputs import ROOT,digest


def pins(archive):
    with zipfile.ZipFile(archive) as source:
        project=tomllib.loads(source.read('yt-dlp-2026.08.19/pyproject.toml').decode())
        requirements=project['project']['optional-dependencies']
        result={}
        for group in ('pin','pin-curl-cffi'):
            for value in requirements[group]:
                item=Requirement(value)
                if item.marker and not item.marker.evaluate(): continue
                constraints=list(item.specifier)
                if len(constraints)!=1 or constraints[0].operator!='==' or not re.fullmatch(r'\d+(?:\.\d+){1,3}',constraints[0].version):
                    raise ValueError('Every selected upstream dependency must be exactly pinned')
                name=item.name.lower().replace('_','-'); version=constraints[0].version
                if name in result and result[name]!=version: raise ValueError('Conflicting upstream dependency pins')
                result[name]=version
        hashes={}
        for filename in ('default.txt','curl-cffi.txt'):
            text=source.read('yt-dlp-2026.08.19/bundle/requirements/'+filename).decode()
            for match in re.finditer(r'^([A-Za-z0-9_-]+)==([^\s;]+)(.*?)(?=^[A-Za-z0-9_-]+==|\Z)',text,re.M|re.S):
                name=match[1].lower().replace('_','-')
                hashes.setdefault((name,match[2]),set()).update(re.findall(r'--hash=sha256:([0-9a-f]{64})',match[3]))
        return result,hashes


def download(item,cache):
    url=urlsplit(item['url']); name=item['file']
    if not re.fullmatch('[A-Za-z0-9_.+-]+',name) or url.scheme!='https' or url.hostname!='files.pythonhosted.org' or url.username or url.password or url.query or url.fragment or not re.fullmatch('[0-9a-f]{64}',item['sha256']):
        raise ValueError('Unsafe primary downloader input')
    path=cache/name
    if not path.exists():
        partial=path.with_suffix(path.suffix+'.partial')
        with urlopen(item['url'],timeout=60) as response,partial.open('xb') as stream: shutil.copyfileobj(response,stream)
        if digest(partial)!=item['sha256']: raise ValueError('Downloaded input hash mismatch')
        partial.rename(path)
    if path.is_symlink() or digest(path)!=item['sha256']: raise ValueError('Changed downloader input')
    return path


def pin(input_cache,cache):
    cache.mkdir(parents=True,exist_ok=True)
    main=json.loads((ROOT/'packaging/inputs-windows.lock.json').read_text())
    item=next(item for item in main['files'] if item['file']=='yt-dlp-2026.08.19-source.zip')
    source=input_cache/item['file']
    if digest(source)!=item['sha256']: raise ValueError('Exact yt-dlp source mismatch')
    requirements,upstream_hashes=pins(source)
    tags=list(sys_tags()); ranks={tag:index for index,tag in enumerate(tags)}; records=[]
    for name,version in sorted(requirements.items()):
        with urlopen('https://pypi.org/pypi/'+name+'/'+version+'/json',timeout=60) as response:
            raw=response.read(8*1024*1024+1)
        if len(raw)>8*1024*1024: raise ValueError('Oversized primary package metadata')
        metadata=json.loads(raw); choices=[]
        for candidate in metadata['urls']:
            if candidate['packagetype']!='bdist_wheel': continue
            _,_,_,wheel_tags=parse_wheel_filename(candidate['filename'])
            rank=min((ranks[tag] for tag in wheel_tags if tag in ranks),default=None)
            if rank is not None: choices.append((rank,candidate))
        if not choices: raise ValueError('No exact compatible wheel for '+name+' '+version)
        candidate=min(choices,key=lambda pair:pair[0])[1]
        wheel={'file':candidate['filename'],'url':candidate['url'],'sha256':candidate['digests']['sha256']}
        if wheel['sha256'] not in upstream_hashes.get((name,version),set()):
            raise ValueError('Selected wheel is not in the exact upstream hash lock: '+name)
        download(wheel,cache)
        sdist=next((entry for entry in metadata['urls'] if entry['packagetype']=='sdist'),None)
        source_record=None
        if sdist:
            source_record={'file':sdist['filename'],'url':sdist['url'],'sha256':sdist['digests']['sha256']}
            download(source_record,cache)
        records.append({'name':name,'version':version,'wheel':wheel,'source':source_record,
            'declaredLicence':metadata['info'].get('license_expression') or metadata['info'].get('license'),
            'upstreamWheelHashVerified':True})
    return {'schema':1,'ytDlpVersion':'2026.08.19','pythonVersion':main['pythonVersion'],'source':item,
        'selection':'Exact tag pin/pin-curl-cffi markers evaluated for Windows CPython 3.13; no optional feature removed',
        'dependencies':records,'redistributionApproved':False,'completeNativeClosure':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs',type=Path,required=True); parser.add_argument('--cache',type=Path,required=True)
    args=parser.parse_args(); print(json.dumps(pin(args.inputs.resolve(),args.cache.resolve()),indent=2))
