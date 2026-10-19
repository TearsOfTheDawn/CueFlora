"""Compact hash-verified CI handoff; measurements never create approval records."""
import argparse
import json
import os
import re
from pathlib import Path, PurePosixPath
import shutil
import subprocess

from approval_evidence import validate_bindings
from redistribution_assessment import ledger_identity
from release_inputs import digest

EXTRA = (
    'readiness.json','release-gates.json','source-export/source-audit.json',
    'source-bundle/source-bundle-report.json','setup-1/bundle/release.json',
    'downloader-build/downloader-build.json','curl-source-evidence/curl-source-evidence.json',
    'cargo-notice-evidence/cargo-notice-inventory.json','repository-notice-evidence/repository-notice-inventory.json',
    'v8-notice-evidence/v8-notice-evidence.json','interpreter-component-notices/interpreter-component-notices.json',
    'licence-evidence/Deno-2.9.7-LICENSE.md','licence-evidence/CPython-3.13.15-source.zip',
    'licence-evidence/python-build-standalone-20260814-source.zip','tool-dependency-audit/tool-dependency-audit.json')


def ordinary(root, name):
    if not isinstance(name,str) or not name or '\\' in name or ':' in name:
        raise ValueError('Unsafe candidate path')
    relative=PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or relative.as_posix()!=name:
        raise ValueError('Unsafe candidate path')
    path=root/name
    if path.resolve()!=path or not path.is_file(): raise ValueError('Missing or linked candidate file')
    return path


