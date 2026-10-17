"""Publish exact reviewed GitHub artifacts; never infer approval from a build."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from approval_evidence import validate_bindings, verified_decisions
from github_candidate import restore
from release_inputs import digest
from stage_release import plan as stage_plan, execute as stage_execute
from promote_release import promotion, execute as promote_execute


def read_review(path):
    path=Path(path)
    if path.is_symlink() or path.stat().st_size > 8*1024*1024:
        raise ValueError('Ordinary bounded review packet required')
    value=json.loads(path.read_text(encoding='utf-8'))
    fields={'schema','distribution','repository','version','candidateRunId','sourceCommit','artifacts','decisions','reports'}
    if not isinstance(value,dict) or set(value)!=fields or value['schema']!=1 or value['distribution']!='github':
        raise ValueError('Explicit GitHub publication review required')
    if not re.fullmatch(r'[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+',str(value['repository'])) or not re.fullmatch(r'\d+\.\d+\.\d+',str(value['version'])) or not re.fullmatch('[0-9a-f]{40}',str(value['sourceCommit'])):
        raise ValueError('Exact repository, version and source commit required')
    if type(value['candidateRunId']) is not int or not 0 < value['candidateRunId'] < 2**63:
        raise ValueError('Exact successful candidate workflow run required')
    validate_bindings(value['artifacts'])
    if not isinstance(value['reports'],dict) or len(value['reports'])>20 or any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*\.json',name) or not isinstance(text,str) or len(text)>8*1024*1024 for name,text in value['reports'].items()):
        raise ValueError('Bounded ordinary JSON review reports required')
    return value


def materialize(value, output):
    output=Path(output).resolve()
    if output.exists(): raise ValueError('Fresh publisher-review directory required')
    output.mkdir(parents=True)
    for name,text in value['reports'].items():
        (output/name).write_text(text,encoding='utf-8')
    verified_decisions(value['decisions'],output,value['artifacts'],'github')
    return output


class ReleaseRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        parsed=urlsplit(newurl); host=(parsed.hostname or '').lower()
        if parsed.scheme!='https' or parsed.port not in (None,443) or parsed.username is not None or parsed.password is not None or not (host=='github.com' or host.endswith('.githubusercontent.com')):
            raise ValueError('Unexpected release-download redirect')
        return super().redirect_request(request,fp,code,msg,headers,newurl)


def anonymous_downloads(staging):
    opener=build_opener(ReleaseRedirect())
    report=[]
    for item in [*staging['assets'],*([staging['checksumAsset']] if staging.get('checksumAsset') else [])]:
        url='https://github.com/'+staging['repository']+'/releases/download/'+staging['tag']+'/'+item['name']
        checksum=hashlib.sha256(); size=0
        with opener.open(Request(url,headers={'User-Agent':'CueFlora-release-verification'}),timeout=120) as response:
            if response.status!=200: raise ValueError('Release asset is not anonymously downloadable')
            for chunk in iter(lambda:response.read(1024*1024),b''):
                size+=len(chunk)
                if size>item['bytes']: raise ValueError('Release asset exceeds its verified size')
                checksum.update(chunk)
        if size!=item['bytes'] or checksum.hexdigest()!=item['sha256']:
            raise ValueError('Anonymous release asset hash mismatch')
        report.append({'url':url,'sha256':checksum.hexdigest(),'bytes':size,'verified':True})
    return report


def publish_pages(preparation, repository):
    pages=Path(preparation)/'public-pages'
    report=json.loads((pages/'public-materials.json').read_text())
    allowed={'index.html','download.html','privacy.html','support.html','style.css','.nojekyll'}
    if report.get('distribution')!='github' or set(report.get('files',{}))!=allowed:
        raise ValueError('Exact GitHub public-page inventory required')
    entries=[]
    for name in sorted(allowed):
        path=pages/name
        if path.is_symlink() or digest(path)!=report['files'][name]: raise ValueError('Public page changed after verification')
        entries.append({'path':name,'type':'blob','mode':'100644','content':path.read_text(encoding='utf-8')})
    def api(endpoint,data=None):
        command=['gh','api','repos/'+repository+'/'+endpoint]
        if data is not None: command+=['--method','POST','--input','-']
        result=subprocess.run(command,input=None if data is None else json.dumps(data),capture_output=True,text=True,timeout=120)
        if result.returncode: raise RuntimeError('GitHub Pages update failed; existing pages were not assumed updated')
        return json.loads(result.stdout)
    branch='codex/public-pages'
    old=api('git/ref/heads/'+branch)['object']['sha']
    parent=api('git/commits/'+old)
    tree=api('git/trees',{'base_tree':parent['tree']['sha'],'tree':entries})
    commit=api('git/commits',{'message':'Publish verified GitHub download links','tree':tree['sha'],'parents':[old]})
    result=subprocess.run(['gh','api','repos/'+repository+'/git/refs/heads/'+branch,'--method','PATCH','--input','-'],
        input=json.dumps({'sha':commit['sha'],'force':False}),capture_output=True,text=True,timeout=120)
    if result.returncode: raise RuntimeError('Concurrent or failed Pages ref update; inspect remote state')
    return {'branch':branch,'commit':commit['sha'],'deploymentAndLiveHashVerification':'Required after GitHub Pages deployment'}


def run(candidate, review, output, execute=False, confirmed_version=None):
    value=read_review(review); output=Path(output).resolve()
    if output.exists(): raise ValueError('Fresh publication receipt required')
    if execute and confirmed_version!=value['version']: raise ValueError('Exact-version execution confirmation required')
    if os.environ.get('GITHUB_REPOSITORY',value['repository'])!=value['repository']:
        raise ValueError('Publication repository differs from the workflow repository')
    evidence=materialize(value,output.parent/'publisher-review')
    root=restore(candidate)
    readiness=json.loads((root/'readiness.json').read_text())
    configuration=json.loads((root/'setup-1/bundle/release.json').read_text())
    if readiness['artifactBindings']!=value['artifacts'] or readiness['effectiveConfiguration']['version']!=value['version'] or configuration['repositoryUrl']!='https://github.com/'+value['repository']:
        raise ValueError('Review does not match candidate/repository/version')
    staging=stage_plan(root,configuration,value['decisions'],evidence,value['sourceCommit'])
    receipt={'schema':1,'repository':value['repository'],'version':value['version'],'sourceCommit':value['sourceCommit'],
        'candidateRunId':value['candidateRunId'],'artifacts':value['artifacts'],'published':False,'staging':staging,
        'storeSubmitted':False,'credentialsRecorded':False}
    def persist(): output.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    persist()
    if execute:
        receipt['staging']=stage_execute(staging,confirmed_version); persist()
        promoted=promotion(root,configuration,value['decisions'],evidence)
        receipt['promotion']=promote_execute(promoted,confirmed_version); receipt['published']=True; persist()
        receipt['anonymousDownloads']=anonymous_downloads(receipt['staging']); persist()
        receipt['pages']=publish_pages(root,value['repository']); persist()
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review',type=Path,required=True)
    parser.add_argument('--metadata',action='store_true')
    parser.add_argument('--candidate',type=Path); parser.add_argument('--output',type=Path)
    parser.add_argument('--execute',action='store_true'); parser.add_argument('--confirm-version')
    args=parser.parse_args()
    if args.metadata:
        value=read_review(args.review)
        for name,text in [('source_commit',value['sourceCommit']),('candidate_run_id',str(value['candidateRunId'])),('version',value['version'])]:
            if os.environ.get('GITHUB_OUTPUT'):
                with Path(os.environ['GITHUB_OUTPUT']).open('a',encoding='utf-8') as stream: stream.write(name+'='+text+'\n')
        print(json.dumps({name:value[name] for name in ('repository','version','sourceCommit','candidateRunId')}))
    elif args.candidate and args.output:
        result=run(args.candidate,args.review,args.output,args.execute,args.confirm_version)
        print(json.dumps({'published':result['published'],'receipt':str(args.output)}))
    else: parser.error('--candidate and --output are required without --metadata')
