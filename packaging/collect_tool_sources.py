"""Version-specific source evidence from observed executable metadata, never latest."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tarfile
from urllib.parse import urlsplit
from urllib.request import urlopen
import zipfile
from packaging.version import Version

ALIASES={'Cryptodome':'pycryptodomex','brotli':'brotli','certifi':'certifi','curl_cffi':'curl_cffi','mutagen':'mutagen',
    'requests':'requests','urllib3':'urllib3','websockets':'websockets','yt_dlp_ejs':'yt-dlp-ejs'}


def selected_sources(audit):
    result=[]
    for item in audit.get('observedOptionalLibraryVersions',[]):
        package=ALIASES.get(item.get('name'))
        if package is None: continue
        version=str(Version(item['version']))
        if not re.fullmatch(r'\d+(?:\.\d+){1,3}',version): raise ValueError('Exact stable dependency version required')
        result.append((package,version))
    if not result: raise ValueError('No observed dependency versions')
    return result


def collect(audit,cache,output,online=False):
    if output.exists(): raise ValueError('Fresh dependency source-evidence directory required')
    cache.mkdir(parents=True,exist_ok=True); output.mkdir(parents=True)
    records=[]; failures=[]
    for package,version in selected_sources(audit):
        metadata_file=cache/(package+'-'+version+'.pypi.json')
        try:
            if not metadata_file.exists():
                if not online: raise ValueError('Missing exact primary metadata cache')
                with urlopen('https://pypi.org/pypi/'+package+'/'+version+'/json',timeout=60) as response:
                    raw=response.read(8*1024*1024+1)
                if len(raw)>8*1024*1024: raise ValueError('Oversized primary metadata')
                metadata_file.write_bytes(raw)
            if metadata_file.is_symlink(): raise ValueError('Linked metadata cache')
            metadata=json.loads(metadata_file.read_bytes())
            if Version(metadata['info']['version'])!=Version(version): raise ValueError('Primary version mismatch')
            item=next((item for item in metadata['urls'] if item['packagetype']=='sdist'),None)
            if item is None: raise ValueError('No matching published source distribution')
            name=item['filename']; checksum=item['digests']['sha256']; parsed=urlsplit(item['url'])
            if not re.fullmatch('[A-Za-z0-9_.+-]+',name) or not re.fullmatch('[0-9a-f]{64}',checksum) or parsed.scheme!='https' or parsed.hostname!='files.pythonhosted.org' or parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError('Unsafe primary source entry')
            path=cache/name
            if not path.exists():
                if not online: raise ValueError('Missing exact source cache')
                partial=path.with_suffix(path.suffix+'.partial')
                with urlopen(item['url'],timeout=60) as response,partial.open('xb') as stream: shutil.copyfileobj(response,stream)
                if hashlib.sha256(partial.read_bytes()).hexdigest()!=checksum: raise ValueError('Source download hash mismatch')
                partial.rename(path)
            if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=checksum: raise ValueError('Changed source cache')
            shutil.copy2(path,output/name)
            notices={}
            if name.endswith('.zip'):
                with zipfile.ZipFile(path) as archive:
                    entries=[(entry.filename,archive.read(entry)) for entry in archive.infolist() if not entry.is_dir() and entry.file_size<1024*1024 and re.search('license|copying|notice',Path(entry.filename).name,re.I)]
            else:
                with tarfile.open(path) as archive:
                    entries=[(entry.name,archive.extractfile(entry).read()) for entry in archive if entry.isfile() and entry.size<1024*1024 and re.search('license|copying|notice',Path(entry.name).name,re.I)]
            for original,content in entries:
                target=output/'notices'/(package+'-'+hashlib.sha256(original.encode()).hexdigest()[:12]+'.txt')
                target.parent.mkdir(exist_ok=True); target.write_bytes(content)
                notices[original]={'file':target.relative_to(output).as_posix(),'sha256':hashlib.sha256(content).hexdigest()}
            records.append({'package':package,'version':version,'file':name,'url':item['url'],'sha256':checksum,
                'metadataSha256':hashlib.sha256(metadata_file.read_bytes()).hexdigest(),'declaredLicence':metadata['info'].get('license_expression') or metadata['info'].get('license'),
                'notices':notices,'sourceScope':'Observed executable version; compiled/native transitive sources require independent matching'})
        except Exception as error:
            failures.append({'package':package,'version':version,'reason':type(error).__name__+': '+str(error)})
    report={'schema':1,'sources':records,'failures':failures,'allObservedPythonSourcesObtained':not failures,
        'completeBinaryDependencyClosure':False,'redistributionApproved':False,'published':False,'inference':False}
    (output/'observed-source-evidence.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'sources':len(records),'failures':failures,'closure':False}))
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('audit','cache','output'): parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--online',action='store_true')
    args=parser.parse_args(); collect(json.loads(args.audit.read_text()),args.cache.resolve(),args.output.resolve(),args.online)
