"""Actual frozen health failure checks in an isolated copy; never install."""
import argparse
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
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
        body = b'{"type":"PING"}'
        result = subprocess.run([str(copy/'cueflora-host.exe')],input=struct.pack('<I',len(body))+body,env=environment,cwd=copy,capture_output=True,timeout=15,check=True)
        if len(result.stdout)<4 or struct.unpack('<I',result.stdout[:4])[0] != len(result.stdout)-4:
            raise ValueError('Malformed PING frame')
        return json.loads(result.stdout[4:])
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
        'inventoryRestored':True,'liveInstallation':False,'inference':False}
    (output/'capabilities.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args = parser.parse_args()
    check(args.runtime.resolve(),args.output.resolve())
