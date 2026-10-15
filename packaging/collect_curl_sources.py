"""Match the actual embedded Windows curl DLL and preserve its exact recipe inputs."""
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
from release_inputs import ROOT,digest
from notice_names import is_notice_name


def validate(lock):
    if not isinstance(lock,dict) or lock.get('schema')!=1 or lock.get('version')!='2.0.0' or lock.get('redistributionApproved') is not False or not isinstance(lock.get('dependencies'),list) or len(lock['dependencies'])!=8:
        raise ValueError('Exact Windows curl source lock required')
    names=set()
    for item in [lock.get('binary'),lock.get('source'),*lock['dependencies']]:
        if not isinstance(item,dict): raise ValueError('Malformed curl input')
        parsed=urlsplit(item.get('url','')); name=item.get('file','')
        if not re.fullmatch('[A-Za-z0-9_.+-]+',name) or name in ('.','..') or name.casefold() in names or not re.fullmatch('[0-9a-f]{64}',str(item.get('sha256',''))) or parsed.scheme!='https' or parsed.hostname not in ('github.com','codeload.github.com') or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.port not in (None,443):
            raise ValueError('Unsafe/unpinned curl source input')
        names.add(name.casefold())
    if lock['binary'].get('member')!='lib/libcurl-impersonate.dll' or not re.fullmatch('[0-9a-f]{64}',str(lock['binary'].get('memberSha256',''))): raise ValueError('Exact curl DLL binding required')
    if {item.get('recipeVariable') for item in lock['dependencies']}!={'BROTLI','BORINGSSL','NGHTTP2','NGTCP2','NGHTTP3','ZLIB','ZSTD','CURL'}:
        raise ValueError('Incomplete curl recipe dependencies')
    return lock


def obtain(cache,online=False):
    lock=validate(json.loads((ROOT/'packaging/curl-native-inputs.lock.json').read_text()))
    cache.mkdir(parents=True,exist_ok=True)
    for item in [lock['binary'],lock['source'],*lock['dependencies']]:
        path=cache/item['file']
        if not path.exists():
            if not online: raise ValueError('Missing exact curl source input: '+item['file'])
            partial=path.with_suffix(path.suffix+'.partial')
            with urlopen(item['url'],timeout=90) as response,partial.open('xb') as stream: shutil.copyfileobj(response,stream)
            if digest(partial)!=item['sha256']: raise ValueError('Downloaded curl input hash mismatch')
            partial.rename(path)
        if path.is_symlink() or not path.is_file() or digest(path)!=item['sha256']: raise ValueError('Changed curl source input')
    return lock


def check_recipe(lock,recipe):
    for item in lock['dependencies']:
        variable=item['recipeVariable']; version_var='COMMIT' if variable=='BORINGSSL' else 'VERSION'
        if 'set('+variable+'_URL_HASH "SHA256='+item['sha256']+'")' not in recipe or 'set('+variable+'_'+version_var+' "'+item['version']+'")' not in recipe:
            raise ValueError('Curl recipe and exact source pins disagree')
    if '-DUSE_WIN32_IDN=ON -DUSE_LIBIDN2=OFF' not in recipe: raise ValueError('Windows IDN recipe evidence missing')


def collect(cache,output,downloader,online=False):
    lock=obtain(cache,online)
    from PyInstaller.archive.readers import CArchiveReader
    archive=CArchiveReader(str(downloader))
    # delvewheel relocates this same DLL using a hash-suffixed filename.
    # The name is only a selector; exact bytes still must match the origin.
    names=[name for name in archive.toc if re.fullmatch(r'libcurl-impersonate(?:-[0-9a-f]{32})?\.dll',Path(name.replace('\\','/')).name)]
    if len(names)!=1 or hashlib.sha256(archive.extract(names[0])).hexdigest()!=lock['binary']['memberSha256']:
        raise ValueError('Curl source evidence belongs to another embedded DLL')
    with tarfile.open(cache/lock['binary']['file']) as bundle:
        matches=[member for member in bundle if member.name==lock['binary']['member'] and member.isfile()]
        if len(matches)!=1 or hashlib.sha256(bundle.extractfile(matches[0]).read()).hexdigest()!=lock['binary']['memberSha256']: raise ValueError('Curl binary-origin archive mismatch')
    with zipfile.ZipFile(cache/lock['source']['file']) as bundle:
        recipe=bundle.read('curl-impersonate-2.0.0/CMakeLists.txt').decode()
    check_recipe(lock,recipe)
    if output.exists(): raise ValueError('Fresh curl evidence output required')
    output.mkdir(parents=True); notices={}
    for item in [lock['source'],*lock['dependencies']]:
        path=cache/item['file']; shutil.copy2(path,output/path.name)
        if path.suffix=='.zip':
            with zipfile.ZipFile(path) as bundle:
                entries=[(entry.filename,bundle.read(entry)) for entry in bundle.infolist() if not entry.is_dir() and entry.file_size<=1024*1024 and is_notice_name(Path(entry.filename).name)]
        else:
            with tarfile.open(path) as bundle:
                entries=[(entry.name,bundle.extractfile(entry).read()) for entry in bundle if entry.isfile() and entry.size<=1024*1024 and is_notice_name(Path(entry.name).name)]
        for name,data in entries:
            target=output/'notices'/(path.name+'-'+hashlib.sha256(name.encode()).hexdigest()[:12]+'.txt')
            target.parent.mkdir(exist_ok=True); target.write_bytes(data)
            notices[target.name]={'sourceArchive':path.name,'sourceEntry':name,'sha256':digest(target)}
        if not entries: raise ValueError('Required curl dependency notice missing: '+path.name)
    shutil.copy2(ROOT/'packaging/curl-native-inputs.lock.json',output/'curl-native-inputs.lock.json')
    (output/'CMakeLists.txt').write_text(recipe,encoding='utf-8')
    report={'schema':1,'downloaderSha256':digest(downloader),'embeddedDllSha256':lock['binary']['memberSha256'],
        'binaryOriginArchive':lock['binary'],'originVerified':True,'recipeInputsVerified':True,
        'lockSha256':digest(ROOT/'packaging/curl-native-inputs.lock.json'),'sourceInputs':[lock['source'],*lock['dependencies']],
        'notices':notices,'files':{path.relative_to(output).as_posix():digest(path) for path in output.rglob('*') if path.is_file()},
        'scope':'Exact Windows DLL bytes match upstream archive. Recipe sources/notices are preserved; other platform aggregate notices are not proof of shipped components.',
        'redistributionApproved':False,'completeBinaryDependencyClosure':False}
    (output/'curl-source-evidence.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'originVerified':True,'recipeSources':len(report['sourceInputs']),'notices':len(notices)}))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('cache','output','downloader'): parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--online',action='store_true')
    args=parser.parse_args(); collect(args.cache.resolve(),args.output.resolve(),args.downloader.resolve(),args.online)
