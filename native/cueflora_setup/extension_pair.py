"""Strict extension ownership and recoverable, stable-folder pair activation."""
import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import uuid
from .bundle import digest

INVENTORY='cueflora-extension.json'

def legacy_releases():
    return json.loads((Path(__file__).parent/'legacy_extensions.json').read_text(encoding='utf-8'))['releases']


def tree(root):
    root=Path(root).absolute()
    if root.resolve()!=root or root.is_symlink():raise ValueError('Unsafe extension directory')
    files={}
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or path.resolve()!=path:raise ValueError('Linked extension entry rejected')
        if path.is_file():files[path.relative_to(root).as_posix()]=digest(path)
    return files


def identity(root):
    manifest=json.loads((Path(root)/'manifest.json').read_text(encoding='utf-8'))
    key=base64.b64decode(manifest.get('key',''),validate=True)
    chrome_id=''.join(chr(97+int(char,16)) for char in hashlib.sha256(key).hexdigest()[:32])
    if not key or not str(manifest.get('name','')).startswith('CueFlora') or not re.fullmatch(r'\d+\.\d+\.\d+',manifest.get('version','')):raise ValueError('Not an identified CueFlora Chrome extension')
    return chrome_id,manifest['version']


def verify_files(root,files):
    if not isinstance(files,dict) or not files or len(files)>5000:raise ValueError('Invalid extension inventory')
    for name,checksum in files.items():
        path=PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or path.as_posix()!=name or '\\' in name or ':' in name or not re.fullmatch('[0-9a-f]{64}',str(checksum)):raise ValueError('Unsafe extension inventory entry')
    if tree(root)!=files:raise ValueError('Extension folder is foreign, modified or incomplete. It was not changed.')
    return identity(root)


def verify_extension(root,binding=None):
    root=Path(root).absolute();path=root/INVENTORY
    files=tree(root)
    if binding is not None and (not re.fullmatch('[0-9a-f]{64}',str(binding)) or digest(path)!=binding):raise ValueError('Extension payload binding mismatch')
    data=json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema')!=1 or data.get('product')!='cueflora' or not isinstance(data.get('files'),dict):raise ValueError('Invalid extension payload inventory')
    expected={**data['files'],INVENTORY:digest(path)}
    chrome_id,version=verify_files(root,expected)
    if data.get('chromeId')!=chrome_id or data.get('version')!=version:raise ValueError('Extension inventory identity mismatch')
    return data,files


