"""Execute headless extraction/checks only. Never install/register/open windows."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / 'native'))
from cueflora_setup.bundle import digest


def verify_embedded(value, runtime, expected_release):
    metadata=json.loads((runtime/'runtime-manifest.json').read_text(encoding='utf-8'))
    from cueflora_setup.package_policy import validate_package
    validate_package(runtime,expected_release,metadata,['chrome'])
    if value.get('release')!=expected_release or expected_release['runtimeInventorySha256']!=digest(runtime/'runtime-manifest.json'):
        raise ValueError('Embedded configuration or runtime differs from expected package')
    if value.get('inventory')!=metadata: raise ValueError('Embedded complete runtime inventory differs')


def verify(executable, runtime, output, release=None):
    release=release or executable.parent.parent/'bundle/release.json'
    expected_release=json.loads(release.read_text(encoding='utf-8'))
    output = output.resolve()
    output.mkdir(parents=True,exist_ok=False)
    destination = output / 'Unicode Ω and spaces'
    destination.mkdir()
    executable_copy = destination / 'CueFlora Setup.exe'
    shutil.copy2(executable,executable_copy)
    environment = {key:value for key,value in os.environ.items() if key not in ('PYTHONHOME','PYTHONPATH','YT_DLP_PATH','FFMPEG_PATH','FFPROBE_PATH','DENO_PATH','CUEFLORA_EVIDENCE_DIR')}
    environment['PATH'] = str(Path(os.environ['SystemRoot']) / 'System32')
    results = {}
    for action in ['self-check','validate-package','detect']:
        report = output / (action + '.json')
        started = time.monotonic()
        result = subprocess.run([str(executable_copy),action,'--report',str(report)],env=environment,cwd=destination,
                                capture_output=True,timeout=180,check=True)
        if not report.is_file():
            raise ValueError('Missing headless installer report')
        value = json.loads(report.read_text(encoding='utf-8'))
        if value.get('error'):
            raise ValueError('Installer headless check failed')
        results[action] = {'seconds':round(time.monotonic()-started,2),'exitCode':result.returncode}
        if action == 'validate-package':
            verify_embedded(value,runtime,expected_release)
    # A malformed payload must fail non-graphically and write a bounded report.
    invalid = output / 'malformed-payload'
    invalid.mkdir()
    (invalid / 'runtime-manifest.json').write_text('{invalid',encoding='utf-8')
    report = output / 'failure.json'
    failure = subprocess.run([str(executable_copy),'validate-package','--payload',str(invalid),'--report',str(report)],
                             env=environment,cwd=destination,capture_output=True,timeout=180)
    if failure.returncode == 0 or not report.is_file() or json.loads(report.read_text())['valid'] is not False:
        raise ValueError('Invalid payload did not produce a headless failure report')
    results['malformed-payload'] = {'exitCode':failure.returncode, 'reported':True}
    results.update({'exeSha256':digest(executable_copy), 'restrictedPath':True, 'spaceUnicodePath':True,
                    'selfExtractionVerified':True,'guiOpened':False,'liveInstallation':False,'realBrowserRegistration':False})
    (output / 'installer-verification.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--setup',type=Path,required=True)
    parser.add_argument('--runtime',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--release',type=Path,help='Expected private or actual-identity public configuration, not a preview-only assumption')
    args = parser.parse_args()
    print(json.dumps(verify(args.setup,args.runtime,args.output,args.release),indent=2))
