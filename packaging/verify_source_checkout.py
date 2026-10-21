"""Run real suites/builds from a source ZIP, without Git/private source inputs."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import time
import zipfile
from source_export import export

ROOT = Path(__file__).resolve().parents[1]


def verify(cache, output):
    if output.exists(): raise ValueError('Fresh clean-source verification output required')
    output.mkdir(parents=True)
    source = export(output/'export')
    workspace = output/'checkout'; workspace.mkdir()
    with zipfile.ZipFile(output/'export/CueFlora-source.zip') as archive:
        for name in archive.namelist():
            path = PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name: raise ValueError('Unsafe source export')
        archive.extractall(workspace)
    for name in ('user.npmrc','global.npmrc'):
        (output/name).write_text('update-notifier=false\naudit=false\nfund=false\nregistry=https://registry.npmjs.org/\n')
    environment = {**os.environ,'NPM_CONFIG_USERCONFIG':str(output/'user.npmrc'),'NPM_CONFIG_GLOBALCONFIG':str(output/'global.npmrc')}
    environment.pop('CUEFLORA_PUBLIC_CONFIG',None)
    environment.pop('CUEFLORA_BUILD_PROFILE',None)
    # A clean-source check must not import private modules or enable captures.
    for name in ('PYTHONPATH','PYTHONHOME','PYTHONSTARTUP','PYTHONUSERBASE','NODE_PATH','NODE_OPTIONS',
            'CUEFLORA_PROVIDER_CONFIG','CUEFLORA_EVIDENCE_DIR','YT_DLP_PATH','FFMPEG_PATH','FFPROBE_PATH','DENO_PATH',
            'CUEFLORA_DEV_YT_DLP_PATH','CUEFLORA_DEV_FFMPEG_PATH','CUEFLORA_DEV_FFPROBE_PATH','CUEFLORA_DEV_DENO_PATH'):
        environment.pop(name,None)
    environment['PYTHONNOUSERSITE'] = '1'
    npm = ['cmd.exe','/d','/c','npm'] if os.name=='nt' else ['npm']
    checks = [('npm-ci',npm+['ci','--offline','--cache',str(cache),'--no-audit','--no-fund'],workspace)]
    checks += [(name,npm+['run',name],workspace) for name in ('typecheck','test','build:chrome','build:firefox')]
    checks += [('native',[sys.executable,'-m','unittest','cueflora_setup.test_setup','cueflora_setup.test_maintenance','cueflora_host.test_credentials',
        'cueflora_host.test_provider_check','cueflora_host.test_deno','cueflora_host.test_runtime_tools','cueflora_host.test_controlled_evidence',
        'cueflora_host.test_audio_preparation','cueflora_host.test_translate','cueflora_host.test_whisper_regressions','cueflora_host.test_evidence',
        'cueflora_host.test_chatgpt','cueflora_host.test_updates','cueflora_host.test_update_payload','cueflora_host.test_download_progress','cueflora_setup.test_extension_pair',
        'cueflora_host.test_quality_benchmark','cueflora_host.test_quality_translation','cueflora_host.test_native_protocol'],workspace/'native'),
        ('packaging',[sys.executable,'-m','unittest','discover','-s','packaging','-p','test_*.py'],workspace),
        ('node-release',['node','--test','scripts/release-config.test.mjs'],workspace)]
    report = {'passed':False,'sourceArchiveSha256':source['archiveSha256'],'checks':[],
        'gitHistoryRequired':False,'privateInputsRequired':False,'browserAutomation':False,'inference':False}
    for index,(name,command,cwd) in enumerate(checks):
        started = time.monotonic()
        with (output/(str(index)+'-'+name.replace(':','-')+'.log')).open('wb') as log:
            result = subprocess.run(command,cwd=cwd,env=environment,stdout=log,stderr=subprocess.STDOUT,timeout=600)
        report['checks'].append({'name':name,'exitCode':result.returncode,'seconds':round(time.monotonic()-started,2)})
        (output/'clean-source-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(name+': '+('PASS' if result.returncode==0 else 'FAIL'),flush=True)
        if result.returncode: raise ValueError('Clean-source verification failed')
    report['passed']=True
    (output/'clean-source-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); verify(args.cache.resolve(),args.output.resolve())
