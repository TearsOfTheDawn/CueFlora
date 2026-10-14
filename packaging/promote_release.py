"""Plan, or explicitly authorize, promotion of a reviewed GitHub prerelease."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
from approval_evidence import verified_decisions
from release_readiness import assess
from release_inputs import digest


def promotion(preparation,configuration,approvals,evidence_root):
    engineering=json.loads((preparation/'readiness.json').read_text())
    source=json.loads((preparation/'source-export/source-audit.json').read_text())
    ledger=json.loads((preparation/'release-ledger/dependency-ledger.json').read_text())
    result=assess(engineering,source,ledger,configuration,approvals,evidence_root,preparation)
    if not result['publicReleaseReady']: raise ValueError('Public release gates unresolved: '+', '.join(result['remaining']))
    version=engineering['effectiveConfiguration']['version']
    if not re.fullmatch(r'\d+\.\d+\.\d+',version): raise ValueError('Invalid candidate version')
    repository=configuration.get('repositoryUrl')
    if not isinstance(repository,str) or not re.fullmatch(r'https://github\.com/[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+',repository):
        raise ValueError('Explicit real repository required')
    artifacts={preparation/'delivery/CueFlora Setup/CueFlora Setup.exe':engineering['artifactBindings']['setupSha256'],
        preparation/'delivery/CueFlora Setup/CueFlora-Chrome-store-upload.zip':engineering['artifactBindings']['extensionSha256']}
    for path,checksum in artifacts.items():
        if path.is_symlink() or digest(path)!=checksum: raise ValueError('Candidate bytes changed after review')
    source_bundle=json.loads((preparation/'source-bundle/source-bundle-report.json').read_text())
    remote_assets={'CueFlora-'+version+'-Setup.exe':engineering['artifactBindings']['setupSha256'],
        'CueFlora-Chrome-store-upload.zip':engineering['artifactBindings']['extensionSha256'],
        'CueFlora-source.zip':source['archiveSha256'],'CueFlora-third-party-sources.zip':source_bundle['archiveSha256']}
    for path,checksum in ((preparation/'source-export/CueFlora-source.zip',source['archiveSha256']),
        (preparation/'source-bundle/CueFlora-third-party-sources.zip',source_bundle['archiveSha256'])):
        if path.is_symlink() or digest(path)!=checksum: raise ValueError('Reviewed source archive changed')
    return {'version':version,'repository':repository.removeprefix('https://github.com/'),'artifacts':engineering['artifactBindings'],'remoteAssetHashes':remote_assets,
        'gates':result,'command':['gh','release','edit','v'+version,'--repo',repository.removeprefix('https://github.com/'),'--prerelease=false','--draft=false'],
        'storeAction':'Publisher manually publishes the approved staged Store item, with matching identity/version/package. No browser automation.',
        'credentialsRead':False,'published':False}


def execute(plan,confirmed_version=None):
    if confirmed_version!=plan['version']: raise ValueError('Explicit exact-version promotion confirmation required')
    if shutil.which('gh') is None: raise ValueError('GitHub CLI is unavailable; manual promotion instructions remain valid')
    # Inspect the existing prerelease and its remote asset bytes before changing
    # its status. Never create a release, upload replacement bytes or clobber tags.
    result=subprocess.run(['gh','release','view','v'+plan['version'],'--repo',plan['repository'],'--json','isDraft,isPrerelease,assets'],check=True,capture_output=True,text=True)
    remote=json.loads(result.stdout)
    if remote.get('isDraft') is True or remote.get('isPrerelease') is not True: raise ValueError('Expected an existing visible review prerelease, not another release state')
    expected=plan['remoteAssetHashes']
    import tempfile
    with tempfile.TemporaryDirectory(prefix='cueflora-remote-verify-') as directory:
        root=Path(directory)
        for name,checksum in expected.items():
            assets=[item for item in remote.get('assets',[]) if item.get('name')==name]
            if len(assets)!=1: raise ValueError('Required remote asset missing or ambiguous')
            subprocess.run(['gh','release','download','v'+plan['version'],'--repo',plan['repository'],'--pattern',name,'--dir',str(root)],check=True,capture_output=True)
            if digest(root/name)!=checksum: raise ValueError('Remote asset does not match reviewed bytes')
    subprocess.run(plan['command'],check=True)
    return {**plan,'published':True,'credentialsRead':'GitHub CLI uses publisher-controlled authentication; this script does not collect or store tokens'}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('preparation','configuration','approvals','output'): parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--confirm-version')
    args=parser.parse_args()
    plan=promotion(args.preparation.resolve(),json.loads(args.configuration.read_text()),json.loads(args.approvals.read_text()),args.approvals.parent.resolve())
    if args.execute: plan=execute(plan,args.confirm_version)
    with args.output.open('x',encoding='utf-8') as stream: json.dump(plan,stream,indent=2)