def pack(preparation, output):
    preparation=Path(preparation).resolve(); output=Path(output).resolve()
    readiness=json.loads((preparation/'readiness.json').read_text())
    if readiness.get('engineeringPassed') is not True or readiness.get('effectiveConfiguration',{}).get('distribution') != 'github':
        raise ValueError('Passed GitHub engineering candidate required')
    validate_bindings(readiness['artifactBindings'])
    if not re.fullmatch(r'\d+\.\d+\.\d+',str(readiness['effectiveConfiguration'].get('version',''))):
        raise ValueError('Exact candidate version required')
    if output.exists(): raise ValueError('Fresh candidate handoff directory required')
    assets=json.loads((preparation/'release-assets/RELEASE_ASSETS.json').read_text())
    if assets['artifacts'] != readiness['artifactBindings']: raise ValueError('Candidate asset bindings differ')
    output.mkdir(parents=True)
    names=set(EXTRA)
    if (preparation/'auth-native-notices/auth-notice-evidence.json').is_file():names.add('auth-native-notices/auth-notice-evidence.json')
    names.update('release-assets/'+name for name in assets['files'])
    names.add('release-assets/RELEASE_ASSETS.json')
    for directory in ('public-pages','verification','capability-verification','credential-verification','auth-verification','installer-verification','lifecycle'):
        # Only top-level measured reports/logs: exclude restored runtimes,
        # synthetic installation records and any nested test payloads.
        names.update(path.relative_to(preparation).as_posix() for path in (preparation/directory).glob('*') if path.is_file() and path.suffix in ('.json','.log','.html','.css'))
    names.add('public-pages/.nojekyll')
    for name in sorted(names):
        source=ordinary(preparation,name); target=output/name
        target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,target)
        if digest(source)!=digest(target): raise ValueError('Candidate handoff copy changed')
    for name,checksum in assets['files'].items():
        if digest(ordinary(output,'release-assets/'+name)) != checksum:
            raise ValueError('Candidate release asset mismatch')
    terms=output/'publisher-decisions/evidence/setup-terms.json'; terms.parent.mkdir(parents=True)
    result=subprocess.run([str(preparation/'setup-1/dist/CueFlora Setup.exe'),'terms','--report',str(terms)],capture_output=True,timeout=180)
    if result.returncode or json.loads(terms.read_text()).get('applied') is not False:
        raise ValueError('Frozen Setup terms evidence failed')
    files={path.relative_to(output).as_posix():digest(path) for path in sorted(output.rglob('*')) if path.is_file()}
    ledger=json.loads((output/'release-assets/release-ledger/dependency-ledger.json').read_text())
    summary={'schema':1,'version':readiness['effectiveConfiguration']['version'],'artifacts':readiness['artifactBindings'],
        'sourceCommit':os.environ.get('GITHUB_SHA'),'workflowRunId':os.environ.get('GITHUB_RUN_ID'),
        'sourceArchiveSha256':readiness['sourceArchive']['archiveSha256'],'ledgerSha256':ledger_identity(ledger),
        'ledgerFileSha256':digest(output/'release-assets/release-ledger/dependency-ledger.json'),
        'unresolvedEvidence':ledger.get('unresolvedEvidence'),'unassignedRuntimeFiles':ledger.get('unassignedRuntimeFiles'),
        'sourceBundleSha256':assets['files']['CueFlora-third-party-sources.zip'],
        'evidenceHashes':{name:files[name] for name in (*EXTRA,'publisher-decisions/evidence/setup-terms.json')},
        'engineeringPassed':True,'publicationApproved':False,'published':False,
        'scope':'Exact measured candidate and evidence, requiring separate scoped review and publisher decisions.'}
    (output/'CANDIDATE_SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    files['CANDIDATE_SUMMARY.json']=digest(output/'CANDIDATE_SUMMARY.json')
    (output/'CANDIDATE_INVENTORY.json').write_text(json.dumps({'schema':1,'artifacts':readiness['artifactBindings'],'files':files},indent=2)+'\n',encoding='utf-8')
    print('CUEFLORA_CANDIDATE_SUMMARY='+json.dumps(summary,separators=(',',':')),flush=True)
    return summary


def restore(candidate):
    root=Path(candidate).resolve()
    inventory=json.loads(ordinary(root,'CANDIDATE_INVENTORY.json').read_text())
    if any(path.is_symlink() or path.resolve()!=path for path in root.rglob('*')):
        raise ValueError('Linked candidate files/directories rejected')
    validate_bindings(inventory['artifacts'])
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if inventory.get('schema') != 1 or actual != set(inventory['files']) | {'CANDIDATE_INVENTORY.json'}:
        raise ValueError('Incomplete, extra or malformed handoff files')
    for name,checksum in inventory['files'].items():
        if digest(ordinary(root,name)) != checksum: raise ValueError('Candidate handoff hash mismatch')
    readiness=json.loads((root/'readiness.json').read_text())
    if readiness['artifactBindings'] != inventory['artifacts']: raise ValueError('Handoff binding mismatch')
    if readiness.get('effectiveConfiguration',{}).get('distribution') != 'github' or not re.fullmatch(r'\d+\.\d+\.\d+',str(readiness['effectiveConfiguration'].get('version',''))) or readiness.get('artifacts',{}).get('archive') != 'CueFlora-Windows-x64-Chrome.zip':
        raise ValueError('Invalid GitHub candidate version or archive path')
    copies={'source-export/CueFlora-source.zip':'release-assets/CueFlora-source.zip',
        'source-bundle/CueFlora-third-party-sources.zip':'release-assets/CueFlora-third-party-sources.zip',
        'release-ledger/dependency-ledger.json':'release-assets/release-ledger/dependency-ledger.json',
        'release-ledger/CONSOLIDATED_NOTICES.txt':'release-assets/release-ledger/CONSOLIDATED_NOTICES.txt',
        'delivery/CueFlora Setup/CueFlora Setup.exe':'release-assets/CueFlora-'+readiness['effectiveConfiguration']['version']+'-Setup.exe',
        'delivery/CueFlora Setup/CueFlora-Chrome-extension.zip':'release-assets/CueFlora-Chrome-extension.zip',
        'delivery/'+readiness['artifacts']['archive']:'release-assets/CueFlora-'+readiness['effectiveConfiguration']['version']+'-Windows-x64.zip'}
    for target,source in copies.items():
        path=root/target
        if path.exists(): raise ValueError('Candidate restore requires a fresh handoff')
        path.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(ordinary(root,source),path)
    return root


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preparation',type=Path); parser.add_argument('--output',type=Path)
    parser.add_argument('--restore',type=Path)
    args=parser.parse_args()
    if args.restore: restore(args.restore)
    elif args.preparation and args.output: pack(args.preparation,args.output)
    else: parser.error('Choose --restore or both --preparation and --output')
