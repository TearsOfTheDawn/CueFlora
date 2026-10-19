"""Measured shipment/source ledger; evidence never implies legal clearance."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import tarfile
from urllib.parse import urlsplit
import zipfile
from release_inputs import ROOT, digest
from notice_names import is_notice_name
from npm_notices import supplemental_notices


def supplemental(cache, output, lock, source_audio=False):
    if not isinstance(lock,dict) or lock.get('schema')!=1 or lock.get('redistributionApproved') is not False or not isinstance(lock.get('files'),list) or not lock['files']:
        raise ValueError('Invalid evidence lock')
    seen=set()
    if any(not isinstance(item,dict) for item in lock['files']): raise ValueError('Invalid evidence input')
    inputs=[item for item in lock['files'] if not source_audio or item.get('role') not in ('origin-checksums','binary-origin-evidence','candidate-build-recipes')]
    for item in inputs:
        if not isinstance(item,dict) or not isinstance(item.get('file'),str) or not isinstance(item.get('url'),str) or not isinstance(item.get('sha256'),str):
            raise ValueError('Invalid evidence input')
        name=item['file']; url=urlsplit(item['url'])
        if not re.fullmatch(r'[A-Za-z0-9_.-]+',name) or name in ('.','..') or name.casefold() in seen or not re.fullmatch('[0-9a-f]{64}',item['sha256']) or url.scheme!='https' or url.hostname not in {'github.com','codeload.github.com','files.pythonhosted.org','static.crates.io'} or url.username is not None or url.password is not None or url.query or url.fragment or url.port not in (None,443) or item.get('role') not in {'origin-checksums','binary-origin-evidence','candidate-build-recipes','yt-dlp-observed-dependency-source','deno-v8-binding-source'}:
            raise ValueError('Invalid evidence input')
        seen.add(name.casefold())
        source=cache/name
        if source.is_symlink() or not source.is_file() or digest(source)!=item['sha256']: raise ValueError('Missing or mismatched evidence input')
    output.mkdir(parents=True,exist_ok=False)
    for item in inputs:
        if item['role']!='binary-origin-evidence': shutil.copy2(cache/item['file'],output/item['file'])
    # Source notices are copied by contents only: no archive path is extracted.
    notices={}
    for item in inputs:
        name=item['file']
        if not name.endswith(('.crate','.tar.gz')): continue
        with tarfile.open(cache/name) as archive:
            for entry in archive.getmembers():
                if not entry.isfile() or entry.size>1024*1024 or not is_notice_name(Path(entry.name).name): continue
                content=archive.extractfile(entry).read()
                filename=hashlib.sha256((name+':'+entry.name).encode()).hexdigest()[:16]+'.txt'
                target=output/'source-notices'/filename; target.parent.mkdir(exist_ok=True); target.write_bytes(content)
                notices[filename]={'sourceArchive':name,'entry':entry.name,'sha256':digest(target)}
    matches={'ffmpeg.exe':None,'ffprobe.exe':None}
    if not source_audio:
        with zipfile.ZipFile(cache/'BtbN-FFmpeg-20260731-win64-gpl.zip') as archive:
            for name in ('ffmpeg.exe','ffprobe.exe'):
                path=next(n for n in archive.namelist() if n.endswith('/bin/'+name)); checksum=hashlib.sha256()
                with archive.open(path) as stream:
                    for chunk in iter(lambda:stream.read(1024*1024),b''): checksum.update(chunk)
                matches[name]=checksum.hexdigest()
    result={'inputs':inputs,'sourceNoticeInventory':notices,'candidateFfmpegHashes':matches,
            'historicalAudioOriginExperimentRequired':not source_audio,
            'candidateRecipeCommit':'a99e8230eae00d1cee38f23076a7a1f55cd984e2',
            'redistributionApproved':False,'correspondingSourceComplete':False}
    (output/'supplemental-evidence.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def ledger(metadata, emitted, source_report, extra):
    files=metadata.get('files',{})
    if not files or not all(isinstance(name,str) and isinstance(checksum,str) and re.fullmatch('[0-9a-f]{64}',checksum) for name,checksum in files.items()):
        raise ValueError('Invalid shipment inventory')
    rows=[]
    sources=source_report['sources']+extra['inputs']
    def row(identifier,kind,version,paths,source_names,licence,obligation):
        notices=[{'path':name,'sha256':checksum} for name,checksum in files.items() if name.startswith('licenses/') and any(part.lower().replace('_','-') in name.lower().replace('_','-') for part in [identifier.split(':')[-1]])]
        evidence=[item for item in sources if any(marker.lower() in item['file'].lower() for marker in source_names)]
        return {'id':identifier,'scope':kind,'version':version,'shippedFiles':[{'path':path,'sha256':files[path]} for path in paths],
                'licence':licence,'notices':notices,'sourceEvidence':evidence,'sourceCoverage':'partial' if evidence else 'not-established',
                'obligation':obligation,'reviewRequired':True}
    for tool in metadata['tools']:
        name=tool['name']; paths=[p for p in files if p=='tools/'+name+'.exe']
        if len(paths)!=1 or files[paths[0]]!=tool['sha256']: raise ValueError('Tool and shipment inventories disagree')
        audio = metadata.get('audioBuild') or {}
        source_built = name in ('ffmpeg','ffprobe') and audio.get('files',{}).get(name+'.exe') == tool['sha256']
        licence = 'LGPL build plus Opus BSD/runtime obligations; see actual -L' if source_built else 'GPLv3-or-later' if name in ('ffmpeg','ffprobe','yt-dlp') else 'MIT plus third-party obligations'
        item=row('tool:'+name,'shipped-executable',tool['versionOutput'],paths,
                 ['FFmpeg-','BtbN-'] if name in ('ffmpeg','ffprobe') else ['yt-dlp-','curl_cffi-','websockets-'] if name=='yt-dlp' else ['Deno-','v8-'],licence,'corresponding-source' if name in ('ffmpeg','ffprobe','yt-dlp') else 'notice-and-third-party-review')
        if name in ('ffmpeg','ffprobe'):
            item['candidateArchiveMatchesActualBytes']=extra['candidateFfmpegHashes'][name+'.exe']==tool['sha256']
            item['originVerified']=item['candidateArchiveMatchesActualBytes']
            if source_built:
                item['originVerified'] = audio.get('sourceSignatureVerified') is True
                item['originEvidence'] = 'Exact source-built audio manifest, source signature and compiler/input locks'
                item['sourceEvidence'] = [{'path':path,'sha256':checksum} for path,checksum in files.items() if path.startswith('corresponding-source/audio/')]
                item['sourceCoverage'] = 'pinned FFmpeg and Opus source/build recipe; runtime obligations still reviewed separately'
        rows.append(item)
    for dependency in metadata.get('dependencies',[]):
        rows.append(row('python:'+dependency['name'],'analysis-observed-shipped-module',dependency['version'],[],['CPython-' if dependency['name']=='python' else dependency['name']],'see matched notices','licence-specific-review'))
    wheel_pins=json.loads((ROOT/'packaging/inputs-windows.lock.json').read_text()).get('wheelNativeFiles',[])
    for name in sorted(files):
        if name.lower().endswith(('.dll','.pyd')):
            audio = metadata.get('audioBuild') or {}
            source_built = name.startswith('tools/') and audio.get('files',{}).get(Path(name).name) == files[name]
            item = row('native:'+Path(name).name,'shipped-native-library','not-established',[name],['CPython-','python-build-standalone-'],'see interpreter/tool notices; exact closure requires review','native-binary-review')
            wheel=next((pin for pin in wheel_pins if pin['sha256']==files[name]),None)
            if wheel:
                component=wheel['wheel'].split('-')[0]
                item.update({'originEvidence':wheel,'originVerified':True,'version':wheel['wheel'].split('-')[1],
                    'licence':'see exact '+component+' wheel notices, including bundled native-library terms; not CPython licence',
                    'notices':[{'path':path,'sha256':checksum} for path,checksum in files.items() if path.lower().startswith('licenses/'+component.lower()+'/')],
                    'sourceEvidence':[entry for entry in sources if entry['file'].lower().startswith(component.lower()+'-')],
                    'sourceCoverage':'exact upstream wheel bytes and matching project source archive; native build/source linkage remains a review obligation'})
            if source_built:
                family = 'Opus' if 'opus' in name else 'MinGW compiler runtime' if 'winpthread' in name else 'FFmpeg'
                item.update({'version':'1.6.1' if family=='Opus' else audio['version'] if family=='FFmpeg' else 'see exact compiler package lock',
                    'licence':'BSD-style; see source COPYING' if family=='Opus' else 'LGPL-2.1-or-later' if family=='FFmpeg' else 'see MinGW runtime notices; review required',
                    'sourceEvidence':[{'path':path,'sha256':checksum} for path,checksum in files.items() if path.startswith('corresponding-source/audio/')],
                    'notices':[{'path':path,'sha256':checksum} for path,checksum in files.items() if path.startswith('licenses/source-built-audio/')],
                    'sourceCoverage':'source archives and build/compiler evidence; runtime closure review still required'})
            rows.append(item)
    packages={(p['name'],p['version']):p for record in emitted for p in record['packages']}
    for package in packages.values():
        rows.append({'id':'javascript:'+package['name'],'scope':'observed-emitted-module','version':package['version'],'licence':package.get('license') or 'not-established',
                     'sourceCoverage':'package-lock tarball evidence','reviewRequired':True})
    build_only=[item for item in metadata.get('buildEnvironmentDependencies',[]) if item['name'].lower() not in {p['name'].lower() for p in metadata.get('dependencies',[])}]
    host=[name for name in files if name=='cueflora-host.exe']
    rows.append(row('bootloader:pyinstaller','embedded-native-bootloader',metadata.get('packager'),host,[],'GPLv2-or-later with PyInstaller bootloader exception','exception-and-notice-review'))
    return {'schema':1,'product':'CueFlora','rows':rows,'completeRuntimeFileInventory':files,'buildOnlyPython':build_only,
            'denoSourceDependencyInventory':source_report['denoSourceDependencies'],'denoInventoryScope':'Source Cargo.lock, not proof of binary shipment',
            'ytDlpObservedMetadata':source_report['ytDlpEmbeddedMetadata'],'sourceEvidence':sources,
            'sourceNoticeInventory':extra['sourceNoticeInventory'],'redistributionApproved':False,'correspondingSourceComplete':False,
            'remainingObligations':['Source-built FFmpeg/Opus LGPL/BSD and MinGW/GCC runtime obligation review' if metadata.get('audioBuild') else 'FFmpeg exact origin and enabled-library corresponding sources/recipes','yt-dlp unobserved bundled/native dependency source closure',
                'Deno actual V8/native third-party closure','Microsoft/native interpreter redistribution review','emitted JavaScript notice review'],
            'interpretation':'Bytes, source archives and notices are evidence. Missing/partial matches remain unresolved; no automatic legal approval.'}


def file_evidence(files, rows):
    """Index original rows without copying their complete notice/source lists per file."""
    matched = {name:[] for name in files}
    for index, item in enumerate(rows):
        paths = {entry.get('path') for field in ('shippedFiles','notices','sourceEvidence')
            for entry in item.get(field,[]) if isinstance(entry,dict)}
        for field in ('shippedFiles','notices','sourceEvidence'):
            for entry in item.get(field,[]):
                if not isinstance(entry,dict) or entry.get('path') not in files: continue
                if entry.get('sha256') != files[entry['path']]:
                    raise ValueError('File attribution and shipment hashes disagree')
        for name in paths.intersection(files):
            matched[name].append(index)
    result = {}
    for name, checksum in files.items():
        indexes = matched[name]
        result[name] = {'sha256':checksum,'components':[
            {'ledgerRow':index,**{field:rows[index].get(field,'not-established')
                for field in ('id','version','licence','sourceCoverage')}}
            for index in indexes], 'attribution': 'matched ledger evidence' if indexes else 'unassigned container/generated/data file; review required',
            'licenceClosure':'review-required; inventory coverage is not legal approval'}
    return result


def require_file_attribution(report):
    """Engineering needs actual per-file attribution, not a declared green flag."""
    files=report.get('completeRuntimeFileInventory')
    if not isinstance(files,dict) or not files or not isinstance(report.get('rows'),list):
        raise ValueError('Complete runtime inventory and attribution rows required')
    expected=file_evidence(files,report['rows'])
    if (any(not item['components'] for item in expected.values()) or report.get('fileCoverage')!=expected or
            report.get('unassignedRuntimeFiles')!=[] or report.get('fileAttributionComplete') is not True):
        raise ValueError('Runtime file attribution is incomplete or inconsistent')
    return True


def setup_inventory(executable, analysis, interpreter_hashes, runtime_hashes=None, wheel_hashes=None):
    from PyInstaller.archive.readers import CArchiveReader
    from release_inputs import shipped_python
    archive = CArchiveReader(str(executable))
    files = {}
    for name in archive.toc:
        content = archive.extract(name)
        if isinstance(content, bytes): files[name.replace('\\','/')] = hashlib.sha256(content).hexdigest()
    native = []
    runtime_hashes = runtime_hashes or {}
    wheel_hashes = wheel_hashes or {}
    for name, checksum in files.items():
        if not name.lower().endswith(('.dll','.pyd')) or name.startswith('bundle/runtime/'): continue
        family = 'Tcl' if Path(name).name.lower().startswith('tcl') else 'Tk' if Path(name).name.lower().startswith('tk') else 'Python/native'
        native.append({'path':name,'sha256':checksum,'noticeFamily':family,
            'lockedInterpreterFile':interpreter_hashes.get(checksum),'lockedRuntimeFile':runtime_hashes.get(checksum),
            'lockedWheelFile':wheel_hashes.get(checksum),
            'originMatched':checksum in interpreter_hashes or checksum in runtime_hashes or checksum in wheel_hashes,
            'licenceClosure':'review-required; payload matching is not licence clearance'})
    return {'executableSha256':digest(executable),'archiveEntryHashes':files,'nativeLibraries':native,
            'analysisObservedPythonModules':shipped_python(analysis),
            'scope':'Exact onefile entry bytes plus executable hash; embedded runtime is separately inventoried. No legal approval.'}


def write(runtime, extension, source_report, extra, output, source_notices=None, setup=None, setup_analysis=None):
    output.mkdir(parents=True,exist_ok=False)
    metadata=json.loads((runtime/'runtime-manifest.json').read_text())
    emitted=[json.loads(path.read_text()) for path in extension.rglob('cueflora-bundled-dependencies-*.json')]
    if not emitted: raise ValueError('Emitted extension inventories missing')
    report=ledger(metadata,emitted,source_report,extra)
    auth=metadata.get('authNativeNoticeEvidence')
    if auth:
        detailed=source_report.get('authNativeNoticeEvidence')
        if not detailed or detailed['lockSha256']!=auth['lockSha256'] or len(detailed['components'])!=auth['componentCount']:raise ValueError('Authentication source/runtime notice binding mismatch')
        report['authNativeNoticeEvidence']=detailed
    repository=metadata.get('repositoryNoticeEvidence')
    if repository:
        detailed=source_report.get('repositoryNoticeEvidence')
        if not detailed or detailed['inputInventorySha256']!=repository['inputInventorySha256']: raise ValueError('Repository source/runtime binding mismatch')
        report['repositoryNoticeEvidence']=detailed
    cargo=metadata.get('cargoNoticeEvidence')
    if cargo:
        detailed=source_report.get('cargoNoticeEvidence')
        if not detailed or detailed['cargoLockSha256']!=cargo['cargoLockSha256'] or detailed['registryPackageCount']!=cargo['registryPackageCount']:
            raise ValueError('Cargo source evidence and runtime binding disagree')
        report['cargoNoticeEvidence']=detailed
    interpreter=metadata.get('interpreterComponentEvidence')
    if interpreter:
        if source_report.get('interpreterComponentEvidence')!=interpreter: raise ValueError('Interpreter notice evidence and runtime binding disagree')
        report['interpreterComponentEvidence']=interpreter
        for name,item in interpreter['components'].items():
            report['rows'].append({'id':'interpreter-native-notice:'+name,'scope':'exact-matching-interpreter-build-source notice and recipe input',
                'version':(item['declaredBuildInput'] or {}).get('version','see bundled CPython source'),
                'licence':'see original notice','notices':[{'path':'licenses/interpreter-components/'+item['notice'],'sha256':item['noticeSha256']}],
                'sourceEvidence':[interpreter['sourceInput']],'sourceCoverage':item['versionScope'],'reviewRequired':True})
    v8=metadata.get('v8NoticeEvidence')
    if v8:
        if source_report.get('v8NoticeEvidence')!=v8: raise ValueError('V8 notice evidence and runtime binding disagree')
        report['v8NoticeEvidence']=v8
        report['rows'].append({'id':'Deno/V8-core-notice-evidence','scope':'exact-core/source-tree-notices; not complete binary dependency closure',
            'version':'15.0.245.2-rusty / binding 150.4.0','licence':'MIT binding, BSD V8 and source-specific third-party terms',
            'sourceEvidence':v8['sourceInputs'],'sourceCoverage':'matching declared commit/version, crate VCS dirty flag retained',
            'notices':[{'path':'licenses/deno-v8-source-notices/'+name,'sha256':item['sha256']} for name,item in v8['notices'].items()],
            'reviewRequired':True})
    downloader=metadata.get('downloaderBuild')
    if downloader:
        if source_report.get('sourceBuiltDownloader')!=downloader: raise ValueError('Downloader source evidence and runtime binding disagree')
        report['sourceBuiltDownloader']=downloader
        report['curlSourceEvidence']=source_report.get('curlSourceEvidence')
        lock=json.loads((ROOT/'packaging/downloader-inputs.lock.json').read_text())
        for item in lock['dependencies']:
            report['rows'].append({'id':'downloader-python:'+item['name'],'scope':'exact-upstream-pinned-frozen-downloader-dependency',
                'version':item['version'],'licence':item['declaredLicence'],'reviewRequired':True,
                'sourceEvidence':[item['source']],'sourceCoverage':'exact sdist plus wheel source/hash provenance',
                'notices':[{'path':'licenses/source-built-downloader/'+name,'sha256':record['sha256']} for name,record in downloader['notices'].items() if record['package']==item['name']],
                'nativeFiles':[{'path':name,**record} for name,record in downloader['nativeLibraries'].items() if isinstance(record['origin'],dict) and record['origin']['package']==item['name']]})
        if report['curlSourceEvidence']:
            for item in report['curlSourceEvidence']['sourceInputs']:
                report['rows'].append({'id':'downloader-native:'+item.get('package','curl-impersonate'),'scope':'byte-matched-native-DLL recipe input',
                    'version':item.get('version','2.0.0'),'licence':'see original source notices','sourceEvidence':[item],
                    'sourceCoverage':'exact upstream recipe inputs; binary origin hash matched, not independent proof of every build flag',
                    'notices':[{'evidencePath':name,**entry} for name,entry in report['curlSourceEvidence']['notices'].items() if entry['sourceArchive']==item['file']],
                    'reviewRequired':True})
    report['observedPythonSourceEvidence'] = source_report.get('observedPythonSources')
    from licence_attribution import augment, completeness
    augment(metadata,report,runtime)
    interpreter=json.loads((ROOT/'packaging/inputs-windows.lock.json').read_text())
    hashes={item['sha256']:item['file'] for item in interpreter['interpreterFiles']}
    wheel_hashes={item['sha256']:item['wheel']+':'+item['file'] for item in interpreter.get('wheelNativeFiles',[])}
    audio = metadata.get('audioBuild') or {}
    audio_hashes = {'tools/'+name:checksum for name,checksum in audio.get('files',{}).items() if name.endswith('.dll')}
    report['nativeInterpreterPayloadMatches']={name:{'sha256':checksum,'lockedInterpreterFile':hashes.get(checksum),
        'lockedWheelFile':wheel_hashes.get(checksum),
        'sourceBuiltAudioFile':name if audio_hashes.get(name)==checksum else None,
        'matched':checksum in hashes or checksum in wheel_hashes or audio_hashes.get(name)==checksum}
        for name,checksum in metadata['files'].items() if name.lower().endswith(('.dll','.pyd'))}
    if any(not item['matched'] for item in report['nativeInterpreterPayloadMatches'].values()):
        raise ValueError('Runtime shipped an unpinned native library')
    if audio:
        report['sourceBuiltAudio'] = {'version':audio['version'],'sourceSignatureVerified':audio['sourceSignatureVerified'],
            'inputLockSha256':audio['inputLockSha256'],'toolchainLockSha256':audio['toolchainLockSha256'],
            'exactFileHashes':audio['files'],'compatibility':metadata.get('audioCompatibility'),
            'correspondingSourcePaths':[name for name in metadata['files'] if name.startswith('corresponding-source/audio/')],
            'legalReviewRequired':True}
    report['pythonInterpreterVersion']=interpreter['pythonVersion']
    report['ytDlpDependencyRows']=[{'archiveMetadataPath':name,'distribution':fields.get('Name'),
        'version':fields.get('Version'),'declaredLicence':fields.get('License'),
        'sourceEvidence':[item for item in extra['inputs'] if fields.get('Name','').lower().replace('-','_') in item['file'].lower().replace('-','_')],
        'scope':'Observed executable metadata only; unobserved dependencies remain unresolved','reviewRequired':True}
        for name,fields in source_report['ytDlpEmbeddedMetadata'].items()]
    if setup is not None and setup_analysis is not None:
        report['setupShipment']=setup_inventory(setup,setup_analysis,hashes,
            {checksum:name for name,checksum in metadata['files'].items() if name.startswith('tools/') and name.endswith('.dll')},wheel_hashes)
        if any(not item['originMatched'] for item in report['setupShipment']['nativeLibraries']):
            raise ValueError('Setup shipped an unpinned native library')
    for tool in ('ffmpeg','ffprobe'):
        evidence=json.loads((runtime/'licenses'/f'{tool}-binary-evidence.json').read_text())
        flags=sorted(set(re.findall(r'--enable-(lib[\w-]+|gmp|zlib|lzma|iconv|vulkan|opencl|amf|ffnvcodec|cuda-llvm|frei0r|lv2|openal|sdl2)',evidence['outputs']['-buildconf'])))
        report[tool+'EnabledExternalComponents']=[{'flag':'--enable-'+flag,
            'sourceCoverage':'source-built pinned Opus; see sourceBuiltAudio' if audio and flag=='libopus' else 'not-established for the actual binary',
            'matchingRecipeArchive':'source-built exact recipe' if audio else 'candidate only; see exact-binary mismatch'} for flag in flags]
    report['fileCoverage'] = file_evidence(metadata['files'],report['rows'])
    report['fileCoverageScope'] = 'Each component ledgerRow is a zero-based reference into rows, where complete original notice/source evidence is retained once. References establish recorded attribution, not licence approval.'
    report['unassignedRuntimeFiles'] = [name for name,item in report['fileCoverage'].items() if not item['components']]
    js_rows = {item['id'].removeprefix('javascript:'):item for item in report['rows'] if item['id'].startswith('javascript:')}
    js_notice_text = []
    for name,row in js_rows.items():
        package = ROOT/'node_modules'/name
        notices = [path for path in package.iterdir() if path.is_file() and is_notice_name(path.name)] if package.is_dir() else []
        row['noticeEvidence'] = [{'packageEntry':path.name,'sha256':digest(path)} for path in notices]
        origins = supplemental_notices(name,row['version']) if not notices else []
        for item in origins:
            notices.append(item['path'])
            row['noticeEvidence'].append({'packageEntry':item['entry'],'sha256':item['sha256'],'origin':item['origin']})
        row['noticeEvidenceComplete'] = bool(notices)
        for path in notices:
            target = output/'javascript-notices'/name.replace('/','_')/path.name
            target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(path,target)
            js_notice_text.append('\n===== '+row['id']+' '+row['version']+' '+path.name+' SHA-256 '+digest(path)+' =====\n'+path.read_text(encoding='utf-8',errors='replace'))
    report['extensionFileCoverage'] = {}
    for path in sorted(extension.rglob('*')):
        if not path.is_file(): continue
        name = path.relative_to(extension).as_posix()
        packages = set()
        for record in emitted:
            if name in record.get('chunkPackages',{}): packages.update(record['chunkPackages'][name])
        report['extensionFileCoverage'][name] = {'sha256':digest(path),'ownSourceLicence':'MIT; original Substrata attribution retained',
            'bundledDependencies':[js_rows[item] for item in sorted(packages)],
            'mappingScope':'Observed emitted chunk modules; static/generated files retain source-export review', 'reviewRequired':True}
    if 'setupShipment' in report:
        report['setupShipment']['fileCoverage'] = {
            name:{'sha256':checksum,'components':['inventoried embedded runtime'] if name.startswith('bundle/runtime/') else
                ['Tcl/Tk'] if name.startswith(('_tcl_data/','_tk_data/')) or Path(name).name.startswith(('tcl','tk')) else
                ['CueFlora MIT / Python / PyInstaller; see analysis-observed modules and interpreter notices'], 'reviewRequired':True}
            for name,checksum in report['setupShipment']['archiveEntryHashes'].items()}
    report.update(completeness(report))
    (output/'dependency-ledger.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    notices=['CueFlora consolidated available notices. This is not redistribution clearance.\nOriginal notice bytes remain in the separately hashed notice files.\n']
    notices.extend(js_notice_text)
    observed_notices = output.parent/'licence-evidence/observed-python/notices'
    if observed_notices.is_dir():
        shutil.copytree(observed_notices,output/'observed-python-notices')
        for path in sorted(observed_notices.iterdir()):
            notices.append('\n===== observed Python source notice '+path.name+' SHA-256 '+digest(path)+' =====\n'+path.read_text(encoding='utf-8',errors='replace'))
    if source_notices and source_notices.is_dir():
        shutil.copytree(source_notices,output/'source-notices')
        for path in sorted(source_notices.iterdir()):
            notices.append('\n===== supplemental source notice '+path.name+' (SHA-256 '+digest(path)+') =====\n'+path.read_text(encoding='utf-8',errors='replace'))
    for path in sorted((runtime/'licenses').rglob('*')):
        if path.is_file() and (path.suffix.lower() in ('.txt','.md','.terms') or path.parent.name=='source-built-audio'):
            notices.append('\n===== '+path.relative_to(runtime).as_posix()+' (SHA-256 '+digest(path)+') =====\n'+path.read_text(encoding='utf-8',errors='replace'))
    (output/'CONSOLIDATED_NOTICES.txt').write_text('\n'.join(notices),encoding='utf-8')
    return report
