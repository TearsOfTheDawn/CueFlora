"""Hash-locked Deno Cargo notice superset; never infer binary shipment or approval."""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import re
import shutil
import tarfile
import tomllib
from urllib.request import urlopen
import zipfile
from release_inputs import ROOT,digest

REGISTRY='registry+https://github.com/rust-lang/crates.io-index'


def pins(cargo):
    if not isinstance(cargo,dict) or not isinstance(cargo.get('package'),list): raise ValueError('Malformed Cargo source lock')
    result=[]; seen=set()
    for item in cargo['package']:
        if not isinstance(item,dict): raise ValueError('Malformed Cargo package')
        origin=item.get('source')
        if origin is None: continue
        if origin!=REGISTRY: raise ValueError('Unsupported Cargo origin; no moving git or registry fallback')
        name=item.get('name',''); version=item.get('version',''); checksum=item.get('checksum','')
        if not all(isinstance(value,str) for value in (name,version,checksum)): raise ValueError('Cargo names, versions and checksums must be strings')
        key=(name.casefold(),version.casefold())
        if not re.fullmatch('[A-Za-z0-9_-]+',name) or not re.fullmatch(r'\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.+-]+)?',version) or not re.fullmatch('[0-9a-f]{64}',checksum) or key in seen:
            raise ValueError('Unsafe/duplicate/unpinned Cargo dependency')
        seen.add(key); result.append({'name':name,'version':version,'sha256':checksum,'crateFile':name+'-'+version+'.crate',
            'url':'https://static.crates.io/crates/'+name+'/'+name+'-'+version+'.crate'})
    if not result: raise ValueError('Empty Cargo registry source inventory')
    return sorted(result,key=lambda item:(item['name'],item['version']))


