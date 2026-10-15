"""Collect source/notice evidence, explicitly without legal clearance."""
import json
from pathlib import Path
import shutil
import tomllib
import zipfile
from release_inputs import digest, inspect_ejs
from notice_names import is_notice_name


def collect(cache, output, lock, evidence_cache=None, source_audio=False, downloader_build=None):
    output.mkdir(parents=True, exist_ok=False)
    sources = []
    for item in lock['files']:
        if item.get('role') != 'licence-source-evidence':
            continue
        if source_audio and item['file'].startswith('FFmpeg-5d4d3bdc61-'): continue
        source = cache / item['file']
        shutil.copy2(source, output / source.name)
        sources.append(item)
    from PyInstaller.archive.readers import CArchiveReader
    executable=downloader_build/'bin/yt-dlp.exe' if downloader_build else cache/'yt-dlp.exe'
    archive = CArchiveReader(str(executable))
    metadata = {}
    exact_notices = {}
    for name in archive.toc:
        normalized = name.replace('\\','/')
        if normalized.endswith('/METADATA') and '.dist-info/' in normalized:
            text = archive.extract(name).decode('utf-8', errors='replace')
            fields = dict(line.split(': ',1) for line in text.splitlines() if line.startswith(('Name: ', 'Version: ', 'License: ')))
            metadata[normalized] = fields
        if any(is_notice_name(part) for part in normalized.split('/')):
            content = archive.extract(name)
            if not isinstance(content, bytes): continue
            target = output / 'yt-dlp-exact-notices' / normalized
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            exact_notices[normalized] = digest(target)
    deno_packages = []
    with zipfile.ZipFile(cache/'Deno-2.9.7-source.zip') as archive:
        name = next(n for n in archive.namelist() if n.count('/') == 1 and n.endswith('Cargo.lock'))
        cargo = tomllib.loads(archive.read(name).decode())
        deno_packages = [{'name':p['name'],'version':p['version'],'checksum':p.get('checksum'),'scope':'Deno source Cargo.lock, not proof every crate is shipped'} for p in cargo['package']]
        (output/'Deno-Cargo.lock').write_bytes(archive.read(name))
        for name in archive.namelist():
            if name.endswith('/') or '/tests/' in name: continue
            if is_notice_name(Path(name).name):
                target = output/'deno-source-notices'/name.split('/',1)[1]
                target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(archive.read(name))
    report = {'sources':sources,'ytDlpEmbeddedMetadata':metadata,'ytDlpEmbeddedNoticeHashes':exact_notices,
        'ejs':inspect_ejs(executable),'denoSourceDependencies':deno_packages,
        'pythonArchiveComparison':lock.get('pythonArchiveComparison'),
        'redistributionApproved':False,'correspondingSourceComplete':False,
        'remaining':'FFmpeg external enabled libraries/build recipes; yt-dlp exact bundled dependency sources; Deno binary third-party closure and interpreter native DLL licence closure remain review gates. Official interpreter payload matching is separately recorded.'}
    from dependency_ledger import supplemental
    extra_lock=json.loads((Path(__file__).parent/'evidence-windows.lock.json').read_text())
    report['supplemental']=supplemental(evidence_cache or Path(__file__).resolve().parents[1]/'artifacts/redistribution-evidence-v2',output/'supplemental',extra_lock,source_audio)
    if downloader_build:
        from build_downloader import validate_build
        report['sourceBuiltDownloader']=validate_build(downloader_build)
        for name in ('notices','corresponding-source'):
            shutil.copytree(downloader_build/name,output/'downloader'/name)
        shutil.copy2(downloader_build/'downloader-build.json',output/'downloader/downloader-build.json')
    (output/'licence-evidence.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report
