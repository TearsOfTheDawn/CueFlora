"""Exact official Node/npm build inputs, isolated from installed/global modules."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
from urllib.request import urlopen
import zipfile
from release_inputs import ROOT,digest


def validate(lock):
    if not isinstance(lock,dict) or set(lock) != {'schema','platform','nodeVersion','npmVersion','archive','checksumOrigin','nodeExeSha256','npmFileInventorySha256','npmFileCount','buildOnly'} or lock['schema']!=1 or lock['platform']!='Windows-x64' or lock['buildOnly'] is not True:
        raise ValueError('Malformed Node input lock')
    for name in ('nodeVersion','npmVersion'):
        if not isinstance(lock[name],str) or not re.fullmatch(r'\d+\.\d+\.\d+',lock[name]): raise ValueError('Exact Node/npm versions required')
    filename='node-v'+lock['nodeVersion']+'-win-x64.zip'; base='https://nodejs.org/dist/v'+lock['nodeVersion']+'/'
    item=lock['archive']
    if not isinstance(item,dict) or set(item)!={'file','url','sha256'} or item['file']!=filename or item['url']!=base+filename or lock['checksumOrigin']!=base+'SHASUMS256.txt':
        raise ValueError('Unsupported Node archive origin/name')
    for checksum in (item['sha256'],lock['nodeExeSha256'],lock['npmFileInventorySha256']):
        if not isinstance(checksum,str) or not re.fullmatch('[0-9a-f]{64}',checksum): raise ValueError('Node/npm input hashes required')
    if type(lock['npmFileCount']) is not int or lock['npmFileCount']<1: raise ValueError('Complete npm file inventory required')
    return lock


def obtain(cache,online=False):
    lock=validate(json.loads((ROOT/'packaging/node-inputs.lock.json').read_text()))
    cache.mkdir(parents=True,exist_ok=True); target=cache/lock['archive']['file']
    if not target.exists():
        if not online: raise ValueError('Missing exact Node archive; populate the public input cache')
        partial=target.with_suffix('.zip.partial')
        with urlopen(lock['archive']['url'],timeout=60) as response,partial.open('xb') as stream: shutil.copyfileobj(response,stream)
        if digest(partial)!=lock['archive']['sha256']: raise ValueError('Downloaded Node input mismatch')
        partial.rename(target)
    if target.is_symlink() or not target.is_file() or digest(target)!=lock['archive']['sha256']: raise ValueError('Changed Node archive')
    return target,lock


def restore(cache,output,online=False):
    target,lock=obtain(cache,online)
    if output.exists(): raise ValueError('Fresh Node build directory required')
    prefix='node-v'+lock['nodeVersion']+'-win-x64/'
    npm_files={}
    with zipfile.ZipFile(target) as archive:
        seen=set()
        for entry in archive.infolist():
            path=PurePosixPath(entry.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in entry.filename or ':' in entry.filename or not entry.filename.startswith(prefix) or entry.filename.casefold() in seen or (entry.external_attr>>16)&0o170000==0o120000:
                raise ValueError('Unsafe/duplicate/linked Node archive member')
            seen.add(entry.filename.casefold())
            if entry.filename.startswith(prefix+'node_modules/npm/') and not entry.is_dir():
                npm_files[entry.filename.removeprefix(prefix)]=hashlib.sha256(archive.read(entry)).hexdigest()
        if len(npm_files)!=lock['npmFileCount'] or hashlib.sha256(json.dumps(npm_files,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=lock['npmFileInventorySha256']:
            raise ValueError('Node/npm archive inventory mismatch')
        output.mkdir(parents=True)
        archive.extractall(output)
    root=output/prefix.rstrip('/')
    if digest(root/'node.exe')!=lock['nodeExeSha256'] or json.loads((root/'node_modules/npm/package.json').read_text())['version']!=lock['npmVersion']:
        raise ValueError('Restored Node/npm version/hash mismatch')
    return root,{'nodeVersion':lock['nodeVersion'],'npmVersion':lock['npmVersion'],'archiveSha256':lock['archive']['sha256'],
        'nodeExeSha256':lock['nodeExeSha256'],'npmFileInventorySha256':lock['npmFileInventorySha256'],
        'npmFileCount':lock['npmFileCount'],'installedGlobalModulesUsed':False,'buildOnly':True}
