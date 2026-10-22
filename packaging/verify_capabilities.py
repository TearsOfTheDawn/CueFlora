"""Actual frozen health failure checks in an isolated copy; never install."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
from persistent_native import exchange
from release_inputs import ROOT
sys.path.insert(0,str(ROOT/'native'))
from cueflora_setup.bundle import verify_bundle


def check(runtime, output):
    output.mkdir(parents=True,exist_ok=False)
    copy = output/'Runtime Ω with spaces'
    shutil.copytree(runtime,copy)
    environment = {key:value for key,value in os.environ.items() if key not in ('DENO_PATH','YT_DLP_PATH','FFMPEG_PATH','FFPROBE_PATH','PYTHONPATH','PYTHONHOME','CUEFLORA_EVIDENCE_DIR')}
    environment['PATH'] = str(Path(os.environ['SystemRoot'])/'System32')
    def ping():
        responses,_ = exchange([str(copy/'cueflora-host.exe')],[{'type':'PING'},{'type':'PING'}],
                               env=environment,cwd=copy,timeout=20)
        if responses[0]!=responses[1]:raise ValueError('Inconsistent persistent health response')
        return responses[-1]
    healthy = ping()
    if not all(healthy['tools'][name]['available'] for name in ['yt-dlp','ffmpeg','ffprobe','deno']):
        raise ValueError('Bundled dependency unhealthy')
    deno = copy/'tools/deno.exe'; held = copy/'tools/deno.exe.held'
    deno.rename(held)
    try:
        missing = ping()
        if missing['status'] != 'PONG' or missing['tools']['deno']['available']:
            raise ValueError('Missing Deno silently accepted')
    finally:
        held.rename(deno)
    verify_bundle(copy)
    report = {'healthy':healthy,'missingDeno':missing,'restrictedPath':True,'unicodePath':True,
        'inventoryRestored':True,'persistentPort':True,'responsesBeforeClosingInput':2,
        'liveInstallation':False,'inference':False}
    (output/'capabilities.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args = parser.parse_args()
    check(args.runtime.resolve(),args.output.resolve())