def validate_policy(source,raw,packages):
    policy=json.loads((ROOT/'packaging/deno-cargo-policy.json').read_text())
    inventory=hashlib.sha256(json.dumps(packages,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if policy.get('schema')!=1 or policy.get('redistributionApproved') is not False or source['sha256']!=policy.get('denoSourceSha256') or hashlib.sha256(raw).hexdigest()!=policy.get('cargoLockSha256') or len(packages)!=policy.get('registryPackageCount') or inventory!=policy.get('registryPinInventorySha256'):
        raise ValueError('Cargo source lock differs from pinned source policy')
    return policy


def source_pins(inputs):
    main=json.loads((ROOT/'packaging/inputs-windows.lock.json').read_text())
    source=next(item for item in main['files'] if item['file']=='Deno-2.9.7-source.zip')
    path=inputs/source['file']
    if path.is_symlink() or digest(path)!=source['sha256']: raise ValueError('Exact Deno source hash mismatch')
    with zipfile.ZipFile(path) as archive: raw=archive.read('deno-2.9.7/Cargo.lock')
    packages=pins(tomllib.loads(raw.decode()))
    validate_policy(source,raw,packages)
    return source,raw,packages


def obtain(item,cache,online=False):
    cache.mkdir(parents=True,exist_ok=True); path=cache/item['crateFile']
    if path.is_symlink(): raise ValueError('Linked Cargo cache input')
    if not path.exists():
        if not online: raise ValueError('Missing exact Cargo input: '+item['crateFile'])
        partial=path.with_suffix('.crate.partial'); size=0
        with urlopen(item['url'],timeout=90) as response,partial.open('xb') as stream:
            while True:
                data=response.read(1024*1024)
                if not data: break
                size+=len(data)
                if size>128*1024*1024: raise ValueError('Oversized Cargo input')
                stream.write(data)
        if digest(partial)!=item['sha256']: raise ValueError('Downloaded Cargo checksum mismatch')
        partial.rename(path)
    if not path.is_file() or digest(path)!=item['sha256']: raise ValueError('Changed Cargo cache input')
    return path


def inspect(item,path,output):
    prefix=item['name']+'-'+item['version']+'/'
    with tarfile.open(path) as archive:
        members=archive.getmembers(); manifests=[member for member in members if member.name==prefix+'Cargo.toml' and member.isfile()]
        if len(manifests)!=1 or manifests[0].size>2*1024*1024: raise ValueError('Exact bounded crate manifest required')
        metadata=tomllib.loads(archive.extractfile(manifests[0]).read().decode()).get('package',{})
        if metadata.get('name')!=item['name'] or metadata.get('version')!=item['version']: raise ValueError('Crate manifest and source pin disagree')
        declared_file=metadata.get('license-file'); explicit=None
        if isinstance(declared_file,str):
            relative=PurePosixPath(declared_file)
            if not relative.is_absolute() and '..' not in relative.parts and '\\' not in declared_file and ':' not in declared_file: explicit=prefix+relative.as_posix()
        notices={}
        for member in members:
            if not member.isfile() or member.size>1024*1024 or not member.name.startswith(prefix): continue
            relative=member.name.removeprefix(prefix)
            if '..' in PurePosixPath(relative).parts or '\\' in relative or ':' in relative: raise ValueError('Unsafe Cargo notice member')
            if member.name!=explicit and not re.fullmatch(r'(?:LICENSE|COPYING|NOTICE|COPYRIGHT)(?:[._-].*)?',Path(relative).name,re.I): continue
            data=archive.extractfile(member).read()
            name=item['name']+'/'+item['version']+'/'+hashlib.sha256(member.name.encode()).hexdigest()[:16]+'.txt'
            target=output/'notices'/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
            notices['notices/'+name]={'sourceEntry':member.name,'sha256':digest(target),
                'scope':'package-root-or-declared' if '/' not in relative or member.name==explicit else 'nested source notice; not necessarily package licence'}
        root_notice=any(record['scope']=='package-root-or-declared' for record in notices.values())
        return {**item,'declaredLicence':metadata.get('license'),'declaredLicenceFile':declared_file,'notices':notices,
            'anyOriginalNoticeAvailable':bool(notices),'packageRootNoticeAvailable':root_notice,
            'scope':'Exact source-lock package. Optional/test/build-only inclusion is not proof of Windows binary shipment.'}


def collect(inputs,cache,output,online=False):
    source,raw,packages=source_pins(inputs)
    if output.exists(): raise ValueError('Fresh Cargo notice evidence output required')
    output.mkdir(parents=True); (output/'Cargo.lock').write_bytes(raw)
    rows=[]
    for index,item in enumerate(packages,1):
        rows.append(inspect(item,obtain(item,cache,online),output))
        if index%200==0: print('Exact Cargo inputs inspected: '+str(index),flush=True)
    files={path.relative_to(output).as_posix():digest(path) for path in (output/'notices').rglob('*') if path.is_file()}
    report={'schema':1,'sourceInput':source,'cargoLockSha256':hashlib.sha256(raw).hexdigest(),'packages':rows,
        'registryPackageCount':len(rows),'registryPinsComplete':True,'noticeFiles':files,
        'missingPackageRootNotices':[{'name':item['name'],'version':item['version'],'declaredLicence':item['declaredLicence']} for item in rows if not item['packageRootNoticeAvailable']],
        'redistributionApproved':False,'binaryDependencyClosureComplete':False,
        'scope':'Conservative source-lock notice superset. No Rust code execution, licence inheritance or binary shipment inferred.'}
    (output/'cargo-notice-inventory.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'registryPackages':len(rows),'noticeFiles':len(files),'missingRootNotices':len(report['missingPackageRootNotices'])}))
    return report


def validate_evidence(folder):
    report=json.loads((folder/'cargo-notice-inventory.json').read_text()); raw=(folder/'Cargo.lock').read_bytes()
    main=json.loads((ROOT/'packaging/inputs-windows.lock.json').read_text())
    source=next(item for item in main['files'] if item['file']=='Deno-2.9.7-source.zip')
    expected=pins(tomllib.loads(raw.decode()))
    validate_policy(source,raw,expected)
    if report.get('sourceInput')!=source or report.get('cargoLockSha256')!=hashlib.sha256(raw).hexdigest() or report.get('registryPinsComplete') is not True or report.get('registryPackageCount')!=len(expected) or report.get('redistributionApproved') is not False or report.get('binaryDependencyClosureComplete') is not False:
        raise ValueError('Cargo evidence source binding mismatch')
    observed=report.get('packages',[])
    if not isinstance(observed,list) or [{key:item.get(key) for key in ('name','version','sha256','crateFile','url')} for item in observed]!=expected:
        raise ValueError('Cargo evidence omitted, reordered or changed source pins')
    paths=list((folder/'notices').rglob('*'))
    if any(path.is_symlink() for path in paths) or {path.relative_to(folder).as_posix():digest(path) for path in paths if path.is_file()}!=report.get('noticeFiles'):
        raise ValueError('Changed/missing Cargo notice evidence')
    notices={name:entry['sha256'] for item in observed for name,entry in item.get('notices',{}).items()}
    if notices!=report['noticeFiles']: raise ValueError('Cargo notice origin inventory mismatch')
    for item in observed:
        prefix=item['name']+'-'+item['version']+'/'
        inferred=False
        for name,entry in item['notices'].items():
            if not name.startswith('notices/'+item['name']+'/'+item['version']+'/') or not re.fullmatch(r'[0-9a-f]{16}\.txt',Path(name).name) or not entry.get('sourceEntry','').startswith(prefix):
                raise ValueError('Cargo notice origin path mismatch')
            relative=PurePosixPath(entry['sourceEntry'].removeprefix(prefix))
            if relative.is_absolute() or '..' in relative.parts or '\\' in str(relative) or ':' in str(relative): raise ValueError('Unsafe Cargo origin path')
            if entry.get('scope') not in ('package-root-or-declared','nested source notice; not necessarily package licence'): raise ValueError('Unsupported Cargo notice scope')
            if entry['scope']=='package-root-or-declared': inferred=True
        if item.get('packageRootNoticeAvailable') is not inferred or item.get('anyOriginalNoticeAvailable') is not bool(item['notices']):
            raise ValueError('Cargo root/nested notice diagnostics mismatch')
    missing=[{'name':item['name'],'version':item['version'],'declaredLicence':item['declaredLicence']} for item in observed if not item.get('packageRootNoticeAvailable')]
    if missing!=report.get('missingPackageRootNotices'): raise ValueError('Cargo missing-notice diagnostics mismatch')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','cache','output'): parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--online',action='store_true')
    args=parser.parse_args(); collect(args.inputs.resolve(),args.cache.resolve(),args.output.resolve(),args.online)
