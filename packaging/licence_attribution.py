"""Explicit file/container attribution and licence-specific evidence, not legal approval."""
import json
from pathlib import Path
import zipfile
from release_inputs import digest
from npm_notices import ROOT, supplemental_notices


def augment(metadata, report, runtime):
    files = metadata['files']; rows = report['rows']
    def add(identifier,scope,version,licence,names,evidence=(),obligation='retain-notice',verified=False):
        rows.append({'id':identifier,'scope':scope,'version':version,'licence':licence,
            'shippedFiles':[{'path':name,'sha256':files[name]} for name in names],
            'notices':[{'path':name,'sha256':files[name]} for name in evidence if name in files],
            'sourceEvidence':[],'sourceCoverage':'not-required-by-notice-only-licence' if obligation=='retain-notice' else 'see corresponding source inventory',
            'obligation':obligation,'originVerified':verified,'reviewRequired':True})
    own = [name for name in files if name == '_internal/cueflora_host/whisper.py' or name in ('licenses/audio-build.json','licenses/audio-compatibility.json','licenses/audio-conformance.json','licenses/notice-origins.json','licenses/interpreter/notice-inventory.json')]
    own.extend(name for name in files if name=='licenses/downloader-build.json' or name.startswith('corresponding-source/downloader/') and Path(name).name in ('build_downloader.py','downloader-inputs.lock.json'))
    own.extend(name for name in files if name=='licenses/v8-notice-evidence.json')
    own.extend(name for name in files if name=='licenses/interpreter-component-notices.json')
    own.extend(name for name in files if name=='licenses/cargo-notice-inventory.json')
    own.extend(name for name in files if name=='licenses/repository-notice-inventory.json')
    add('cueflora:source-and-generated-evidence','own-source-or-generated-metadata',metadata['hostVersion'],'MIT; upstream Substrata notice retained',own,verified=True)
    notices = metadata.get('noticeOrigins',{})
    for name,item in notices.items():
        if name not in files or item['sha256'] != files[name]: raise ValueError('Notice origin and shipment hashes disagree')
        add('notice:'+item['component'],item['scope'],item['version'],item['licence'],[name],[name],verified=True)
    # The runtime also carries public upstream notices for the complete package.
    # Attribute those exact notice bytes without claiming the extension code is
    # embedded in the Python host. Unknown files still have no automatic owner.
    policy=json.loads((ROOT/'packaging/npm-notices.lock.json').read_text(encoding='utf-8'))
    for package in policy['packages']:
        name='licenses/upstream/'+package['file']
        if name not in files: continue
        notice,=supplemental_notices(package['name'],package['version'])
        if files[name]!=notice['sha256'] or digest(runtime/name)!=notice['sha256']:
            raise ValueError('Supplemental runtime notice origin mismatch')
        add('extension-original-notice:'+package['name'],'original extension notice only; native code shipment not asserted',
            package['version'],'see exact original upstream notice',[name],[name],verified=True)
        rows[-1].update({'packageCodeShippedByThisRow':False,
            'sourceCoverage':'original source-retained notice; extension code assessed separately',
            'noticeOrigin':{'url':notice['origin'],'npmIntegrity':notice['integrity'],'sha256':notice['sha256']}})
    for component in ('Python','Tcl','Tk'):
        names = [name for name in files if name.startswith('licenses/interpreter/'+component+'-') or component=='Tcl' and name=='licenses/upstream/Tcl-8.6.12-license.terms']
        if names:
            add('interpreter-notice:'+component,'exact-interpreter-notice',metadata['python'] if component=='Python' else '8.6.12; binary health separately measured',
                'PSF-2.0 plus included component notices' if component=='Python' else 'Tcl/Tk permissive licence; see original terms',names,names,verified=True)
    downloader=metadata.get('downloaderBuild')
    if downloader:
        for notice,item in downloader['notices'].items():
            name='licenses/source-built-downloader/'+notice
            if files.get(name)!=item['sha256']: raise ValueError('Downloader notice origin mismatch')
            add('downloader-notice:'+item['package'],'exact-downloader-wheel-notice',item['version'],'see original dependency licence',[name],[name],verified=True)
        for name in files:
            if name.startswith('corresponding-source/downloader/') and Path(name).name not in ('build_downloader.py','downloader-inputs.lock.json'):
                add('downloader-source:'+Path(name).name,'exact-pinned-downloader-source-archive',downloader['version'],'source-specific original terms',[name],obligation='corresponding-source',verified=True)
    v8=metadata.get('v8NoticeEvidence')
    if v8:
        for notice,item in v8['notices'].items():
            name='licenses/deno-v8-source-notices/'+notice
            if files.get(name)!=item['sha256']: raise ValueError('V8 notice origin mismatch')
            add('v8-notice:'+item['sourceEntry'],'exact-source-notice; source tree includes tests/tools','15.0.245.2 / binding 150.4.0',
                'source-specific original terms; not every listed source is claimed shipped',[name],[name],verified=True)
    interpreter=metadata.get('interpreterComponentEvidence')
    if interpreter:
        for notice,item in interpreter['notices'].items():
            name='licenses/interpreter-components/'+notice
            if files.get(name)!=item['sha256']: raise ValueError('Interpreter component notice origin mismatch')
            add('interpreter-component-notice:'+notice,'exact-pinned-build-source-notice','see dependency build recipe',
                'source-specific original terms',[name],[name],verified=True)
    cargo=metadata.get('cargoNoticeEvidence')
    if cargo:
        inventory=json.loads((runtime/'licenses/cargo-notice-inventory.json').read_text())
        if inventory['cargoLockSha256']!=cargo['cargoLockSha256']: raise ValueError('Cargo source notice binding mismatch')
        for notice,entry in inventory.get('declarationNotices',{}).items():
            name='licenses/deno-cargo-declarations/'+notice
            if files.get(name)!=entry['sha256'] or digest(runtime/name)!=entry['sha256']:
                raise ValueError('Cargo declaration notice origin mismatch')
            add('cargo-declaration:'+entry['name'],entry['scope'],entry['version'],
                entry.get('declaredLicence') or 'see original upstream licence file',[name],[name],verified=True)
        for item in inventory['packages']:
            for notice,entry in item['notices'].items():
                name='licenses/deno-cargo-source-superset/'+notice.removeprefix('notices/')
                if files.get(name)!=entry['sha256']: raise ValueError('Cargo notice and runtime file disagree')
                add('cargo-source-notice:'+item['name'],'exact source-lock superset notice; binary inclusion unproven',item['version'],
                    item.get('declaredLicence') or 'see exact source notice',[name],[name],verified=True)
    repository=metadata.get('repositoryNoticeEvidence')
    if repository:
        inventory=json.loads((runtime/'licenses/repository-notice-inventory.json').read_text())
        if inventory['inputInventorySha256']!=repository['inputInventorySha256']: raise ValueError('Repository notice selection binding mismatch')
        notices={name:entry for row in inventory['packages'] for name,entry in row.get('notices',{}).items()}
        for notice,entry in notices.items():
            name='licenses/deno-repository-source-notices/'+notice
            if files.get(name)!=entry['sha256']: raise ValueError('Repository notice and runtime bytes disagree')
            add('repository-source-notice:'+notice,'exact source/ancestor notice; applicability unproven',entry['commit'],
                'see original source terms; no automatic inheritance',[name],[name],verified=True)
    if '_internal/base_library.zip' in files:
        path = runtime/'_internal/base_library.zip'
        if digest(path) != files['_internal/base_library.zip']: raise ValueError('Changed standard-library container')
        with zipfile.ZipFile(path) as archive:
            import hashlib
            report['standardLibraryContainer'] = {'sha256':digest(path),'members':{name:hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()},
                'scope':'Compiled CPython standard library generated by pinned PyInstaller; component licences retained in Python notice'}
        add('container:python-stdlib','compiled-standard-library-container',metadata['python'],'PSF-2.0 and CPython component notices',['_internal/base_library.zip'],['licenses/interpreter/Python-LICENSE.txt'],verified=True)
    certifi = next((item for item in metadata.get('dependencies',[]) if item['name'].lower()=='certifi'),None)
    names = [name for name in files if name.startswith('_internal/certifi/')]
    if certifi and names:
        notices = [name for name in files if name.startswith('licenses/certifi/')]
        add('data:certifi','shipped-source-form-certificate-data',certifi['version'],'MPL-2.0',names,notices,'retain-notice-and-source-form',verified=True)
    # Older packages copied build-only notices. Attribute their notice bytes,
    # not a claim the corresponding build-tool code was embedded in the host.
    for dependency in metadata.get('buildEnvironmentDependencies',[]):
        if dependency['name'] in {item['name'] for item in metadata.get('dependencies',[])}: continue
        names = [name for name in files if name.startswith('licenses/'+dependency['name']+'/') and name not in metadata.get('noticeOrigins',{})]
        if names: add('build-notice:'+dependency['name'],'notice-only; build code not thereby shipped',dependency['version'],'see retained original notice',names,names)
    return rows


