"""Read-only original preservation and new-project isolation audit."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'native'))
from cueflora_setup.bundle import digest


def verify(baseline):
    baseline = json.loads(Path(baseline).read_text(encoding='utf-8'))
    original = Path(baseline['source'])
    changed = [item['path'] for item in baseline['files'] if not (original / item['path']).is_file() or digest(original / item['path']) != item['sha256']]
    environment = {**os.environ, 'GIT_OPTIONAL_LOCKS':'0'}
    status = subprocess.check_output(['git','status','--porcelain=v1'],cwd=original,env=environment,text=True).splitlines()
    if changed or status != baseline['gitStatus']:
        raise ValueError('Original source or Git status changed: ' + ', '.join(changed))
    if subprocess.check_output(['git','remote'],cwd=ROOT,env=environment,text=True).strip():
        raise ValueError('New project must have no inherited remote')
    if subprocess.check_output(['git','rev-list','--all'],cwd=ROOT,env=environment,text=True).strip():
        raise ValueError('Fresh baseline must not contain inherited commits')
    offenders = []
    for directory in ('entrypoints','utils','native','scripts','packaging'):
        for path in (ROOT / directory).rglob('*'):
            if path.suffix not in ('.ts','.py','.mjs','.json','.sh') or '__pycache__' in path.parts or path.name == 'verify_isolation.py' or path.name.startswith('test_') or '__tests__' in path.parts:
                continue
            text = path.read_text(encoding='utf-8')
            if any(token in text for token in ('SUBSTRATA_', 'substrata_', 'substrata_host', 'cjjpgncpjnddfbkfbnfjlcgpbnggnhcd')):
                offenders.append(path.relative_to(ROOT).as_posix())
    if offenders:
        raise ValueError('Operational Substrata identifiers remain: ' + ', '.join(offenders))
    if (ROOT / 'LICENSE.md').read_bytes() != (original / 'LICENSE.md').read_bytes():
        raise ValueError('Upstream MIT license changed')
    copied = {path for path in baseline['copied']}
    missing = [path for path in copied if not (ROOT / path.replace('substrata_host','cueflora_host').replace('substrata_setup','cueflora_setup')).is_file()]
    if missing:
        raise ValueError('Copied source missing: ' + ', '.join(missing))
    return {'originalFilesVerified':len(baseline['files']), 'copiedFilesAccountedFor':len(copied),
            'originalGitStatusUnchanged':True, 'upstreamLicenseUnchanged':True,
            'inheritedCommits':False,'inheritedRemotes':False,'operationalNamespaceIsolation':True,
            'liveInstallationTouched':False,'privateCapturesCopied':False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path,default=ROOT / 'artifacts/source-baseline.json')
    parser.add_argument('--report',type=Path,required=True)
    args = parser.parse_args()
    result = verify(args.baseline)
    with args.report.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2)
    print(json.dumps(result,indent=2))
