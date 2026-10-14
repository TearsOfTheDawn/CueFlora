"""Replay exact repository notice evidence without licence inheritance assumptions."""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import re
import tarfile
import tomllib
from urllib.request import urlopen
import zipfile
from cargo_notice_evidence import source_pins,obtain
from release_inputs import digest


def safe_repository(value):
    if not isinstance(value,str): return None
    match=re.fullmatch(r'https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(?:/tree/[^?#]+)?/?',value)
    return 'https://github.com/'+match[1]+'/'+match[2].removesuffix('.git') if match else None


def origin(item,path):
    prefix=item['name']+'-'+item['version']+'/'
    with tarfile.open(path) as archive:
        metadata=tomllib.loads(archive.extractfile(prefix+'Cargo.toml').read().decode())['package']
        entries=[member for member in archive if member.name==prefix+'.cargo_vcs_info.json' and member.isfile()]
        vcs=json.loads(archive.extractfile(entries[0]).read()) if len(entries)==1 else {}
    return {'repository':safe_repository(metadata.get('repository')),'vcs':vcs}


def inspect_notice_archive(item,entry,cache):
    repository=safe_repository(entry.get('repository')); vcs=entry.get('vcs',{}); commit=vcs.get('git',{}).get('sha1')
    record=entry.get('sourceArchive',{})
    expected_url='https://codeload.github.com/'+repository.removeprefix('https://github.com/')+'/zip/'+commit if repository and isinstance(commit,str) else None
    if not repository or not re.fullmatch('[0-9a-f]{40}',str(commit or '')) or record.get('url')!=expected_url or not re.fullmatch(r'[0-9a-f]{64}\.zip',str(record.get('file',''))) or not re.fullmatch('[0-9a-f]{64}',str(record.get('sha256',''))):
        raise ValueError('Exact repository notice origin required')
    path=cache/record['file']
    if path.is_symlink() or digest(path)!=record['sha256']: raise ValueError('Repository source hash mismatch')
    results={}
    with zipfile.ZipFile(path) as archive:
        roots={member.filename.split('/')[0] for member in archive.infolist()}
        if len(roots)!=1 or not next(iter(roots)).endswith('-'+commit): raise ValueError('Repository archive commit mismatch')
        prefix=next(iter(roots))+'/'
        for name,notice in entry.get('notices',{}).items():
            relative=notice.get('sourceEntry',''); parsed=PurePosixPath(relative)
            if not re.fullmatch(r'[0-9a-f]{24}\.txt',name) or parsed.is_absolute() or '..' in parsed.parts or parsed.as_posix()!=relative or '\\' in relative or ':' in relative or notice.get('repository')!=repository or notice.get('commit')!=commit:
                raise ValueError('Unsafe repository notice member')
            members=[member for member in archive.infolist() if member.filename==prefix+relative and not member.is_dir()]
            if len(members)!=1 or members[0].file_size>1024*1024: raise ValueError('Missing/duplicate/oversized repository notice')
            data=archive.read(members[0])
            if hashlib.sha256(data).hexdigest()!=notice.get('sha256'): raise ValueError('Repository notice content mismatch')
            results[name]=(data,notice)
    if not results: raise ValueError('Empty recovered repository notice set')
    return results


def obtain_inputs(cache,inventory_path,online=False):
    inventory=json.loads(inventory_path.read_text())
    from release_inputs import ROOT
    policy=json.loads((ROOT/'packaging/deno-cargo-policy.json').read_text())
    if digest(inventory_path)!=policy.get('repositoryNoticeInputSha256') or inventory.get('cargoLockSha256')!=policy['cargoLockSha256'] or inventory.get('redistributionApproved') is not False or inventory.get('licenceApplicabilityProven') is not False or inventory.get('binaryDependencyClosureComplete') is not False or inventory.get('errors')!=[]:
        raise ValueError('Unapproved repository source selection')
    cache.mkdir(parents=True,exist_ok=True)
    for entry in inventory['packages']:
        if entry['status']!='notices-found': continue
        record=entry['sourceArchive']; repo=safe_repository(entry['repository']); commit=entry['vcs'].get('git',{}).get('sha1')
        if not repo or not re.fullmatch('[0-9a-f]{40}',str(commit or '')) or record.get('url')!='https://codeload.github.com/'+repo.removeprefix('https://github.com/')+'/zip/'+commit or not re.fullmatch(r'[0-9a-f]{64}\.zip',str(record.get('file',''))) or not re.fullmatch('[0-9a-f]{64}',str(record.get('sha256',''))):
            raise ValueError('Unpinned repository source input')
        path=cache/record['file']
        if path.is_symlink(): raise ValueError('Linked repository cache input')
        if not path.exists():
            if not online: raise ValueError('Missing exact repository source input')
            partial=path.with_suffix('.partial'); size=0
            with urlopen(record['url'],timeout=90) as response,partial.open('xb') as stream:
                while True:
                    data=response.read(1024*1024)
                    if not data: break
                    size+=len(data)
                    if size>256*1024*1024: raise ValueError('Oversized repository source input')
                    stream.write(data)
            if digest(partial)!=record['sha256']: raise ValueError('Downloaded repository source mismatch')
            partial.rename(path)
        if not path.is_file() or digest(path)!=record['sha256']: raise ValueError('Changed repository source input')
    return inventory


