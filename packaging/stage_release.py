"""Stage an exact reviewed helper prerelease; never submit or approve the Store item."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from approval_evidence import validate_bindings
from release_inputs import digest
from release_readiness import assess


def ordinary(root, name, expected):
    if not isinstance(name,str) or not name or '\\' in name or ':' in name:
        raise ValueError('Unsafe release asset path')
    path=root/name
    if path.resolve()!=path or not path.is_file() or not path.is_relative_to(root):
        raise ValueError('Missing, linked or escaping release asset')
    if not re.fullmatch('[0-9a-f]{64}',str(expected)) or digest(path)!=expected:
        raise ValueError('Release asset hash mismatch')
    return path


def plan(preparation, configuration, approvals, evidence_root, target_commit):
    root=Path(preparation).resolve()
    if not isinstance(target_commit,str) or not re.fullmatch('[0-9a-f]{40}',target_commit):
        raise ValueError('Exact public source commit required; branches are not release inputs')
    engineering=json.loads((root/'readiness.json').read_text())
    source=json.loads((root/'source-export/source-audit.json').read_text())
    ledger=json.loads((root/'release-ledger/dependency-ledger.json').read_text())
    readiness=assess(engineering,source,ledger,configuration,approvals,evidence_root,root)
    if not readiness['helperDownloadReady']:
        raise ValueError('Helper redistribution gates unresolved: '+', '.join(readiness['helperRemaining']))
    bindings=validate_bindings(engineering['artifactBindings'])
    version=engineering['effectiveConfiguration']['version']
    repository=configuration.get('repositoryUrl')
    if not re.fullmatch(r'\d+\.\d+\.\d+',str(version)) or not isinstance(repository,str) or not re.fullmatch(r'https://github\.com/[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+',repository):
        raise ValueError('Exact version and real GitHub repository required')
    assets_root=root/'release-assets'
    manifest=json.loads((assets_root/'RELEASE_ASSETS.json').read_text())
    if manifest.get('schema')!=1 or manifest.get('version')!=version or manifest.get('artifacts')!=bindings or not isinstance(manifest.get('files'),dict):
        raise ValueError('Release assets do not match the reviewed candidate')
    for name,expected in manifest['files'].items():
        ordinary(assets_root,name,expected)
    sources=json.loads((root/'source-bundle/source-bundle-report.json').read_text())
    files={
        'CueFlora-'+version+'-Setup.exe':('CueFlora-'+version+'-Setup.exe',bindings['setupSha256']),
        'CueFlora-Chrome-store-upload.zip':('CueFlora-Chrome-store-upload.zip',bindings['extensionSha256']),
        'CueFlora-source.zip':('CueFlora-source.zip',source['archiveSha256']),
        'CueFlora-third-party-sources.zip':('CueFlora-third-party-sources.zip',sources['archiveSha256']),
        'CueFlora-CONSOLIDATED-NOTICES.txt':('release-ledger/CONSOLIDATED_NOTICES.txt',None),
        'CueFlora-dependency-ledger.json':('release-ledger/dependency-ledger.json',None)}
    assets=[]
    for public_name,(name,expected) in files.items():
        actual=manifest['files'].get(name)
        if actual is None or (expected is not None and actual!=expected):
            raise ValueError('Required binary, notice or corresponding-source identity differs')
        path=ordinary(assets_root,name,actual)
        assets.append({'name':public_name,'path':str(path),'sha256':actual,'bytes':path.stat().st_size})
    return {'schema':1,'version':version,'tag':'v'+version,
        'repository':repository.removeprefix('https://github.com/'),'targetCommit':target_commit,
        'artifacts':bindings,'assets':assets,'gates':readiness,
        'published':False,'storeSubmitted':False,'stableRelease':False,
        'interpretation':'Reviewed helper prerelease only. Store approval/screenshots are separate; required redistribution, security and authorization gates are not waived.'}


def execute(staging, confirmed_version=None):
    if confirmed_version!=staging['version']:
        raise ValueError('Exact-version execution confirmation required')
    executable=shutil.which('gh')
    if executable is None:
        raise ValueError('Authenticated GitHub CLI is unavailable; no release was uploaded')
    for item in staging['assets']:
        path=Path(item['path'])
        if path.resolve()!=path or not path.is_file() or path.stat().st_size!=item['bytes'] or digest(path)!=item['sha256']:
            raise ValueError('Reviewed release asset changed before upload')

    def command(arguments):
        return subprocess.run([executable,*arguments],capture_output=True,text=True,timeout=600,check=False)

    repository=staging['repository']; tag=staging['tag']
    # A failed read is not assumed to mean absence. Only an explicit 404 permits
    # creation. Never take over another release or an existing Git tag.
    for endpoint in ('releases/tags/'+tag,'git/ref/tags/'+tag):
        result=command(['api','repos/'+repository+'/'+endpoint])
        if result.returncode==0:
            raise ValueError('Release or tag already exists; no overwrite or takeover is permitted')
        if 'HTTP 404' not in result.stderr:
            raise RuntimeError('GitHub preflight failed; check account access without sharing credentials')
    commit=command(['api','repos/'+repository+'/git/commits/'+staging['targetCommit']])
    if commit.returncode or json.loads(commit.stdout).get('sha')!=staging['targetCommit']:
        raise RuntimeError('Release target commit is unavailable or changed')
    # Bind the requested target to every file of the exact candidate source,
    # not just to a publisher-supplied commit label.
    source_asset=next(item for item in staging['assets'] if item['name']=='CueFlora-source.zip')
    import hashlib
    import zipfile
    with zipfile.ZipFile(source_asset['path']) as archive:
        expected={}
        for item in archive.infolist():
            if item.is_dir(): continue
            if item.filename in expected: raise ValueError('Duplicate source archive entry')
            data=archive.read(item)
            expected[item.filename]=(hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),
                '100755' if item.filename.endswith('.sh') else '100644')
    tree_sha=json.loads(commit.stdout).get('tree',{}).get('sha')
    if not isinstance(tree_sha,str) or not re.fullmatch('[0-9a-f]{40}',tree_sha):
        raise RuntimeError('Release commit has no exact source tree')
    tree=command(['api','repos/'+repository+'/git/trees/'+tree_sha+'?recursive=1'])
    if tree.returncode: raise RuntimeError('Cannot verify the exact public source tree')
    observed=json.loads(tree.stdout)
    actual={item['path']:(item['sha'],item['mode']) for item in observed.get('tree',[]) if item.get('type')=='blob'}
    if observed.get('truncated') is not False or actual!=expected:
        raise ValueError('Public commit does not exactly match the reviewed source archive')
    with tempfile.TemporaryDirectory(prefix='cueflora-review-staging-') as directory:
        temporary=Path(directory)
        notes=temporary/'RELEASE_NOTES.md'
        notes.write_text('CueFlora '+staging['version']+' Windows x64 / Chrome helper review prerelease.\n\n'
            'The installer is unsigned. The Chrome Store item is separate and may not yet be available. '
            'AI services are not included: compatible transcription/chat-completions APIs must be supplied by the user. '
            'Automated checks are not clean-machine or real-browser acceptance.\n\n'
            'Corresponding sources and third-party notices accompany this installer. '
            'Do not disable security software. Checksums do not guarantee software safety.\n',encoding='utf-8')
        checksums=temporary/'CueFlora-SHA256SUMS.txt'
        checksums.write_text(''.join(item['sha256']+'  '+item['name']+'\n' for item in staging['assets']),encoding='utf-8')
        # gh's PATH#LABEL changes a display label, not the asset filename.
        # Stage real flat filenames so documented download URLs are correct.
        uploads=[]
        for item in staging['assets']:
            target=temporary/item['name']; shutil.copyfile(item['path'],target)
            if digest(target)!=item['sha256']: raise ValueError('Staged asset copy changed')
            uploads.append(str(target))
        uploads.append(str(checksums))
        result=command(['release','create',tag,'--repo',repository,'--target',staging['targetCommit'],
            '--draft','--prerelease','--title','CueFlora '+staging['version']+' — Windows/Chrome review candidate',
            '--notes-file',str(notes),*uploads])
        if result.returncode:
            raise RuntimeError('Draft upload failed; an incomplete draft may remain. No public release was requested')
        downloaded=temporary/'downloaded'; downloaded.mkdir()
        expected_downloads=[*staging['assets'],{'name':checksums.name,'sha256':digest(checksums)}]
        for item in expected_downloads:
            result=command(['release','download',tag,'--repo',repository,'--pattern',item['name'],'--dir',str(downloaded)])
            if result.returncode or not (downloaded/item['name']).is_file() or digest(downloaded/item['name'])!=item['sha256']:
                raise RuntimeError('Draft asset verification failed; draft was not made public')
        # Create the tag atomically only after verifying the draft. A concurrent
        # pre-existing tag is refused by GitHub, never silently adopted.
        result=command(['api','repos/'+repository+'/git/refs','--method','POST',
            '-f','ref=refs/tags/'+tag,'-f','sha='+staging['targetCommit']])
        if result.returncode or json.loads(result.stdout).get('object',{}).get('sha')!=staging['targetCommit']:
            raise RuntimeError('Exact tag creation failed; draft remains unpublished')
        result=command(['release','edit',tag,'--repo',repository,'--draft=false','--prerelease','--latest=false'])
        if result.returncode:
            raise RuntimeError('Prerelease publication response failed; inspect the remote state before retrying')
    return {**staging,'published':True,'url':'https://github.com/'+repository+'/releases/tag/'+tag,
        'anonymousDownloadVerification':'Not performed by this command; verify public download bytes before updating the website.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('preparation','configuration','approvals','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--target-commit',required=True)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--confirm-version')
    args=parser.parse_args()
    if args.output.exists(): parser.error('Fresh report output required')
    staging=plan(args.preparation,json.loads(args.configuration.read_text()),
        json.loads(args.approvals.read_text()),args.approvals.parent,args.target_commit)
    if args.execute: staging=execute(staging,args.confirm_version)
    with args.output.open('x',encoding='utf-8') as stream: json.dump(staging,stream,indent=2)
