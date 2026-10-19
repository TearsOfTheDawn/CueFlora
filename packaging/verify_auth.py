"""Run the frozen helper's explicit synthetic auth check; no login/network/inference."""
import argparse
import json
import os
from pathlib import Path
import subprocess


def verify(runtime,output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    env={key:value for key,value in os.environ.items() if not key.startswith(('CUEFLORA_','PYTHON'))}
    env['PATH']=str(Path(os.environ['SystemRoot'])/'System32')
    report=output/'frozen-auth.json'
    subprocess.run([str((Path(runtime)/'cueflora-host.exe').resolve()),'--auth-self-check','--report',str(report)],env=env,cwd=output,check=True,timeout=30,capture_output=True)
    data=json.loads(report.read_text())
    if data!={'passed':True,'jwtSignatureValidation':True,'userScopedDpapi':True,'tokensRedacted':True,'genuineLogin':False,'network':'mocked','inference':False}:raise ValueError('Invalid frozen auth self-check')
    return data


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--runtime',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();print(json.dumps(verify(args.runtime,args.output)))