def completeness(report):
    """Derive closure from identified obligations; unknown licences remain blockers."""
    issues = []
    for name in report.get('unassignedRuntimeFiles',[]): issues.append({'component':name,'reason':'file-attribution-missing'})
    audio = report.get('sourceBuiltAudio')
    if not audio or not audio.get('sourceSignatureVerified') or not any(name.endswith('ffmpeg-9.0.2.tar.xz') for name in audio.get('correspondingSourcePaths',[])) or not any(name.endswith('opus-1.6.1.tar.gz') for name in audio.get('correspondingSourcePaths',[])):
        issues.append({'component':'FFmpeg/Opus','reason':'matching-source-or-recipe-missing'})
    # Native/tool payload matching is not a full bundled-code dependency manifest.
    downloader=report.get('sourceBuiltDownloader')
    if downloader:
        if downloader.get('passed') is not True or not downloader.get('sourceFiles') or not downloader.get('nativeLibraries'):
            issues.append({'component':'yt-dlp','reason':'verified source build, corresponding sources or native inventory missing'})
        curl=report.get('curlSourceEvidence')
        if not curl or curl.get('downloaderSha256')!=downloader.get('executableSha256') or curl.get('originVerified') is not True or curl.get('recipeInputsVerified') is not True:
            issues.append({'component':'yt-dlp/curl','reason':'exact embedded DLL origin and recipe source inputs missing'})
        issues.append({'component':'yt-dlp native dependencies','reason':'supported-runtime rebuild, Python sdists and byte-matched curl recipe supplied; remaining interpreter/extension native notice and transitive-source closure requires review'})
    else:
        issues.append({'component':'yt-dlp','reason':'embedded GPL/LGPL/native dependency versions and corresponding sources not fully established'})
    v8=report.get('v8NoticeEvidence')
    if not v8 or v8.get('coreNoticesRestored') is not True:
        issues.append({'component':'Deno/V8 core','reason':'original V8 and binding core notices omitted by source crate; matching source notices required'})
    for component,reason in [
        ('Deno/V8','core notices restored; remaining Rust and V8 transitive/submodule notice coverage is not established by Cargo.lock alone' if v8 else 'binary third-party notice closure not established by source Cargo.lock'),
        ('CPython native dependencies','original component notices supplied; binary/source version linkage and Microsoft runtime redistribution eligibility remain review gates' if report.get('interpreterComponentEvidence') else 'individual native-library terms/version evidence and Microsoft runtime redistribution terms require review')]:
        issues.append({'component':component,'reason':reason})
    for row in report['rows']:
        if row['id'].startswith('javascript:') and row.get('noticeEvidenceComplete') is not True:
            issues.append({'component':row['id'],'reason':'emitted-package notice evidence missing'})
    return {'fileAttributionComplete':not report.get('unassignedRuntimeFiles'),
        'correspondingSourceComplete':not issues,'licenceEvidenceComplete':not issues,
        'unresolvedEvidence':issues,'remainingObligations':[item['component']+': '+item['reason'] for item in issues],
        'redistributionApproved':False,'interpretation':'Automatic evidence completeness is separate from explicit publisher approval. Permissive notice-only licences do not require full corresponding source.'}