class ExtensionPair:
    def __init__(self,root):self.root=Path(root).absolute()
    def target(self,value=None):
        path=Path(value).absolute() if value is not None else self.root/'Chrome-extension'
        if not path.is_absolute() or path==self.root or len(path.parts)<3 or path.resolve()!=path or path.is_symlink():raise ValueError('Unsafe managed extension target')
        if any(part.casefold() in ('user data','profiles','system32') for part in path.parts):raise ValueError('Chrome profiles and system folders cannot be adopted')
        return path
    def source(self,record):
        if not isinstance(record,dict) or record.get('schema')!=1 or not re.fullmatch('[0-9a-f]{32}',str(record.get('id',''))):raise ValueError('Invalid managed extension record')
        self.target(record.get('directory'))
        source=self.root/'extension-versions'/record['id']
        if source.resolve()!=source:raise ValueError('Linked extension version')
        chrome_id,version=verify_files(source,record.get('files'))
        if chrome_id!=record.get('chromeId') or version!=record.get('version'):raise ValueError('Managed extension identity changed')
        return source
    def preserve(self,source,target,files):
        identifier=uuid.uuid4().hex;folder=self.root/'extension-versions'/identifier
        if folder.resolve()!=folder:raise ValueError('Unsafe extension version directory')
        folder.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(source,folder)
        chrome_id,version=verify_files(folder,files)
        return {'schema':1,'id':identifier,'directory':str(target),'chromeId':chrome_id,'version':version,'files':files}
    def prepare(self,payload,release,previous,adopt=None,confirmed=False):
        target=self.target(previous['directory'] if previous else adopt)
        if previous:self.source(previous)
        elif target.exists():
            if adopt is None or not confirmed:raise ValueError('Existing extension folder requires explicit adoption confirmation')
            actual=tree(target)
            matches=[item for item in legacy_releases() if item['chromeId']==release['extensionIds']['chrome'] and item['files']==actual]
            if len(matches)!=1:raise ValueError('Only the exact, unmodified published CueFlora extension can be adopted. No files changed.')
            previous=self.preserve(target,target,actual)
        old_present=target.exists()
        if old_present:
            if not previous:raise ValueError('Unowned extension folder')
            verify_files(target,previous['files'])
        data,files=verify_extension(payload,release.get('extensionInventorySha256'))
        if data['chromeId']!=release['extensionIds']['chrome']:raise ValueError('Helper/extension Chrome identity mismatch')
        record=self.preserve(payload,target,files)
        return record,previous,self.change(record,previous,old_present)
    def change(self,new,old,old_present=None):
        target=self.target((new or old)['directory'])
        if new and old and new['directory']!=old['directory']:raise ValueError('Managed extension directory cannot change during upgrade')
        if new:self.source(new)
        if old:self.source(old)
        if old_present is None:old_present=target.exists()
        if old_present:
            if not old:raise ValueError('Unowned extension target')
            verify_files(target,old['files'])
        suffix=uuid.uuid4().hex
        change={'target':str(target),'stage':str(target.with_name(target.name+'.cueflora-stage-'+suffix)),
            'backup':str(target.with_name(target.name+'.cueflora-backup-'+suffix)),
            'failed':str(target.with_name(target.name+'.cueflora-recovery-'+suffix)),
            'old':old if old_present else None,'new':new}
        if new:
            stage=Path(change['stage']);target.parent.mkdir(parents=True,exist_ok=True)
            if stage.resolve()!=stage:raise ValueError('Unsafe extension staging folder')
            shutil.copytree(self.source(new),stage);verify_files(stage,new['files'])
        return change
    def validate_change(self,change):
        if not isinstance(change,dict) or set(change)!={'target','stage','backup','failed','old','new'}:raise ValueError('Invalid extension recovery change')
        target=self.target(change['target'])
        for name,prefix in [('stage','.cueflora-stage-'),('backup','.cueflora-backup-'),('failed','.cueflora-recovery-')]:
            path=Path(change[name])
            if path.parent!=target.parent or not re.fullmatch(re.escape(target.name+prefix)+'[0-9a-f]{32}',path.name) or path.resolve()!=path:raise ValueError('Unsafe extension recovery target')
        for record in (change['old'],change['new']):
            if record:
                self.source(record)
                if record['directory']!=str(target):raise ValueError('Extension recovery ownership mismatch')
        backup=Path(change['backup']);stage=Path(change['stage'])
        if backup.exists():
            if not change['old']:raise ValueError('Unexpected extension backup')
            verify_files(backup,change['old']['files'])
        if stage.exists():
            if not change['new']:raise ValueError('Unexpected extension stage')
            verify_files(stage,change['new']['files'])
        if target.exists():
            actual=tree(target)
            if not any(record and actual==record['files'] for record in (change['old'],change['new'])):raise ValueError('Extension changed during recovery; refusing overwrite')
        return target
    def apply(self,change):
        target=self.validate_change(change);backup=Path(change['backup'])
        if target.exists():target.rename(backup)
        if change['new']:
            Path(change['stage']).rename(target);verify_files(target,change['new']['files'])
    def recover(self,change):
        target=self.validate_change(change);backup=Path(change['backup'])
        if target.exists() and change['old'] and tree(target)==change['old']['files']:return
        if change['old'] and not backup.exists():raise ValueError('Extension recovery backup is missing; retain the journal and repair explicitly')
        if target.exists():target.rename(Path(change['failed']))
        if backup.exists():backup.rename(target)
