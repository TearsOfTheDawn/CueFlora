"""Restore notices omitted by the exact v8 crate; do not claim binary closure."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tomllib
from urllib.parse import urlsplit
from urllib.request import urlopen
import zipfile
from release_inputs import ROOT,digest


def validate(lock):
    if not isinstance(lock,dict) or lock.get('schema')!=1 or lock.get('denoVersion')!='2.9.7' or lock.get('bindingVersion')!='150.4.0' or lock.get('v8Version')!='15.0.245.2-rusty' or lock.get('redistributionApproved') is not False or not isinstance(lock.get('files'),list) or len(lock['files'])!=2:
        raise ValueError('Exact Deno/V8 notice lock required')
    for field in ('bindingCommit','v8Commit'):
        if not re.fullmatch('[0-9a-f]{40}',str(lock.get(field,''))): raise ValueError('Exact V8 commits required')
    names=set()
    for item in lock['files']:
        if not isinstance(item,dict): raise ValueError('Malformed V8 notice source')
        parsed=urlsplit(item.get('url','')); name=item.get('file',''); source_root=item.get('root','')
        if not re.fullmatch('[A-Za-z0-9_.-]+',name) or name in ('.','..') or name.casefold() in names or not re.fullmatch('[0-9a-f]{64}',str(item.get('sha256',''))) or not re.fullmatch('[A-Za-z0-9_-]+',source_root) or parsed.scheme!='https' or parsed.hostname!='codeload.github.com' or parsed.username or parsed.password or parsed.port not in (None,443) or parsed.query or parsed.fragment:
            raise ValueError('Unsafe/unpinned V8 notice source')
        names.add(name.casefold())
    expected=[('rusty_v8',lock['bindingCommit']),('v8',lock['v8Commit'])]
    for item,(repo,commit) in zip(lock['files'],expected):
        if item['root']!=repo+'-'+commit or item['url']!='https://codeload.github.com/denoland/'+repo+'/zip/'+commit:
            raise ValueError('V8 repository/commit/root mismatch')
    return lock


def obtain(cache,online=False):
    lock=validate(json.loads((ROOT/'packaging/v8-notice-inputs.lock.json').read_text()))
    cache.mkdir(parents=True,exist_ok=True)
    for item in lock['files']:
        path=cache/item['file']
        if not path.exists():
            if not online: raise ValueError('Missing exact V8 notice source: '+item['file'])
            partial=path.with_suffix(path.suffix+'.partial')
            with urlopen(item['url'],timeout=90) as response,partial.open('xb') as stream: shutil.copyfileobj(response,stream)
            if digest(partial)!=item['sha256']: raise ValueError('Downloaded V8 source hash mismatch')
            partial.rename(path)
        if path.is_symlink() or not path.is_file() or digest(path)!=item['sha256']: raise ValueError('Changed V8 notice source')
    return lock


def match_versions(lock,cargo,vcs,crate_header,source_header,version_output):
    packages=[item for item in cargo.get('package',[]) if item.get('name')=='v8']
    if len(packages)!=1 or packages[0]['version']!=lock['bindingVersion'] or vcs.get('git',{}).get('sha1')!=lock['bindingCommit']:
        raise ValueError('Deno Cargo/V8 crate commit evidence mismatch')
    if crate_header!=source_header or 'v8 '+lock['v8Version'] not in version_output:
        raise ValueError('V8 source/crate/binary version evidence mismatch')
    # Dirty source metadata is recorded, never silently treated as clean proof.
    return packages[0]['checksum']


def collect(inputs,cache,output,online=False):
    lock=obtain(cache,online)
    main=json.loads((ROOT/'packaging/inputs-windows.lock.json').read_text())
    expected={item['file']:item['sha256'] for item in main['files']}
    for name in ('deno.exe','Deno-2.9.7-source.zip'):
        if (inputs/name).is_symlink() or digest(inputs/name)!=expected[name]: raise ValueError('Deno origin input mismatch')
    with zipfile.ZipFile(inputs/'Deno-2.9.7-source.zip') as archive:
        cargo=tomllib.loads(archive.read('deno-2.9.7/Cargo.lock').decode())
    crate=cache/'v8-150.4.0.crate'
    extra=json.loads((ROOT/'packaging/evidence-windows.lock.json').read_text())
    crate_hash=next(item['sha256'] for item in extra['files'] if item['file']==crate.name)
    if crate.is_symlink() or digest(crate)!=crate_hash: raise ValueError('Exact V8 crate hash mismatch')
    with tarfile.open(crate) as archive:
        vcs=json.loads(archive.extractfile('v8-150.4.0/.cargo_vcs_info.json').read())
        crate_header=archive.extractfile('v8-150.4.0/v8/include/v8-version.h').read()
        package=tomllib.loads(archive.extractfile('v8-150.4.0/Cargo.toml').read().decode())
    with zipfile.ZipFile(cache/lock['files'][1]['file']) as archive:
        source_header=archive.read(lock['files'][1]['root']+'/include/v8-version.h')
    version=subprocess.check_output([str(inputs/'deno.exe'),'--version'],text=True,timeout=15)
    if match_versions(lock,cargo,vcs,crate_header,source_header,version)!=crate_hash: raise ValueError('Cargo and crate checksum mismatch')
    if output.exists(): raise ValueError('Fresh V8 notice output required')
    output.mkdir(parents=True); notices={}
    for item in lock['files']:
        with zipfile.ZipFile(cache/item['file']) as archive:
            required=item['root']+'/LICENSE'
            if required not in archive.namelist(): raise ValueError('Core V8/binding licence missing')
            for entry in archive.infolist():
                if entry.is_dir() or entry.file_size>1024*1024 or not re.fullmatch(r'(?:LICENSE|COPYING|NOTICE|COPYRIGHT)(?:[._-].*)?',Path(entry.filename).name,re.I): continue
                content=archive.read(entry)
                target=output/'notices'/(hashlib.sha256((item['file']+':'+entry.filename).encode()).hexdigest()[:16]+'.txt')
                target.parent.mkdir(exist_ok=True); target.write_bytes(content)
                notices[target.name]={'sourceArchive':item['file'],'sourceEntry':entry.filename,'sha256':digest(target),
                    'scope':'Exact source notice; tree includes tests/tools, not proof that all described code is shipped'}
    sources=output/'sources'; sources.mkdir()
    for item in lock['files']: shutil.copy2(cache/item['file'],sources/item['file'])
    shutil.copy2(ROOT/'packaging/v8-notice-inputs.lock.json',sources/'v8-notice-inputs.lock.json')
    report={'schema':1,'denoSha256':expected['deno.exe'],'denoVersionOutput':version,'bindingCrateSha256':crate_hash,'crateVcs':vcs,
        'versionHeaderSha256':hashlib.sha256(crate_header).hexdigest(),'lockSha256':digest(ROOT/'packaging/v8-notice-inputs.lock.json'),
        'sourceInputs':lock['files'],'notices':notices,'noticeFiles':{path.name:digest(path) for path in (output/'notices').iterdir()},
        'crateLicenceExclusionObserved':'LICENSE*' in package['package'].get('exclude',[]),
        'coreNoticesRestored':True,'redistributionApproved':False,'binaryDependencyClosureComplete':False,
        'remaining':['V8 transitive submodule notices at exact pointers','Deno shipped Rust dependency notice coverage',
            'Determine Windows-relevant libraries/build flags; test/Linux notices are not actual Windows-binary shipment evidence'],
        'scope':'Exact original core notices restored; matching declared source commit/version does not erase dirty crate VCS metadata or establish complete binary closure.'}
    (output/'v8-notice-evidence.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'coreNoticesRestored':True,'notices':len(notices),'binaryDependencyClosureComplete':False}))
    return report


def validate_evidence(folder,deno):
    report=json.loads((folder/'v8-notice-evidence.json').read_text())
    lock=validate(json.loads((ROOT/'packaging/v8-notice-inputs.lock.json').read_text()))
    if report.get('coreNoticesRestored') is not True or report.get('denoSha256')!=digest(deno) or report.get('lockSha256')!=digest(ROOT/'packaging/v8-notice-inputs.lock.json') or report.get('sourceInputs')!=lock['files'] or report.get('redistributionApproved') is not False or report.get('binaryDependencyClosureComplete') is not False:
        raise ValueError('Deno/V8 notice evidence binding mismatch')
    paths=list((folder/'notices').rglob('*'))
    if any(path.is_symlink() for path in paths) or {path.name:digest(path) for path in paths if path.is_file()}!=report.get('noticeFiles'):
        raise ValueError('Changed V8 notice evidence')
    if set(report['noticeFiles'])!=set(report.get('notices',{})) or not report['noticeFiles'] or any(report['noticeFiles'][name]!=item.get('sha256') for name,item in report['notices'].items()):
        raise ValueError('V8 notice origin inventory mismatch')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','cache','output'): parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--online',action='store_true')
    args=parser.parse_args(); collect(args.inputs.resolve(),args.cache.resolve(),args.output.resolve(),args.online)
