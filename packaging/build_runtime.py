"""Build a fresh one-folder prototype; no installation, registration or publication."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from runtime_notices import collect_interpreter_notices
from release_inputs import inspect_ejs, shipped_python, source_inventory
from build_isolation import environment, native_inputs
from source_export import source_identity
from notice_names import is_notice_name

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def validated_audio_build(folder, tools):
    audio = json.loads((folder/'audio-build.json').read_text())
    evidence_file = folder/'audio-conformance.json' if (folder/'audio-conformance.json').is_file() else folder/'audio-compatibility.json'
    compatibility = json.loads(evidence_file.read_text())
    if evidence_file.name == 'audio-conformance.json':
        from verify_audio_conformance import validate_recipe
        validate_recipe(folder)
        if compatibility.get('policySha256') != sha256(ROOT/'packaging/audio-policy.json') or compatibility.get('fixtureSha256') != sha256(ROOT/'packaging/fixtures/synthetic-audio.json'):
            raise ValueError('Audio conformance policy/fixture mismatch')
    audit_file = folder/'corresponding-source/toolchain-audit.json'
    audit = json.loads(audit_file.read_text())
    if audit.get('passed') is not True or not audit.get('files') or audio.get('toolchainAuditSha256') != sha256(audit_file):
        raise ValueError('Matching pre-build toolchain audit required')
    if audio.get('inputLockSha256') != sha256(ROOT/'packaging/audio-inputs.lock.json') or audio.get('toolchainLockSha256') != sha256(ROOT/'packaging/audio-toolchain.lock.json'):
        raise ValueError('Audio build does not match the current source/toolchain locks')
    if audio.get('version') != '9.0.2' or audio.get('sourceSignatureVerified') is not True or compatibility.get('passed') is not True or compatibility.get('audioBuildSha256') != sha256(folder/'audio-build.json') or compatibility.get('candidateFileHashes') != audio.get('files'):
        raise ValueError('Verified 9.0.2 audio compatibility evidence required')
    for name, checksum in audio['files'].items():
        if Path(name).name != name or Path(name).suffix not in ('.exe','.dll') or sha256(folder/'install/bin'/name) != checksum:
            raise ValueError('Changed/unsafe audio-build payload')
    for name in ('ffmpeg','ffprobe'):
        if sha256(Path(tools[name])) != audio['files'][name+'.exe']:
            raise ValueError('Resolved audio tool differs from the verified build')
    return audio, compatibility


def build(output, tool_lock=None, audio_build=None, transport_policy='preview', public_config=None, downloader_build=None, v8_notices=None, interpreter_notices=None, cargo_notices=None, repository_notices=None):
    if transport_policy not in ('preview', 'https-remote'):
        raise ValueError('Invalid packaged transport policy')
    public = None
    if public_config:
        sys.path.insert(0, str(ROOT / 'native'))
        from cueflora_setup.public_release import validate_public
        public = validate_public(json.loads(public_config.read_text(encoding='utf-8')),require_binding=False)
        transport_policy = 'https-remote'
    output = output.resolve()
    if output.exists():
        raise ValueError('Build output already exists; choose a fresh directory')
    output.mkdir(parents=True)
    sys.path.insert(0, str(ROOT / 'native'))
    from cueflora_host.download import _resolve_yt_dlp_executable
    from cueflora_host.whisper import _resolve_binary
    from cueflora_host.runtime_tools import resolve_deno
    tools = {'yt-dlp': _resolve_yt_dlp_executable(), 'ffmpeg': _resolve_binary('ffmpeg'), 'ffprobe': _resolve_binary('ffprobe'), 'deno': resolve_deno()}
    if not all(tools.values()):
        raise RuntimeError('All four tools are required to build a portable runtime')
    audio = None
    compatibility = None
    if audio_build:
        audio, compatibility = validated_audio_build(audio_build, tools)
    downloader=None
    if downloader_build:
        from build_downloader import validate_build
        downloader=validate_build(downloader_build)
        if sha256(Path(tools['yt-dlp']))!=downloader['executableSha256']:
            raise ValueError('Resolved downloader differs from verified supported-runtime build')
    v8_evidence=None
    if v8_notices:
        from collect_v8_notices import validate_evidence
        v8_evidence=validate_evidence(v8_notices,Path(tools['deno']))
    interpreter_evidence=None
    if interpreter_notices:
        from interpreter_component_notices import validate_evidence
        interpreter_evidence=validate_evidence(interpreter_notices)
    cargo_evidence=None
    if cargo_notices:
        from cargo_notice_evidence import validate_evidence
        cargo_evidence=validate_evidence(cargo_notices)
    repository_evidence=None
    if repository_notices:
        from repository_notice_evidence import validate_evidence
        repository_evidence=validate_evidence(repository_notices)
    ejs = inspect_ejs(tools['yt-dlp'])
    if tool_lock:
        locked = json.loads(tool_lock.read_text(encoding='utf-8'))
        expected = {item['name']: item['sha256'] for item in locked['tools']}
        if set(expected) != set(tools) or any(sha256(Path(path)) != expected[name] for name, path in tools.items()):
            raise RuntimeError('Tool inputs do not match the pinned inventory')
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--onedir', '--noupx',
                    '--name', 'cueflora-host', '--paths', str(ROOT / 'native'),
                    '--add-data', str(ROOT / 'native/cueflora_host/whisper.py') + ':cueflora_host',
                    '--distpath', str(output / 'dist'), '--workpath', str(output / 'work'),
                    '--specpath', str(output), str(ROOT / 'packaging/host_entry.py')], check=True, env=environment())
    native_inventory = native_inputs(output / 'work/cueflora-host/Analysis-00.toc')
    bundle = output / 'dist/cueflora-host'
    (bundle / 'tools').mkdir()
    if audio:
        for name in audio['files']:
            if name.endswith('.dll'): shutil.copy2(audio_build/'install/bin'/name,bundle/'tools'/name)
    inventory = []
    licenses = bundle / 'licenses'
    licenses.mkdir()
    observed = shipped_python(output / 'work/cueflora-host/Analysis-00.toc')
    notice_dependencies = {item['name'].lower().replace('_','-') for item in observed} | {'pyinstaller'}
    notice_origins = {}
    # Preserve available dependency notices. External tool license/source review
    # is intentionally separate and remains an explicit release gate.
    for distribution in importlib.metadata.distributions():
        component = distribution.metadata['Name']
        if component.lower().replace('_','-') not in notice_dependencies: continue
        for entry in distribution.files or []:
            if is_notice_name(entry.name):
                source = Path(distribution.locate_file(entry))
                if source.is_file():
                    folder = licenses / distribution.metadata['Name']
                    folder.mkdir(exist_ok=True)
                    target = folder / (hashlib.sha256(str(entry).encode()).hexdigest()[:8] + '-' + entry.name)
                    shutil.copy2(source, target)
                    notice_origins[target.relative_to(bundle).as_posix()] = {
                        'component':component,'version':distribution.version,'distributionEntry':str(entry).replace('\\','/'),
                        'sha256':sha256(target),'licence':distribution.metadata.get('License-Expression') or distribution.metadata.get('License') or 'see exact notice',
                        'scope':'shipped bootloader notice' if component.lower() == 'pyinstaller' else 'analysis-observed runtime dependency notice'}
    (licenses/'notice-origins.json').write_text(json.dumps(notice_origins,indent=2)+'\n',encoding='utf-8')
    for name, source in tools.items():
        target = bundle / 'tools' / (name + ('.exe' if platform.system() == 'Windows' else ''))
        shutil.copy2(source, target)
        if name == 'yt-dlp':
            from PyInstaller.archive.readers import CArchiveReader
            archive = CArchiveReader(str(target))
            for entry in archive.toc:
                normalized = entry.replace('\\', '/')
                if 'license' in normalized.lower() or normalized == 'THIRD_PARTY_LICENSES.txt':
                    data = archive.extract(entry)
                    if isinstance(data, bytes):
                        notice = licenses / 'yt-dlp-exact' / normalized
                        notice.parent.mkdir(parents=True, exist_ok=True)
                        notice.write_bytes(data)
        version = subprocess.check_output([str(target), '--version' if name in ('yt-dlp', 'deno') else '-version'], timeout=15, text=True).splitlines()[0]
        evidence = {}
        for flag in (['--version'] if name in ('yt-dlp', 'deno') else ['-version', '-buildconf', '-L']):
            result = subprocess.run([str(target), flag], timeout=15, check=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            evidence[flag] = result.stdout
        evidence_path = licenses / (name + '-binary-evidence.json')
        evidence_path.write_text(json.dumps({'sha256': sha256(target), 'outputs': evidence,
            'redistributionApproved': False}, indent=2) + '\n', encoding='utf-8')
        inventory.append({'name': name, 'versionOutput': version, 'sha256': sha256(target),
                          'binaryEvidence': evidence_path.relative_to(bundle).as_posix(),
                          'licenseReview': 'required-before-distribution'})
    collect_interpreter_notices(bundle)
    notice_source = ROOT / 'packaging/notices'
    if notice_source.exists():
        shutil.copytree(notice_source, licenses / 'upstream')
    if audio:
        shutil.copytree(audio_build/'notices',licenses/'source-built-audio')
        shutil.copytree(audio_build/'corresponding-source',bundle/'corresponding-source/audio')
        shutil.copy2(audio_build/'audio-build.json',licenses/'audio-build.json')
        evidence_file = audio_build/'audio-conformance.json' if (audio_build/'audio-conformance.json').is_file() else audio_build/'audio-compatibility.json'
        shutil.copy2(evidence_file,licenses/evidence_file.name)
    if downloader:
        shutil.copytree(downloader_build/'notices',licenses/'source-built-downloader')
        shutil.copytree(downloader_build/'corresponding-source',bundle/'corresponding-source/downloader')
        shutil.copy2(downloader_build/'downloader-build.json',licenses/'downloader-build.json')
    if v8_evidence:
        shutil.copytree(v8_notices/'notices',licenses/'deno-v8-source-notices')
        shutil.copy2(v8_notices/'v8-notice-evidence.json',licenses/'v8-notice-evidence.json')
    if interpreter_evidence:
        shutil.copytree(interpreter_notices/'notices',licenses/'interpreter-components')
        shutil.copy2(interpreter_notices/'interpreter-component-notices.json',licenses/'interpreter-component-notices.json')
    if cargo_evidence:
        shutil.copytree(cargo_notices/'notices',licenses/'deno-cargo-source-superset')
        shutil.copytree(cargo_notices/'declarations',licenses/'deno-cargo-declarations')
        shutil.copy2(cargo_notices/'cargo-notice-inventory.json',licenses/'cargo-notice-inventory.json')
    if repository_evidence:
        shutil.copytree(repository_notices/'notices',licenses/'deno-repository-source-notices')
        shutil.copy2(repository_notices/'repository-notice-inventory.json',licenses/'repository-notice-inventory.json')
    source_files = source_inventory()
    source_hash = source_identity(source_files)
    if public and public.get('sourceInventorySha256') not in (None, source_hash):
        raise ValueError('Public approval does not match the current source snapshot')
    metadata = {'schema': 1, 'product': 'cueflora', 'prototype': True, 'platform': platform.system(), 'architecture': platform.machine(),
                'python': platform.python_version(), 'packager': importlib.metadata.version('pyinstaller'),
                'hostVersion': json.loads((ROOT / 'package.json').read_text())['version'],
                'nativeInputIsolation':{'inheritedPathUsed':False,'inputs':native_inventory},
                'tools': inventory, 'ejs': ejs, 'sourceFiles': source_files, 'sourceInventorySha256':source_hash,
                'transportPolicy':transport_policy, 'publicEvidence':public.get('evidence') if public else None,
                'audioBuild':audio,'audioCompatibility':compatibility,'downloaderBuild':downloader,'v8NoticeEvidence':v8_evidence,
                'interpreterComponentEvidence':interpreter_evidence,
                'cargoNoticeEvidence':{'cargoLockSha256':cargo_evidence['cargoLockSha256'],'registryPackageCount':cargo_evidence['registryPackageCount'],
                    'missingPackageRootNotices':cargo_evidence['missingPackageRootNotices'],'redistributionApproved':False,'binaryDependencyClosureComplete':False} if cargo_evidence else None,
                'repositoryNoticeEvidence':{'inputInventorySha256':repository_evidence['inputInventorySha256'],'recoveredPackageCount':repository_evidence['recoveredPackageCount'],
                    'unresolvedPackages':repository_evidence['unresolvedPackages'],'licenceApplicabilityProven':False,'binaryDependencyClosureComplete':False} if repository_evidence else None,
                'inputLockSha256': sha256(ROOT / 'packaging/inputs-windows.lock.json'),
                'dependencyScope': 'Analysis-observed third-party Python modules; standard library, native DLLs, tools and bootloader require separate inventory review.',
                'noticeOrigins':notice_origins,
                'dependencies': observed, 'buildEnvironmentDependencies': sorted(
                    ({'name': d.metadata['Name'], 'version': d.version} for d in importlib.metadata.distributions()),
                    key=lambda item: item['name'].lower()),
                'files': {str(p.relative_to(bundle)).replace('\\', '/'): sha256(p)
                          for p in sorted(bundle.rglob('*')) if p.is_file()}}
    (bundle / 'runtime-manifest.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    print(bundle)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tool-lock', type=Path, help='Previously reviewed runtime inventory; tool SHA-256 values must match')
    parser.add_argument('--downloader-build',type=Path,help='Verified same-version downloader on pinned supported Python')
    parser.add_argument('--v8-notices',type=Path,help='Hash-bound Deno/V8 core source notice evidence')
    parser.add_argument('--interpreter-notices',type=Path,help='Original notices from the pinned Windows interpreter build source')
    parser.add_argument('--cargo-notices',type=Path,help='Exact Deno source-Cargo notice superset, not binary shipment evidence')
    parser.add_argument('--repository-notices',type=Path,help='Fixed-commit missing-notice follow-up; applicability stays unapproved')
    parser.add_argument('--audio-build', type=Path, help='Verified shared FFmpeg/ffprobe 9.0.2 build directory')
    parser.add_argument('--transport-policy', choices=['preview','https-remote'], default='preview')
    parser.add_argument('--public-config', type=Path, help='Explicit authorized public release configuration')
    args = parser.parse_args()
    build(args.output, args.tool_lock, args.audio_build, args.transport_policy, args.public_config, args.downloader_build, args.v8_notices, args.interpreter_notices, args.cargo_notices, args.repository_notices)
