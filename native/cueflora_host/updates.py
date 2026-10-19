"""User-triggered GitHub updates. No arbitrary repository, URL or executable input."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import sys
from urllib.parse import urlsplit, unquote
import uuid
import httpx
from .account_store import safe_directory
from .update_payload import verify_update_payload

REPOSITORY='TearsOfTheDawn/CueFlora'
API='https://api.github.com/repos/'+REPOSITORY
UPDATER_VERSION='0.2.0'
CHROME_ID='akcolbcdfnjcahhhodnpablekjagfadf'
REDIRECT_HOSTS={'github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'}


def version(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d+\.\d+\.\d+',value): raise ValueError('Stable semantic version required')
    return tuple(map(int,value.split('.')))


def asset_url(value, tag, name):
    expected='https://github.com/'+REPOSITORY+'/releases/download/'+tag+'/'+name
    if value!=expected: raise ValueError('Unexpected GitHub release asset URL')
    return value


def validate_manifest(data, current=UPDATER_VERSION, chrome_id=CHROME_ID):
    fields={'schema','product','repository','version','platform','architecture','chromeId','minimumUpdaterVersion','setup',
            'runtimeInventorySha256','extensionInventorySha256','sourceInventorySha256'}
    if not isinstance(data,dict) or set(data)!=fields or data.get('schema')!=1 or data.get('product')!='cueflora' or data.get('repository')!=REPOSITORY:
        raise ValueError('Invalid CueFlora update manifest')
    if data['platform']!='Windows' or data['architecture']!='x64' or data['chromeId']!=chrome_id: raise ValueError('Update platform or Chrome identity mismatch')
    if version(data['version'])<=version(current): raise ValueError('Update is not newer than this installation')
    if version(data['minimumUpdaterVersion'])>version(UPDATER_VERSION): raise ValueError('This update requires a newer updater. Download the complete package manually.')
    for field in ('runtimeInventorySha256','extensionInventorySha256','sourceInventorySha256'):
        if not isinstance(data[field],str) or not re.fullmatch('[0-9a-f]{64}',data[field]): raise ValueError('Invalid update payload binding')
    setup=data['setup']
    if not isinstance(setup,dict) or set(setup)!={'name','size','sha256','url'}: raise ValueError('Invalid Setup asset')
    if setup['name']!='CueFlora-'+data['version']+'-Setup.exe': raise ValueError('Unexpected Setup asset name')
    if type(setup['size']) is not int or not 1024*1024<=setup['size']<=1024*1024*1024: raise ValueError('Invalid Setup size')
    if not isinstance(setup['sha256'],str) or not re.fullmatch('[0-9a-f]{64}',setup['sha256']): raise ValueError('Invalid Setup hash')
    asset_url(setup['url'],'v'+data['version'],setup['name'])
    return data


def download_bytes(client,url,limit,cancel=None,on_chunk=None,allow_redirects=False,overall=120):
    started=time.monotonic(); last=started; received=0
    for hop in range(6):
        parsed=urlsplit(url)
        if parsed.scheme!='https' or parsed.username or parsed.password or parsed.port not in (None,443): raise ValueError('Unsafe update transport')
        if hop and (not allow_redirects or parsed.hostname not in REDIRECT_HOSTS): raise ValueError('Update redirect host rejected')
        with client.stream('GET',url,headers={'Accept':'application/octet-stream','User-Agent':'CueFlora-Updater/'+UPDATER_VERSION}) as response:
            if response.status_code in (301,302,303,307,308):
                location=response.headers.get('location','')
                if not allow_redirects or not location.startswith('https://'): raise ValueError('Unexpected update redirect')
                url=location;continue
            if response.status_code!=200: raise RuntimeError('GitHub update request failed. Retry explicitly.')
            for chunk in response.iter_bytes():
                now=time.monotonic()
                if cancel is not None and cancel.is_set(): raise RuntimeError('Update download cancelled')
                if now-started>overall or now-last>300: raise RuntimeError('Update download timed out. Retry explicitly.')
                if chunk: last=now
                received+=len(chunk)
                if received>limit: raise ValueError('Update response exceeded the expected size')
                if on_chunk:on_chunk(chunk)
            return received
    raise ValueError('Too many update redirects')


def metadata(client,url,limit=1024*1024,asset=False):
    raw=bytearray()
    download_bytes(client,url,limit,on_chunk=raw.extend,allow_redirects=asset)
    return json.loads(raw)


class Updates:
    def __init__(self,root=None,current=None,chrome_id=CHROME_ID):
        if current is None:
            if getattr(sys,'frozen',False):current=json.loads((Path(sys.executable).parent/'runtime-manifest.json').read_text())['hostVersion']
            else:current=json.loads((Path(__file__).resolve().parents[2]/'package.json').read_text())['version']
        version(current)
        if root is None:
            if os.name!='nt' or not os.environ.get('LOCALAPPDATA'): raise RuntimeError('Windows updates require the packaged helper')
            root=Path(os.environ['LOCALAPPDATA'])/'CueFlora'/'updates'
        self.root=Path(root).absolute();self.current=current;self.chrome_id=chrome_id

    def _folder(self,selection):
        if not isinstance(selection,str) or not re.fullmatch('[0-9a-f-]{36}',selection): raise ValueError('Invalid update selection')
        return safe_directory(safe_directory(self.root)/selection)

    def selected(self,selection):
        folder=self._folder(selection);record=folder/'selected.json'
        if record.is_symlink() or not record.is_file() or record.stat().st_size>16384: raise ValueError('Update selection expired. Check again.')
        return validate_manifest(json.loads(record.read_bytes()),self.current,self.chrome_id)

    def check(self):
        with httpx.Client(timeout=15,follow_redirects=False,trust_env=False) as client:
            releases=metadata(client,API+'/releases?per_page=20')
            if not isinstance(releases,list): raise ValueError('Invalid GitHub releases response')
            stable=[]
            for release in releases:
                if not isinstance(release,dict) or release.get('draft') is not False or release.get('prerelease') is not False or not release.get('published_at'): continue
                tag=release.get('tag_name','')
                if not isinstance(tag,str) or not re.fullmatch(r'v\d+\.\d+\.\d+',tag): continue
                if version(tag[1:])>version(self.current): stable.append(release)
            if not stable:return {'available':False,'currentVersion':self.current}
            release=max(stable,key=lambda item:version(item['tag_name'][1:]));target=release['tag_name'][1:]
            name='CueFlora-'+target+'-update.json';assets=release.get('assets',[])
            manifests=[asset for asset in assets if isinstance(asset,dict) and asset.get('name')==name]
            if len(manifests)!=1: raise RuntimeError('This release needs a manual complete-package download; no compatible update manifest is published.')
            manifest=validate_manifest(metadata(client,asset_url(manifests[0].get('browser_download_url'),release['tag_name'],name),16384,True),self.current,self.chrome_id)
            if manifest['version']!=target: raise ValueError('Release/manifest version mismatch')
            setups=[asset for asset in assets if isinstance(asset,dict) and asset.get('name')==manifest['setup']['name']]
            if len(setups)!=1 or setups[0].get('size')!=manifest['setup']['size'] or setups[0].get('browser_download_url')!=manifest['setup']['url']: raise ValueError('Manifest/release asset mismatch')
        selection=str(uuid.uuid4());folder=self._folder(selection)
        with (folder/'selected.json').open('x',encoding='utf-8') as output:json.dump(manifest,output,sort_keys=True)
        return {'available':True,'selectionRef':selection,'version':target,'size':manifest['setup']['size'],'unsigned':True}

    def download(self,selection,cancel,progress):
        manifest=self.selected(selection);folder=self._folder(selection);target=folder/manifest['setup']['name'];temporary=folder/('download-'+uuid.uuid4().hex+'.partial')
        if target.exists():
            try:
                self.verify(selection);return {'selectionRef':selection,'version':manifest['version'],'ready':True}
            except ValueError:
                if target.is_symlink():raise
                target.rename(folder/('rejected-'+uuid.uuid4().hex+'.bin'))
        checksum=hashlib.sha256();received=0
        try:
            with temporary.open('xb') as stream:
                def write(chunk):
                    nonlocal received
                    stream.write(chunk);checksum.update(chunk);received+=len(chunk)
                    progress(round(received*100/manifest['setup']['size'],1))
                with httpx.Client(timeout=httpx.Timeout(30,connect=10),follow_redirects=False,trust_env=False) as client:
                    size=download_bytes(client,manifest['setup']['url'],manifest['setup']['size'],cancel,write,True,3600)
                stream.flush();os.fsync(stream.fileno())
            if cancel.is_set():raise RuntimeError('Update download cancelled')
            if size!=manifest['setup']['size'] or checksum.hexdigest()!=manifest['setup']['sha256']:raise ValueError('Downloaded Setup failed its size/hash verification')
            verify_update_payload(temporary,manifest)
            if target.exists():raise ValueError('Update target changed during download')
            temporary.rename(target)
            return {'selectionRef':selection,'version':manifest['version'],'ready':True}
        finally:
            if temporary.exists():temporary.unlink()

    def verify(self,selection):
        manifest=self.selected(selection);target=self._folder(selection)/manifest['setup']['name']
        if target.is_symlink() or not target.is_file() or target.stat().st_size!=manifest['setup']['size']:raise ValueError('Update Setup is missing or has changed. Download again.')
        checksum=hashlib.sha256()
        with target.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):checksum.update(block)
        if checksum.hexdigest()!=manifest['setup']['sha256']:raise ValueError('Update Setup hash changed. Refusing execution.')
        verify_update_payload(target,manifest)
        return target

    def launch(self,selection):
        target=self.verify(selection)
        # No shell, arbitrary arguments, silent install, or Windows-warning bypass.
        subprocess.Popen([str(target)],cwd=str(target.parent),close_fds=True)
        return {'launched':True,'version':self.selected(selection)['version']}
