"""Original notices for exact cryptography wheel SBOM/Cargo inputs; not approval."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tarfile
import tomllib
from urllib.request import urlopen
import zipfile
from release_inputs import ROOT,digest
from notice_names import is_notice_name

LOCK=ROOT/'packaging/auth-native-notices.lock.json'


def read_tar(archive,name,limit=4*1024*1024):
    member=archive.getmember(name)
    if not member.isfile() or not 0<member.size<=limit:raise ValueError('Invalid bounded source member')
    return archive.extractfile(member).read()


def derive(inputs):
    lock=json.loads((ROOT/'packaging/inputs-windows.lock.json').read_text())
    files={item['file']:item for item in lock['files']}
    names=['cryptography-50.0.2-cp311-abi3-win_amd64.whl','cryptography-50.0.2.tar.gz','cffi-2.1.1.tar.gz']
    for name in names:
        if name not in files or (inputs/name).is_symlink() or digest(inputs/name)!=files[name]['sha256']:raise ValueError('Changed authentication source/wheel input')
    with zipfile.ZipFile(inputs/names[0]) as wheel:
        openssl=wheel.read('cryptography-50.0.2.dist-info/sboms/sbom.json')
        rust=wheel.read('cryptography-50.0.2.dist-info/sboms/cryptography-rust.cyclonedx.json')
    with tarfile.open(inputs/names[1]) as source:cargo=read_tar(source,'cryptography-50.0.2/Cargo.lock')
    packages=tomllib.loads(cargo.decode())['package']
    declared={(item['name'],item.get('version')) for item in json.loads(rust)['components']}
    pins=[]
    for item in packages:
        if not item.get('source','').startswith('registry+'):continue
        name,version,checksum=item['name'],item['version'],item['checksum']
        if (name,version) not in declared or not re.fullmatch('[A-Za-z0-9_-]+',name) or not re.fullmatch(r'[0-9][A-Za-z0-9.+-]*',version) or not re.fullmatch('[0-9a-f]{64}',checksum):raise ValueError('Cargo/SBOM mismatch')
        filename=name+'-'+version+'.crate'
        pins.append({'name':name,'version':version,'file':filename,'sha256':checksum,'url':'https://static.crates.io/crates/'+name+'/'+filename,'scope':'exact upstream source-lock/SBOM superset; may include build-only code'})
    component,=json.loads(openssl)['components']
    if component['name']!='openssl' or component['version']!='4.0.3':raise ValueError('Unexpected wheel OpenSSL component')
    checksum,=[item['content'] for item in component['hashes'] if item['alg']=='SHA-256']
    url='https://github.com/openssl/openssl/releases/download/openssl-4.0.3/openssl-4.0.3.tar.gz'
    if not any(item.get('url')==url for item in component['externalReferences']):raise ValueError('OpenSSL origin mismatch')
    pins.append({'name':'openssl-native','version':'4.0.3','file':'openssl-4.0.3.tar.gz','sha256':checksum,'url':url,'scope':'wheel-declared static OpenSSL input, not independently rebuilt'})
    return {'schema':1,'product':'cueflora','inputFiles':{name:files[name]['sha256'] for name in names},
        'cargoLockSha256':hashlib.sha256(cargo).hexdigest(),'rustSbomSha256':hashlib.sha256(rust).hexdigest(),
        'opensslSbomSha256':hashlib.sha256(openssl).hexdigest(),'files':sorted(pins,key=lambda item:item['file']),
        'redistributionApproved':False,'scope':'Exact upstream-declared native dependency sources and original notices; not proof every source-lock package is runtime code'}


def obtain(inputs,cache,online=False):
    expected=json.loads(LOCK.read_text())
    if derive(inputs)!=expected:raise ValueError('Authentication notice lock differs from exact source/SBOM inputs')
    cache.mkdir(parents=True,exist_ok=True)
    for item in expected['files']:
        target=cache/item['file']
        if target.is_symlink():raise ValueError('Linked authentication evidence')
        if not target.exists():
            if not online:raise ValueError('Missing pinned authentication source '+item['file'])
            partial=cache/(item['file']+'.partial')
            with urlopen(item['url'],timeout=60) as source,partial.open('xb') as output:shutil.copyfileobj(source,output)
            if digest(partial)!=item['sha256']:raise ValueError('Authentication source hash mismatch')
            partial.rename(target)
        if digest(target)!=item['sha256']:raise ValueError('Changed authentication source '+item['file'])
    return expected


def collect(inputs,cache,output,online=False):
    lock=obtain(inputs,cache,online)
    output.mkdir(parents=True,exist_ok=False);(output/'notices').mkdir();(output/'sources').mkdir()
    records=[];all_notices={}
    items=[*lock['files'],{'name':'cffi-vendored-libffi-x64','version':'2.1.1','file':'cffi-2.1.1.tar.gz','sha256':lock['inputFiles']['cffi-2.1.1.tar.gz'],'scope':'original x64 vendored libffi C/header notices and build input'}]
    for item in items:
        source=(inputs if item['name']=='cffi-vendored-libffi-x64' else cache)/item['file']
        shutil.copy2(source,output/'sources'/item['file']);notices={}
        with tarfile.open(source) as archive:
            for member in archive:
                if not member.isfile():continue
                # Retain full original libffi text sources, including their
                # embedded copyright/permission blocks, not rewritten notices.
                vendored=item['name']=='cffi-vendored-libffi-x64' and '/src/c/libffi_x86_x64/' in member.name and member.name.endswith(('.c','.h','.asm'))
                if not vendored and not is_notice_name(Path(member.name).name,strict=True):continue
                if not 0<member.size<=2*1024*1024:raise ValueError('Oversized original authentication notice')
                data=archive.extractfile(member).read();name=item['name']+'-'+hashlib.sha256(member.name.encode()).hexdigest()[:12]+'.txt'
                target=output/'notices'/name;target.write_bytes(data)
                notices[name]={'sha256':digest(target),'sourceEntry':member.name,'sourceArchive':item['file']};all_notices[name]=notices[name]
        if not notices:raise ValueError('Original notices missing for '+item['name']+'; review exact upstream origin')
        records.append({**item,'notices':notices})
    report={'schema':1,'lockSha256':digest(LOCK),'cargoLockSha256':lock['cargoLockSha256'],'rustSbomSha256':lock['rustSbomSha256'],
        'opensslSbomSha256':lock['opensslSbomSha256'],'components':records,'notices':all_notices,
        'sourceFiles':{path.name:digest(path) for path in sorted((output/'sources').iterdir())},'redistributionApproved':False,
        'scope':lock['scope']}
    (output/'auth-notice-evidence.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def validate(folder):
    report=json.loads((folder/'auth-notice-evidence.json').read_text())
    lock=json.loads(LOCK.read_text())
    expected={item['name']:item for item in lock['files']}
    expected['cffi-vendored-libffi-x64']={'file':'cffi-2.1.1.tar.gz','sha256':lock['inputFiles']['cffi-2.1.1.tar.gz']}
    if report.get('lockSha256')!=digest(LOCK) or not report.get('notices') or report.get('redistributionApproved') is not False or any(report.get(key)!=lock[key] for key in ('cargoLockSha256','rustSbomSha256','opensslSbomSha256')):raise ValueError('Unbound authentication notice evidence')
    components=report.get('components',[])
    if len(components)!=len(expected) or {item.get('name') for item in components}!=set(expected):raise ValueError('Incomplete authentication notice components')
    if report.get('sourceFiles')!={item['file']:item['sha256'] for item in expected.values()}:raise ValueError('Authentication source inventory mismatch')
    for name,item in report['notices'].items():
        path=folder/'notices'/name
        if Path(name).name!=name or path.is_symlink() or digest(path)!=item['sha256']:raise ValueError('Changed authentication notice')
    for name,checksum in report['sourceFiles'].items():
        path=folder/'sources'/name
        if Path(name).name!=name or path.is_symlink() or digest(path)!=checksum:raise ValueError('Changed authentication source')
    found={}
    for component in components:
        pin=expected[component['name']]
        if component.get('file')!=pin['file'] or component.get('sha256')!=pin['sha256'] or not component.get('notices'):raise ValueError('Authentication component origin mismatch')
        with tarfile.open(folder/'sources'/pin['file']) as archive:
            for name,item in component['notices'].items():
                if name in found or item.get('sourceArchive')!=pin['file'] or hashlib.sha256(read_tar(archive,item['sourceEntry'],2*1024*1024)).hexdigest()!=item.get('sha256'):raise ValueError('Original authentication notice differs from its source')
                found[name]=item
    if found!=report['notices'] or {path.name for path in (folder/'notices').iterdir()}!=set(found):raise ValueError('Authentication notice inventory mismatch')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs',type=Path,required=True);parser.add_argument('--cache',type=Path);parser.add_argument('--output',type=Path)
    parser.add_argument('--online',action='store_true');parser.add_argument('--print-lock',action='store_true')
    args=parser.parse_args()
    if args.print_lock:print(json.dumps(derive(args.inputs),indent=2))
    elif args.cache and args.output:print(json.dumps({'components':len(collect(args.inputs,args.cache,args.output,args.online)['components']),'approval':False}))
    else:parser.error('--cache and --output required for collection')
