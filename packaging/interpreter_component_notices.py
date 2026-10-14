"""Retain original Windows interpreter component notices from its pinned build source."""
import ast
import hashlib
import json
from pathlib import Path
import re
import ssl
import sqlite3
import zlib
import pyexpat
import decimal
import zipfile
from release_inputs import ROOT,digest,verify_environment

COMPONENTS={
    'cpython':('cpython-3.13','LICENSE.cpython.txt'),
    'bzip2':('bzip2','LICENSE.bzip2.txt'),
    'expat':(None,'LICENSE.expat.txt'),
    'libffi':('libffi','LICENSE.libffi.txt'),
    'liblzma':('xz','LICENSE.liblzma.txt'),
    'mpdecimal':('mpdecimal','LICENSE.mpdecimal.txt'),
    'openssl':('openssl-3.5','LICENSE.openssl-3.txt'),
    'sqlite':('sqlite','LICENSE.sqlite.txt'),
    'tcl':('tcl-8612','LICENSE.tcl.txt'),
    'tk':('tk-8612','LICENSE.tcl.txt'),
    'zlib':('zlib','LICENSE.zlib.txt'),
}


def read_downloads(content):
    tree=ast.parse(content)
    matches=[node for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='DOWNLOADS' for target in node.targets)]
    if len(matches)!=1: raise ValueError('Exact standalone download manifest required')
    try: result=ast.literal_eval(matches[0].value)
    except (ValueError,TypeError): raise ValueError('Build download manifest must contain literals only') from None
    if not isinstance(result,dict): raise ValueError('Malformed build download manifest')
    return result


def collect(inputs,output):
    if output.exists(): raise ValueError('Fresh interpreter notice evidence required')
    lock=json.loads((ROOT/'packaging/inputs-windows.lock.json').read_text())
    verify_environment(lock)
    record=next(item for item in lock['files'] if item['file']=='python-build-standalone-20260814-source.zip')
    source=inputs/record['file']
    if source.is_symlink() or digest(source)!=record['sha256']: raise ValueError('Pinned interpreter build-source mismatch')
    core_record=next(item for item in lock['files'] if item['file']=='CPython-3.13.15-source.zip')
    core_source=inputs/core_record['file']
    if core_source.is_symlink() or digest(core_source)!=core_record['sha256']: raise ValueError('Pinned CPython source mismatch')
    with zipfile.ZipFile(core_source) as archive:
        expat_notice=archive.read('cpython-3.13.15/Modules/expat/COPYING')
        header=archive.read('cpython-3.13.15/Modules/expat/expat.h').decode()
        expat_version='.'.join(re.search(r'#\s*define XML_'+part+r'_VERSION\s+(\d+)',header)[1] for part in ('MAJOR','MINOR','MICRO'))
    runtime_versions={'openssl':re.search(r'OpenSSL (\d+\.\d+\.\d+)',ssl.OPENSSL_VERSION)[1],
        'sqlite':sqlite3.sqlite_version,'zlib':zlib.ZLIB_VERSION,'expat':pyexpat.EXPAT_VERSION.removeprefix('expat_'),
        'mpdecimal':decimal.__libmpdec_version__}
    if runtime_versions['expat']!=expat_version: raise ValueError('Bundled Expat source/runtime version mismatch')
    output.mkdir(parents=True); notices={}; components={}
    prefix='python-build-standalone-20260814/'
    with zipfile.ZipFile(source) as archive:
        recipe=archive.read(prefix+'cpython-windows/build.py')
        downloads=read_downloads(archive.read(prefix+'pythonbuild/downloads.py').decode())
        for component,(key,name) in COMPONENTS.items():
            content=expat_notice if component=='expat' else archive.read(prefix+name)
            if not content: raise ValueError('Empty required interpreter component notice')
            target=output/'notices'/name; target.parent.mkdir(exist_ok=True)
            if not target.exists(): target.write_bytes(content)
            notices[name]={'sourceArchive':core_record['file'] if component=='expat' else record['file'],
                'sourceEntry':'cpython-3.13.15/Modules/expat/COPYING' if component=='expat' else prefix+name,'sha256':hashlib.sha256(content).hexdigest()}
            selection=downloads[key] if key else None
            if selection is not None and (not isinstance(selection,dict) or not isinstance(selection.get('version'),str)):
                raise ValueError('Missing exact interpreter dependency version')
            if component in runtime_versions and selection is not None:
                declared=selection.get('actual_version',selection['version'])
                if component=='sqlite' and declared.endswith('.0'): declared=declared[:-2]
                if declared!=runtime_versions[component]: raise ValueError('Declared interpreter dependency and runtime version mismatch: '+component)
            components[component]={'notice':name,'noticeSha256':notices[name]['sha256'],
                'declaredBuildInput':selection,'observedRuntimeVersion':runtime_versions.get(component),
                'versionScope':'Pinned build recipe input; runtime version separately recorded where available' if selection else 'Bundled CPython Expat source; do not substitute the Unix-only standalone Expat download',
                'binarySourceIdentityProven':False}
    (output/'windows-build.py').write_bytes(recipe)
    report={'schema':1,'sourceInput':record,'cpythonSourceInput':core_record,'windowsBuildRecipeSha256':hashlib.sha256(recipe).hexdigest(),
        'components':components,'notices':notices,'noticeFiles':{name:item['sha256'] for name,item in notices.items()},
        'runtimeVersions':runtime_versions,'versionProbeScope':'Actual hash-locked build interpreter; frozen payload hashes are independently checked, not a binary-source equivalence claim',
        'redistributionApproved':False,'nativeSourceClosureComplete':False,
        'remaining':['Microsoft runtime redistribution terms/eligibility','Exact native binary/source version linkage where the build recipe alone is insufficient'],
        'scope':'Original notices from the exact source of the matching official interpreter archive. Not execution of upstream build code, legal clearance, or proof that every listed source component is shipped.'}
    (output/'interpreter-component-notices.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'componentFamilies':len(components),'originalNotices':len(notices),'redistributionApproved':False}))
    return report


def validate_evidence(folder):
    report=json.loads((folder/'interpreter-component-notices.json').read_text())
    main=json.loads((ROOT/'packaging/inputs-windows.lock.json').read_text())
    record=next(item for item in main['files'] if item['file']=='python-build-standalone-20260814-source.zip')
    core_record=next(item for item in main['files'] if item['file']=='CPython-3.13.15-source.zip')
    if report.get('sourceInput')!=record or report.get('cpythonSourceInput')!=core_record or set(report.get('components',{}))!=set(COMPONENTS) or report.get('redistributionApproved') is not False or report.get('nativeSourceClosureComplete') is not False or digest(folder/'windows-build.py')!=report.get('windowsBuildRecipeSha256'):
        raise ValueError('Interpreter component evidence binding mismatch')
    paths=list((folder/'notices').rglob('*'))
    if any(path.is_symlink() for path in paths) or {path.name:digest(path) for path in paths if path.is_file()}!=report.get('noticeFiles'):
        raise ValueError('Changed/missing interpreter component notices')
    if set(report['notices'])!=set(report['noticeFiles']) or any(item['sha256']!=report['noticeFiles'][name] for name,item in report['notices'].items()):
        raise ValueError('Interpreter notice origin inventory mismatch')
    for family,(key,name) in COMPONENTS.items():
        component=report['components'][family]
        if component.get('notice')!=name or component.get('noticeSha256')!=report['noticeFiles'].get(name) or component.get('binarySourceIdentityProven') is not False:
            raise ValueError('Interpreter component and notice mismatch')
    return report


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','output'): parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args(); collect(args.inputs.resolve(),args.output.resolve())
