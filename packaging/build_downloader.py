"""Same-version yt-dlp on the pinned supported interpreter; no media/inference."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import zipfile
from release_inputs import ROOT,digest,inspect_ejs,shipped_python
from bootstrap_offline import bootstrap
from build_isolation import environment
from pin_downloader_inputs import download


def validate_lock(lock):
    if not isinstance(lock,dict) or lock.get('schema')!=1 or lock.get('ytDlpVersion')!='2026.08.19' or lock.get('pythonVersion')!='3.13.15' or lock.get('redistributionApproved') is not False or not isinstance(lock.get('dependencies'),list):
        raise ValueError('Exact supported-interpreter downloader lock required')
    names=set(); files=set()
    def entry_valid(entry):
        from urllib.parse import urlsplit
        if not isinstance(entry,dict): raise ValueError('Malformed downloader input')
        parsed=urlsplit(entry.get('url',''))
        if not re.fullmatch('[A-Za-z0-9_.+-]+',str(entry.get('file',''))) or entry['file'] in ('.','..') or entry['file'].casefold() in files or not re.fullmatch('[0-9a-f]{64}',str(entry.get('sha256',''))) or parsed.scheme!='https' or parsed.hostname!='files.pythonhosted.org' or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.port not in (None,443):
            raise ValueError('Unpinned/unsafe downloader input')
        files.add(entry['file'].casefold())
    source=lock.get('source')
    main=json.loads((ROOT/'packaging/inputs-windows.lock.json').read_text())
    expected=next(item for item in main['files'] if item['file']=='yt-dlp-2026.08.19-source.zip')
    if source!=expected or lock['pythonVersion']!=main['pythonVersion']: raise ValueError('Downloader source/interpreter pin mismatch')
    for item in lock['dependencies']:
        if not isinstance(item,dict) or not re.fullmatch('[a-z0-9-]+',str(item.get('name',''))) or item['name'] in names or not re.fullmatch(r'\d+(?:\.\d+){1,3}',str(item.get('version',''))) or item.get('upstreamWheelHashVerified') is not True:
            raise ValueError('Malformed downloader dependency pin')
        names.add(item['name'])
        for entry in (item.get('wheel'),item.get('source')): entry_valid(entry)
    required={'brotli','certifi','charset-normalizer','idna','mutagen','pycryptodomex','requests','urllib3','websockets','yt-dlp-ejs','cffi','curl-cffi','pycparser'}
    if names!=required: raise ValueError('Upstream optional capabilities are incomplete or unexpected')
    return lock


def obtain(cache,online=False):
    cache.mkdir(parents=True,exist_ok=True)
    lock=validate_lock(json.loads((ROOT/'packaging/downloader-inputs.lock.json').read_text()))
    for item in lock['dependencies']:
        for entry in (item['wheel'],item.get('source')):
            if entry is None: continue
            path=cache/entry['file']
            if not path.exists():
                if not online: raise ValueError('Missing exact downloader input: '+entry['file'])
                download(entry,cache)
            if path.is_symlink() or not path.is_file() or digest(path)!=entry['sha256']: raise ValueError('Changed downloader input')
    return lock


def probe(executable,deno):
    env=environment()
    result=subprocess.run([str(executable),'--ignore-config','--no-plugin-dirs','--no-remote-components',
        '--no-js-runtimes','--js-runtimes','deno:'+str(deno),'--verbose'],capture_output=True,text=True,timeout=30,env=env)
    if result.returncode!=2 or 'You must provide at least one URL' not in result.stderr: raise ValueError('No-URL downloader probe failed')
    metadata=[line for line in result.stderr.splitlines() if line.startswith('[debug] ') and any(word in line for word in ('Python ','yt-dlp version ','Optional libraries:','Request Handlers:','JS runtimes:'))]
    extractors=subprocess.check_output([str(executable),'--ignore-config','--no-plugin-dirs','--list-extractors'],text=True,timeout=30,env=env).splitlines()
    return {'metadata':metadata,'extractors':sorted(extractors),'extractorListSha256':hashlib.sha256('\n'.join(sorted(extractors)).encode()).hexdigest(),
        'networkRequested':False,'mediaRequested':False}


def validate_capabilities(previous,current):
    if previous.get('extractors')!=current.get('extractors') or not current.get('extractors'): raise ValueError('Downloader extractor coverage changed')
    lines=current.get('metadata',[])
    if not any('Python 3.13.15' in line for line in lines) or any('OpenSSL 1.1.1' in line for line in lines):
        raise ValueError('Supported-interpreter/TLS replacement not present')
    for capability in ('Cryptodome','brotli','certifi','curl_cffi','mutagen','requests','urllib3','websockets','yt_dlp_ejs'):
        if not any(capability+'-' in line for line in lines): raise ValueError('Optional capability disappeared: '+capability)
    if not any('JS runtimes: deno-' in line for line in lines): raise ValueError('Explicit Deno capability missing')


def validate_build(folder):
    main=json.loads((ROOT/'packaging/inputs-windows.lock.json').read_text())
    lock=validate_lock(json.loads((ROOT/'packaging/downloader-inputs.lock.json').read_text()))
    report=json.loads((folder/'downloader-build.json').read_text())
    if report.get('passed') is not True or report.get('version')!=lock['ytDlpVersion'] or report.get('pythonVersion')!=lock['pythonVersion'] or report.get('inputLockSha256')!=digest(ROOT/'packaging/downloader-inputs.lock.json') or report.get('interpreterLockSha256')!=digest(ROOT/'packaging/inputs-windows.lock.json') or report.get('sourceSha256')!=lock['source']['sha256'] or report.get('ejs')!=main['ejs'] or report.get('executableSha256')!=digest(folder/'bin/yt-dlp.exe'):
        raise ValueError('Verified same-version downloader binding required')
    if inspect_ejs(folder/'bin/yt-dlp.exe')!=main['ejs']: raise ValueError('Local EJS solver bytes changed')
    validate_capabilities(report.get('before',{}),report.get('after',{}))
    from PyInstaller.archive.readers import CArchiveReader
    archive=CArchiveReader(str(folder/'bin/yt-dlp.exe'))
    native={name:hashlib.sha256(archive.extract(name)).hexdigest() for name in archive.toc if name.lower().endswith(('.dll','.pyd'))}
    if not native or native!={name:item['sha256'] for name,item in report.get('nativeLibraries',{}).items()}:
        raise ValueError('Downloader native inventory mismatch')
    for prefix,key in (('notices','noticeFiles'),('corresponding-source','sourceFiles')):
        files={path.relative_to(folder/prefix).as_posix():digest(path) for path in (folder/prefix).rglob('*') if path.is_file()}
        if not files or files!=report.get(key): raise ValueError('Downloader evidence inventory mismatch')
        if any(path.is_symlink() for path in (folder/prefix).rglob('*')): raise ValueError('Linked downloader evidence')
    return report


def build(inputs,cache,output,online=False):
    if os.name!='nt': raise ValueError('Windows x64 downloader build only')
    if output.exists(): raise ValueError('Fresh downloader build directory required')
    lock=obtain(cache,online); main=json.loads((ROOT/'packaging/inputs-windows.lock.json').read_text())
    source=inputs/lock['source']['file']
    if source.is_symlink() or digest(source)!=lock['source']['sha256']: raise ValueError('Downloader source hash mismatch')
    output.mkdir(parents=True)
    bootstrap(inputs,output/'python',official=True)
    python=output/'python/venv/Scripts/python.exe'
    requirement=output/'downloader-requirements.lock'
    requirement.write_text('\n'.join(item['name']+'=='+item['version']+' --hash=sha256:'+item['wheel']['sha256'] for item in lock['dependencies'])+'\n')
    with (output/'install.log').open('wb') as log:
        subprocess.run([str(python),'-m','pip','install','--no-index','--no-deps','--find-links',str(cache),'--require-hashes','-r',str(requirement)],check=True,stdout=log,stderr=subprocess.STDOUT,timeout=300)
    workspace=output/'source'; workspace.mkdir()
    with zipfile.ZipFile(source) as archive:
        seen=set()
        for entry in archive.infolist():
            path=PurePosixPath(entry.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in entry.filename or ':' in entry.filename or not entry.filename.startswith('yt-dlp-2026.08.19/') or entry.filename.casefold() in seen or (entry.external_attr>>16)&0o170000==0o120000:
                raise ValueError('Unsafe/duplicate downloader source member')
            seen.add(entry.filename.casefold())
        archive.extractall(workspace)
    project=workspace/'yt-dlp-2026.08.19'
    # Use the exact upstream recipe; do not update the version or source logic.
    with (output/'lazy-extractors.log').open('wb') as log:
        subprocess.run([str(python),str(project/'devscripts/make_lazy_extractors.py')],cwd=project,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=300)
    env=environment(interpreter=output/'python/python')
    with (output/'build.log').open('wb') as log:
        subprocess.run([str(python),str(project/'bundle/pyinstaller.py'),'--onefile','--noupx'],cwd=project,env=env,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=900)
    executable=project/'dist/yt-dlp.exe'
    version=subprocess.check_output([str(executable),'--version'],text=True,timeout=15).strip()
    if version!=lock['ytDlpVersion']: raise ValueError('Built downloader version changed')
    if inspect_ejs(executable)!=main['ejs']: raise ValueError('Local EJS solver bytes changed or are missing')
    previous=probe(inputs/'yt-dlp.exe',inputs/'deno.exe'); current=probe(executable,inputs/'deno.exe')
    validate_capabilities(previous,current)
    destination=output/'bin'; destination.mkdir(); shutil.copy2(executable,destination/'yt-dlp.exe')
    notices=output/'notices'; notices.mkdir()
    from PyInstaller.archive.readers import CArchiveReader
    archive=CArchiveReader(str(executable)); native={}; notice_origins={}
    interpreter_hashes={item['sha256']:'interpreter:'+item['file'] for item in main['interpreterFiles']}
    wheel_hashes={}
    for dependency in lock['dependencies']:
        with zipfile.ZipFile(cache/dependency['wheel']['file']) as wheel:
            for name in wheel.namelist():
                if name.endswith('/'): continue
                data=wheel.read(name)
                if name.lower().endswith(('.dll','.pyd')): wheel_hashes[hashlib.sha256(data).hexdigest()]={'package':dependency['name'],'version':dependency['version'],'wheelEntry':name,'wheelSha256':dependency['wheel']['sha256']}
                if re.search('license|copying|notice',Path(name).name,re.I):
                    target=notices/(dependency['name']+'-'+hashlib.sha256(name.encode()).hexdigest()[:12]+'.txt'); target.write_bytes(data)
                    notice_origins[target.name]={'package':dependency['name'],'version':dependency['version'],'entry':name,'sha256':digest(target)}
    for name in archive.toc:
        data=archive.extract(name)
        if not isinstance(data,bytes): continue
        checksum=hashlib.sha256(data).hexdigest()
        if name.lower().endswith(('.dll','.pyd')):
            origin=interpreter_hashes.get(checksum) or wheel_hashes.get(checksum)
            if origin is None: raise ValueError('Built downloader shipped an unpinned native library: '+name)
            native[name]={'sha256':checksum,'origin':origin}
    corresponding=output/'corresponding-source'; corresponding.mkdir()
    shutil.copy2(source,corresponding/source.name)
    shutil.copy2(ROOT/'packaging/downloader-inputs.lock.json',corresponding/'downloader-inputs.lock.json')
    shutil.copy2(Path(__file__),corresponding/'build_downloader.py')
    for dependency in lock['dependencies']:
        if dependency['source']: shutil.copy2(cache/dependency['source']['file'],corresponding/dependency['source']['file'])
    report={'schema':1,'passed':True,'version':version,'pythonVersion':lock['pythonVersion'],'executableSha256':digest(destination/'yt-dlp.exe'),
        'sourceSha256':digest(source),'inputLockSha256':digest(ROOT/'packaging/downloader-inputs.lock.json'),
        'interpreterLockSha256':digest(ROOT/'packaging/inputs-windows.lock.json'),'ejs':main['ejs'],
        'nativeLibraries':native,'notices':notice_origins,'before':previous,'after':current,'inference':False,'mediaRequested':False,
        'productionArgumentsChanged':False,'redistributionApproved':False,'completeNativeClosure':False,
        'noticeFiles':{path.relative_to(notices).as_posix():digest(path) for path in notices.rglob('*') if path.is_file()},
        'sourceFiles':{path.relative_to(corresponding).as_posix():digest(path) for path in corresponding.rglob('*') if path.is_file()}}
    (output/'downloader-build.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':True,'version':version,'python':lock['pythonVersion'],'extractors':len(current['extractors']),'nativeLibraries':len(native)}))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','cache','output'): parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--online',action='store_true')
    args=parser.parse_args(); build(args.inputs.resolve(),args.cache.resolve(),args.output.resolve(),args.online)
