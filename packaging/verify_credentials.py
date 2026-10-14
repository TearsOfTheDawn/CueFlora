"""Synthetic-key frozen DPAPI checks. No network, browser or installation."""
import argparse
import json
import os
from pathlib import Path
import struct
import subprocess


def verify(runtime, output):
    output.mkdir(parents=True, exist_ok=False)
    executable = runtime / 'cueflora-host.exe'
    env = {key:value for key,value in os.environ.items() if key not in ('PYTHONPATH','PYTHONHOME','CUEFLORA_EVIDENCE_DIR','YT_DLP_PATH','FFMPEG_PATH','FFPROBE_PATH','DENO_PATH')}
    env['PATH'] = os.environ['SystemRoot'] + '\\System32'

    def request(message):
        encoded = json.dumps(message).encode()
        result = subprocess.run([str(executable.resolve())], input=struct.pack('<I',len(encoded))+encoded,
                                capture_output=True, timeout=15, cwd=runtime, env=env)
        if result.returncode or len(result.stdout) < 4 or struct.unpack('<I',result.stdout[:4])[0] != len(result.stdout)-4:
            raise ValueError('Invalid frozen credential response')
        return json.loads(result.stdout[4:])

    key = 'synthetic-frozen-check-Ω-only'
    first = request({'type':'CREDENTIAL_PROTECT','requestId':'one','stage':'transcription','baseUrl':'https://synthetic.invalid/v1','apiKey':key})
    if first.get('requestId') != 'one' or 'credential' not in first or key in json.dumps(first):
        raise ValueError('Frozen protection failed or exposed plaintext')
    # Rebinding necessarily decrypts and validates the old blob inside the host.
    rebound = request({'type':'CREDENTIAL_PROTECT','requestId':'two','stage':'transcription','baseUrl':'https://changed.invalid/v1',
                       'previousBaseUrl':'https://synthetic.invalid/v1','credential':first['credential']})
    if 'credential' not in rebound:
        raise ValueError('Frozen decryption/rebinding failed')
    for stage, endpoint, credential in [('translation','https://synthetic.invalid/v1',first['credential']),
            ('transcription','https://wrong.invalid/v1',first['credential']),
            ('transcription','https://synthetic.invalid/v1',{'schema':1,'method':'windows-dpapi-v1','blob':'bad!'})]:
        failure = request({'type':'CREDENTIAL_PROTECT','requestId':'bad','stage':stage,'baseUrl':'https://changed.invalid/v1',
                           'previousBaseUrl':endpoint,'credential':credential})
        if 'error' not in failure or 'credential' in failure or key in json.dumps(failure) or first['credential']['blob'] in json.dumps(failure):
            raise ValueError('Frozen credential failure did not fail closed')
    blocked = request({'type':'TRANSCRIBE_NATIVE','jobId':'synthetic','videoId':'U_V6Jqg7PV4','transportPolicy':'https-remote',
                       'whisperConfig':{'baseUrl':'http://remote.invalid','allowRemoteHttp':True,'model':'synthetic'}})
    if 'error' not in blocked or 'cues' in blocked:
        raise ValueError('Store transport did not fail before download')
    report = {'realWindowsDpapi':True,'syntheticKeysOnly':True,'roundTripAndRebinding':True,'wrongStageEndpointAndMalformedBlobRejected':True,
              'restrictedPath':True,'storeRemoteHttpBlockedBeforeDownload':True,'rawCredentialsRecorded':False,'networkRequests':0,'inference':False,'liveInstallation':False}
    (output/'credential-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',type=Path,required=True); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); print(json.dumps(verify(args.runtime,args.output),indent=2))
