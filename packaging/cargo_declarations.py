"""Retain published licence declarations, supplied attribution and exact source archives."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import tomllib
from release_inputs import ROOT,digest


def standard_terms(root=ROOT):
    root=Path(root); lock=json.loads((root/'packaging/cargo-standard-terms.lock.json').read_text())
    if lock.get('schema')!=1 or lock.get('sourceRelease')!='spdx/license-list-data v3.20' or not isinstance(lock.get('files'),list):
        raise ValueError('Exact standard licence reference lock required')
    result={}
    for item in lock['files']:
        identifier=item.get('id'); filename=item.get('file','')
        if identifier not in {'MIT','Apache-2.0','CC0-1.0'} or identifier in result or filename!='SPDX-'+identifier+'.txt' or item.get('url')!='https://raw.githubusercontent.com/spdx/license-list-data/v3.20/text/'+identifier+'.txt':
            raise ValueError('Unsupported/duplicate standard licence reference')
        path=root/'packaging/source-metadata'/filename
        if path.is_symlink() or not path.is_file() or not re.fullmatch('[0-9a-f]{64}',str(item.get('sha256',''))) or type(item.get('bytes')) is not int or not 0<item['bytes']<100000 or path.stat().st_size!=item['bytes'] or digest(path)!=item['sha256']:
            raise ValueError('Missing/changed standard licence reference')
        result[identifier]=(item,path)
    if set(result)!={'MIT','Apache-2.0','CC0-1.0'}: raise ValueError('Incomplete standard licence references')
    return result


def declaration(item,archive_path):
    if archive_path.is_symlink() or digest(archive_path)!=item['sha256']:
        raise ValueError('Source archive changed before declaration inspection')
    prefix=item['name']+'-'+item['version']+'/'
    with tarfile.open(archive_path) as archive:
        members=archive.getmembers(); manifests=[m for m in members if m.name==prefix+'Cargo.toml' and m.isfile()]
        if len(manifests)!=1 or manifests[0].size>2*1024*1024: raise ValueError('Exact bounded upstream manifest required')
        raw=archive.extractfile(manifests[0]).read(); package=tomllib.loads(raw.decode()).get('package',{})
        if package.get('name')!=item['name'] or package.get('version')!=item['version'] or package.get('license')!=item.get('declaredLicence') or package.get('license-file')!=item.get('declaredLicenceFile'):
            raise ValueError('Upstream licence declaration differs from source inventory')
        statements=[]; seen=set(); read_files=0
        for member in members:
            if not member.isfile() or not member.name.startswith(prefix): continue
            relative=PurePosixPath(member.name.removeprefix(prefix))
            if relative.is_absolute() or '..' in relative.parts or '\\' in str(relative) or ':' in str(relative):
                raise ValueError('Unsafe source member in attribution inspection')
            if relative.suffix.lower() not in {'.rs','.c','.h','.cpp','.cc','.hpp','.md','.txt','.toml','.py','.js','.ts'} and relative.name not in {'AUTHORS','COPYRIGHT','LICENSE','LICENCE','NOTICE','COPYING'}: continue
            if member.size>16*1024*1024: raise ValueError('Oversized source prevents complete attribution inspection')
            data=archive.extractfile(member).read()
            try: text=data.decode('utf-8')
            except UnicodeDecodeError: continue  # Original complete source remains supplied, bytes unchanged.
            read_files+=1
            for number,line in enumerate(text.splitlines(),1):
                if re.search(r'\bcopyright\b|\(c\)\s+\d{4}|©\s*\d{4}',line,re.I) and line not in seen:
                    statements.append({'sourceEntry':member.name,'sourceSha256':hashlib.sha256(data).hexdigest(),'line':number,'verbatimLine':line})
                    seen.add(line)
        return {'name':item['name'],'version':item['version'],'archiveSha256':item['sha256'],
            'declaredLicence':package.get('license'),'declaredLicenceFile':package.get('license-file'),
            'upstreamAuthorsMetadata':package.get('authors'),'repository':package.get('repository'),
            'originalCargoManifest':raw.decode(),'manifestSha256':hashlib.sha256(raw).hexdigest(),
            'suppliedCopyrightStatements':statements,'utf8TextFilesInspected':read_files,
            'interpretation':'Generated record of the exact published package declaration and verbatim supplied source lines. Authors metadata is not relabelled as a copyright notice. No year, holder, missing NOTICE or additional grant is invented. Standard licence texts and all unchanged source archives accompany these records; existing original notices remain retained separately.'}


def collect(rows,cache,output):
    folder=output/'declarations'; folder.mkdir()
    sources=output/'sources/registry'; sources.mkdir(parents=True)
    declarations={}; source_files={}
    for item in rows:
        path=cache/item['crateFile']
        if path.is_symlink() or not path.is_file() or digest(path)!=item['sha256']:
            raise ValueError('Missing/changed corresponding Cargo source')
        target=sources/item['crateFile']; shutil.copy2(path,target)
        source_files[target.relative_to(output).as_posix()]=digest(target)
        if not item['packageRootNoticeAvailable']:
            record=declaration(item,path); filename=item['crateFile'].removesuffix('.crate')+'.json'
            target=folder/filename; target.write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
            declarations[filename]={'sha256':digest(target),'name':item['name'],'version':item['version'],
                'declaredLicence':item['declaredLicence'],'archiveSha256':item['sha256'],
                'scope':'upstream declaration plus supplied source attribution; generated record, not an original standalone licence'}
    for identifier,(item,path) in standard_terms().items():
        filename='STANDARD-'+identifier+'.txt'; target=folder/filename; shutil.copy2(path,target)
        declarations[filename]={'sha256':digest(target),'name':identifier,'version':'SPDX 3.20','declaredLicence':identifier,
            'sourceUrl':item['url'],'scope':'unmodified standard reference text; template copyright fields are not original package attribution'}
    return declarations,source_files


def validate(report,folder):
    rows=report['packages']; observed=report.get('declarationNotices'); sources=report.get('sourceArchives')
    if not isinstance(observed,dict) or not isinstance(sources,dict): raise ValueError('Cargo declaration/source evidence required')
    expected_sources={'sources/registry/'+row['crateFile']:row['sha256'] for row in rows}
    if sources!=expected_sources: raise ValueError('Cargo source archives missing or changed')
    for name,checksum in sources.items():
        path=folder/name
        if path.is_symlink() or not path.is_file() or digest(path)!=checksum: raise ValueError('Changed corresponding Cargo source')
    expected={row['crateFile'].removesuffix('.crate')+'.json':row for row in rows if not row['packageRootNoticeAvailable']}
    references=standard_terms(); names=set(expected)|{'STANDARD-'+key+'.txt' for key in references}
    if set(observed)!=names or {p.name for p in (folder/'declarations').iterdir() if p.is_file()}!=names:
        raise ValueError('Cargo declaration inventory incomplete')
    for name,item in observed.items():
        path=folder/'declarations'/name
        if path.is_symlink() or not path.is_file() or digest(path)!=item.get('sha256'): raise ValueError('Changed Cargo attribution record')
        if name in expected:
            row=expected[name]; record=json.loads(path.read_text(encoding='utf-8'))
            metadata=tomllib.loads(record['originalCargoManifest']).get('package',{})
            if any(record.get(key)!=row[key] for key in ('name','version','declaredLicence','declaredLicenceFile')) or record.get('archiveSha256')!=row['sha256'] or hashlib.sha256(record['originalCargoManifest'].encode()).hexdigest()!=record.get('manifestSha256') or metadata.get('authors')!=record.get('upstreamAuthorsMetadata'):
                raise ValueError('Original declaration and source binding mismatch')
        else:
            identifier=name.removeprefix('STANDARD-').removesuffix('.txt')
            if digest(path)!=references[identifier][0]['sha256']: raise ValueError('Standard reference changed')
    return {'fullRegistrySourcesSupplied':len(sources),'generatedDeclarationRecords':len(expected),
        'scope':'Complete exact source-lock registry archives, not a binary-inclusion claim or automatic licensing approval.'}
