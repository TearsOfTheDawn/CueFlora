"""Replay hash-locked observed Python sources without selecting newer versions."""
import json
from pathlib import Path
import re
import shutil
import tarfile
from urllib.parse import urlsplit
from urllib.request import urlopen
import zipfile
from release_inputs import ROOT,digest


def validate(lock):
    if not isinstance(lock,dict) or lock.get('schema')!=1 or lock.get('completeBinaryDependencyClosure') is not False or lock.get('redistributionApproved') is not False or not re.fullmatch('[0-9a-f]{64}',str(lock.get('observedYtDlpSha256',''))) or not isinstance(lock.get('sources'),list) or not lock['sources']:
        raise ValueError('Malformed observed source lock')
    names=set()
    for item in lock['sources']:
        if not isinstance(item,dict): raise ValueError('Malformed observed source')
        name=item.get('file',''); parsed=urlsplit(item.get('url',''))
        if not isinstance(name,str) or not re.fullmatch('[A-Za-z0-9_.+-]+',name) or name.casefold() in names or not isinstance(item.get('package'),str) or not re.fullmatch('[A-Za-z0-9_-]+',item['package']) or not re.fullmatch(r'\d+(?:\.\d+){1,3}',str(item.get('version',''))) or not re.fullmatch('[0-9a-f]{64}',str(item.get('sha256',''))) or parsed.scheme!='https' or parsed.hostname!='files.pythonhosted.org' or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('Unsafe/unpinned observed source')
        names.add(name.casefold())
    return lock


def obtain(cache,online=False):
    lock=validate(json.loads((ROOT/'packaging/observed-tool-sources.lock.json').read_text()))
    cache.mkdir(parents=True,exist_ok=True)
    for item in lock['sources']:
        target=cache/item['file']
        if not target.exists():
            if not online: raise ValueError('Missing exact observed dependency source: '+item['file'])
            partial=target.with_suffix(target.suffix+'.partial')
            with urlopen(item['url'],timeout=60) as response,partial.open('xb') as stream: shutil.copyfileobj(response,stream)
            if digest(partial)!=item['sha256']: raise ValueError('Observed source hash mismatch')
            partial.rename(target)
        if target.is_symlink() or not target.is_file() or digest(target)!=item['sha256']: raise ValueError('Changed observed source input')
    return lock


def collect(cache,output,audit,online=False):
    lock=obtain(cache,online)
    if audit.get('ytDlpSha256')!=lock['observedYtDlpSha256']: raise ValueError('Observed source lock belongs to another downloader executable')
    if output.exists(): raise ValueError('Fresh observed source output required')
    output.mkdir(parents=True)
    notices={}
    for item in lock['sources']:
        path=cache/item['file']; shutil.copy2(path,output/path.name)
        if path.suffix=='.zip':
            with zipfile.ZipFile(path) as archive:
                entries=[(entry.filename,archive.read(entry)) for entry in archive.infolist() if not entry.is_dir() and entry.file_size<1024*1024 and re.search('license|copying|notice',Path(entry.filename).name,re.I)]
        else:
            with tarfile.open(path) as archive:
                entries=[(entry.name,archive.extractfile(entry).read()) for entry in archive if entry.isfile() and entry.size<1024*1024 and re.search('license|copying|notice',Path(entry.name).name,re.I)]
        import hashlib
        for original,content in entries:
            name=item['package']+'-'+hashlib.sha256(original.encode()).hexdigest()[:12]+'.txt'
            target=output/'notices'/name; target.parent.mkdir(exist_ok=True); target.write_bytes(content)
            notices[name]={'package':item['package'],'version':item['version'],'sourceArchive':item['file'],'entry':original,'sha256':digest(target)}
    report={'schema':1,'lockSha256':digest(ROOT/'packaging/observed-tool-sources.lock.json'),'observedYtDlpSha256':lock['observedYtDlpSha256'],
        'sources':lock['sources'],'notices':notices,'completeBinaryDependencyClosure':False,'redistributionApproved':False,
        'scope':'Matching observed Python dependencies, including GPL Mutagen; native and unobserved dependencies remain separately assessed'}
    (output/'observed-source-inventory.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report