def collect(inputs,registry_cache,repository_cache,inventory_path,output,online=False):
    source,raw,packages=source_pins(inputs); expected={(item['name'],item['version']):item for item in packages}
    inventory=obtain_inputs(repository_cache,inventory_path,online)
    if inventory.get('redistributionApproved') is not False or inventory.get('licenceApplicabilityProven') is not False or inventory.get('binaryDependencyClosureComplete') is not False or inventory.get('errors')!=[] or not isinstance(inventory.get('packages'),list):
        raise ValueError('Repository evidence must retain incomplete applicability/closure status')
    if output.exists(): raise ValueError('Fresh repository replay output required')
    origins={}; aliases={}
    for item in packages:
        record=origin(item,obtain(item,registry_cache))
        origins[(item['name'],item['version'])]=record
        commit=record['vcs'].get('git',{}).get('sha1')
        if record['repository'] and commit: aliases.setdefault(commit,set()).add(record['repository'])
    output.mkdir(parents=True); rows=[]; notice_files={}; seen=set()
    for entry in inventory['packages']:
        key=(entry.get('name'),entry.get('version'))
        if key not in expected or key in seen or entry.get('status') not in ('notices-found','unresolved'): raise ValueError('Unknown/duplicate repository package evidence')
        seen.add(key); original=origins[key]
        if entry.get('vcs')!=original['vcs']: raise ValueError('Repository VCS evidence differs from exact crate')
        record={'name':key[0],'version':key[1],'status':entry['status'],'reason':entry.get('reason'),
            'repository':entry.get('repository'),'vcs':original['vcs'],'notices':{},'licenceApplicabilityProven':False}
        if entry['status']=='notices-found':
            repo=safe_repository(entry['repository']); commit=original['vcs'].get('git',{}).get('sha1')
            if repo!=original['repository'] and aliases.get(commit,set())!={repo}: raise ValueError('Unsubstantiated repository inference')
            for name,(data,notice) in inspect_notice_archive(expected[key],entry,repository_cache).items():
                target=output/'notices'/name; target.parent.mkdir(exist_ok=True)
                if not target.exists(): target.write_bytes(data)
                elif target.read_bytes()!=data: raise ValueError('Conflicting shared source notice')
                record['notices'][name]=notice; notice_files[name]=digest(target)
            record['sourceArchive']=entry['sourceArchive']; record['repositoryInference']=entry.get('repositoryInference')
        rows.append(record)
    report={'schema':1,'sourceInput':source,'cargoLockSha256':hashlib.sha256(raw).hexdigest(),'inputInventorySha256':digest(inventory_path),
        'packages':rows,'noticeFiles':notice_files,'recoveredPackageCount':sum(item['status']=='notices-found' for item in rows),
        'unresolvedPackages':[{'name':item['name'],'version':item['version'],'reason':item['reason']} for item in rows if item['status']=='unresolved'],
        'redistributionApproved':False,'licenceApplicabilityProven':False,'binaryDependencyClosureComplete':False,
        'scope':'Exact registry/VCS/source archive/notice bytes linked; ancestor notice applicability and actual binary shipment remain separate review questions'}
    (output/'repository-notice-inventory.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'recoveredPackages':report['recoveredPackageCount'],'noticeFiles':len(notice_files),'unresolved':len(report['unresolvedPackages'])}))
    return report


def validate_evidence(folder):
    report=json.loads((folder/'repository-notice-inventory.json').read_text())
    if report.get('schema')!=1 or report.get('redistributionApproved') is not False or report.get('licenceApplicabilityProven') is not False or report.get('binaryDependencyClosureComplete') is not False:
        raise ValueError('Repository notice evidence cannot grant approval or applicability')
    from release_inputs import ROOT
    policy=json.loads((ROOT/'packaging/deno-cargo-policy.json').read_text())
    if report.get('inputInventorySha256')!=policy.get('repositoryNoticeInputSha256') or report.get('cargoLockSha256')!=policy['cargoLockSha256'] or report.get('sourceInput',{}).get('sha256')!=policy['denoSourceSha256']:
        raise ValueError('Repository/Cargo evidence binding mismatch')
    locked=json.loads((ROOT/'packaging/repository-notice-inputs.lock.json').read_text())
    selected={(row['name'],row['version']):row for row in locked['packages']}
    rows=report.get('packages',[]); seen=set()
    for row in rows:
        key=(row.get('name'),row.get('version'))
        if key in seen or key not in selected or row.get('licenceApplicabilityProven') is not False:
            raise ValueError('Unknown/duplicate/approved repository evidence row')
        seen.add(key); expected=selected[key]
        for field in ('status','repository','vcs','reason'):
            if row.get(field)!=expected.get(field): raise ValueError('Repository evidence selection changed')
        if row['status']=='notices-found' and (row.get('sourceArchive')!=expected.get('sourceArchive') or row.get('notices')!=expected.get('notices')):
            raise ValueError('Recovered repository evidence origin changed')
    if seen!=set(selected) or report.get('recoveredPackageCount')!=sum(row['status']=='notices-found' for row in rows):
        raise ValueError('Repository evidence omitted source rows')
    paths=list((folder/'notices').rglob('*'))
    if any(path.is_symlink() for path in paths) or {path.name:digest(path) for path in paths if path.is_file()}!=report.get('noticeFiles'):
        raise ValueError('Changed/missing recovered repository notices')
    expected={name:item['sha256'] for row in report['packages'] for name,item in row.get('notices',{}).items()}
    if expected!=report['noticeFiles']: raise ValueError('Recovered notice origin inventory mismatch')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','registry-cache','repository-cache','output'): parser.add_argument('--'+name,type=Path,required=True)
    from release_inputs import ROOT
    parser.add_argument('--inventory',type=Path,default=ROOT/'packaging/repository-notice-inputs.lock.json')
    parser.add_argument('--online',action='store_true')
    args=parser.parse_args(); collect(args.inputs.resolve(),args.registry_cache.resolve(),args.repository_cache.resolve(),args.inventory.resolve(),args.output.resolve(),args.online)
