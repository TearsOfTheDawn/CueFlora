"""Read pinned executable/source metadata; no media request or AI inference."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import zipfile
from release_inputs import ROOT, digest, validate_lock


def audit(cache,output,downloader_build=None):
    if output.exists(): raise ValueError('Fresh tool-audit output required')
    lock=validate_lock(json.loads((ROOT/'packaging/inputs-windows.lock.json').read_text()))
    records={item['file']:item for item in lock['files']}
    for name in ('yt-dlp.exe','deno.exe','Deno-2.9.7-source.zip'):
        if digest(cache/name) != records[name]['sha256']: raise ValueError('Tool audit input mismatch')
    output.mkdir(parents=True)
    from PyInstaller.archive.readers import CArchiveReader
    executable=cache/'yt-dlp.exe'
    built=None
    if downloader_build:
        from build_downloader import validate_build
        built=validate_build(downloader_build)
        executable=downloader_build/'bin/yt-dlp.exe'
    reader=CArchiveReader(str(executable))
    entries={}
    for name in reader.toc:
        data=reader.extract(name)
        if isinstance(data,bytes): entries[name.replace('\\','/')]=hashlib.sha256(data).hexdigest()
    environment={key.upper():value for key,value in os.environ.items() if not any(token in key.upper() for token in ('TOKEN','KEY','PASSWORD','SECRET'))}
    environment['PATH']=str(Path(environment.get('SYSTEMROOT',r'C:\Windows'))/'System32')
    for key in ('PYTHONPATH','PYTHONHOME','LD_LIBRARY_PATH','DYLD_LIBRARY_PATH'): environment.pop(key,None)
    result=subprocess.run([str(executable),'--ignore-config','--no-plugin-dirs','--no-remote-components',
        '--no-js-runtimes','--js-runtimes','deno:'+str(cache/'deno.exe'),'--verbose'],
        capture_output=True,text=True,timeout=30,env=environment)
    if result.returncode not in (0,2) or result.returncode==2 and 'You must provide at least one URL' not in result.stderr:
        raise ValueError('Pinned downloader metadata probe failed')
    lines=[line for line in result.stderr.splitlines() if line.startswith('[debug] ') and any(marker in line for marker in ('Python ','Optional libraries:','yt-dlp version '))]
    if not lines: raise ValueError('Downloader did not expose required dependency metadata')
    versions=[]
    for line in lines:
        if 'Optional libraries:' in line:
            versions=[{'name':match[0],'version':match[1]} for match in re.findall(r'([A-Za-z0-9_-]+)-([0-9][A-Za-z0-9_.+-]*)',line)]
    deno_source=[]
    native_versions={}
    bytecode_versions={}
    pyz_name=next((name for name in reader.toc if name.endswith('.pyz')),None)
    if pyz_name:
        pyz=reader.open_embedded_archive(pyz_name)
        for name in ('cffi','pycparser','idna.package_data','charset_normalizer.version'):
            if name not in pyz.toc: continue
            raw=pyz.extract(name,raw=True)
            bytecode_versions[name]={'sha256':hashlib.sha256(raw).hexdigest(),
                'literalVersionStrings':sorted({value.decode() for value in re.findall(rb'(?<![A-Za-z0-9])\d{1,4}\.\d{1,3}(?:\.\d{1,3})?(?![A-Za-z0-9])',raw)}),
                'scope':'Literal constants, not execution or automatic declaration of package version'}
    for name in reader.toc:
        if not name.lower().endswith(('.dll','.pyd')): continue
        data=reader.extract(name)
        # Record literal observed build strings, without loading native code or
        # asserting that a version string identifies every statically linked library.
        strings=re.findall(rb'[\x20-\x7e]{8,}',data)
        markers=[text.decode('ascii') for text in strings if re.search(rb'(?:libcurl/\d|OpenSSL \d|BoringSSL|libidn2/\d|libssh2/\d|zstd/\d)',text)]
        if markers: native_versions[name]={'sha256':hashlib.sha256(data).hexdigest(),'observedBuildStrings':markers[:20]}
    with zipfile.ZipFile(cache/'Deno-2.9.7-source.zip') as archive:
        for name in archive.namelist():
            if name.endswith('/') or archive.getinfo(name).file_size>1024*1024: continue
            if name.endswith('.rs') and ('cli/args/' in name or name.endswith('/main.rs')):
                content=archive.read(name).decode('utf-8',errors='replace')
                if 'license' in content.lower():
                    deno_source.append({'entry':name,'sha256':hashlib.sha256(archive.read(name)).hexdigest(),
                        'licenseRelatedLines':[line.strip() for line in content.splitlines() if 'license' in line.lower()][:20]})
    report={'schema':1,'published':False,'inference':False,'mediaRequested':False,
        'ytDlpSha256':digest(executable),'ytDlpEmbeddedEntryHashes':entries,'downloaderBuild':built,
        'ytDlpMetadataProbe':lines,'observedOptionalLibraryVersions':versions,'observedNativeBuildStrings':native_versions,
        'embeddedBytecodeVersionEvidence':bytecode_versions,
        'denoSha256':digest(cache/'deno.exe'),'denoVersion':subprocess.check_output([str(cache/'deno.exe'),'--version'],text=True,timeout=15),
        'denoLicenseSourceInspection':deno_source,
        'scope':'Observed runtime versions/bytes; source-lock packages and cross-platform notices are not proof every component is shipped',
        'redistributionApproved':False}
    (output/'tool-dependency-audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'metadata':lines,'versions':versions,'denoLicenseInspection':deno_source},indent=2))
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('cache','output'): parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--downloader-build',type=Path)
    args=parser.parse_args(); audit(args.cache.resolve(),args.output.resolve(),args.downloader_build)
