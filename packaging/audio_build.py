"""Pinned, portable Windows audio-tool build. No installer/registry/AI operations."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
INPUT_LOCK = ROOT / 'packaging/audio-inputs.lock.json'
TOOLCHAIN_LOCK = ROOT / 'packaging/audio-toolchain.lock.json'
CONFIGURE = [
    '--disable-autodetect', '--disable-gpl', '--disable-nonfree',
    '--disable-static', '--enable-shared', '--disable-doc', '--disable-debug',
    '--disable-ffplay', '--disable-network', '--disable-avdevice',
    '--disable-everything', '--enable-ffmpeg', '--enable-ffprobe',
    '--enable-libopus', '--enable-encoder=libopus,pcm_s16le,pcm_f32le',
    '--enable-decoder=aac,aac_fixed,mp3,mp3float,opus,vorbis,flac,alac,pcm_s16le,pcm_s24le,pcm_s32le,pcm_f32le,pcm_f64le,pcm_s16be,pcm_u8',
    '--enable-demuxer=mov,matroska,ogg,mp3,aac,flac,wav',
    '--enable-muxer=ogg,opus,wav,pcm_f32le,pcm_s16le,null',
    '--enable-parser=aac,aac_latm,mpegaudio,opus,vorbis,flac',
    '--enable-filter=aresample,aformat,anull,atrim,asetpts,pan',
    '--enable-protocol=file,pipe', '--enable-swresample',
    '--extra-cflags=-O2', '--extra-ldflags=-static-libgcc',
]


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): value.update(block)
    return value.hexdigest()


def validate_inputs(lock):
    if not isinstance(lock, dict) or lock.get('schema') != 1 or not isinstance(lock.get('files'), list) or not lock['files']:
        raise ValueError('Invalid audio input lock')
    seen = set()
    for item in lock['files']:
        if not isinstance(item, dict): raise ValueError('Invalid audio input')
        name = item.get('file', '')
        if not isinstance(name, str) or not re.fullmatch(r'[\w.~+-]+', name) or name in ('.', '..') or name.casefold() in seen:
            raise ValueError('Unsafe audio input name')
        if not re.fullmatch('[0-9a-f]{64}', str(item.get('sha256', ''))): raise ValueError('Invalid audio input hash')
        from urllib.parse import urlsplit
        address = urlsplit(item.get('url', ''))
        if address.scheme != 'https' or address.hostname not in {'ffmpeg.org', 'downloads.xiph.org', 'github.com', 'repo.msys2.org', 'codeload.github.com', 'raw.githubusercontent.com', 'files.pythonhosted.org', 'static.crates.io'} or address.username or address.password or address.query or address.fragment or address.port not in (None, 443):
            raise ValueError('Unapproved audio input URL')
        seen.add(name.casefold())
    return lock


def obtain(lock, cache, online=False):
    validate_inputs(lock)
    cache.mkdir(parents=True, exist_ok=True)
    for item in lock['files']:
        target = cache / item['file']
        if target.is_symlink(): raise ValueError('Linked audio cache input')
        if not target.exists():
            if not online: raise ValueError('Missing locked audio input: ' + item['file'])
            partial = target.with_suffix(target.suffix + '.partial')
            with urllib.request.urlopen(item['url'], timeout=60) as response, partial.open('xb') as stream:
                shutil.copyfileobj(response, stream)
            if digest(partial) != item['sha256']: raise ValueError('Downloaded audio input hash mismatch')
            partial.rename(target)
        if not target.is_file() or digest(target) != item['sha256']:
            raise ValueError('Locked audio input hash mismatch: ' + item['file'])


def extract_source(archive, destination):
    destination.mkdir(parents=True, exist_ok=False)
    with tarfile.open(archive) as source:
        for member in source.getmembers():
            path = PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or '\\' in member.name or ':' in member.name or not (member.isfile() or member.isdir()):
                raise ValueError('Unsafe source archive member')
        source.extractall(destination, filter='data')


def posix(path):
    path = Path(path).resolve()
    if not path.drive or len(path.drive) != 2: raise ValueError('Local Windows drive required')
    return '/' + path.drive[0].lower() + path.as_posix()[2:]


def shell(toolchain, command, log, timeout=1800):
    environment = {key.upper(): value for key, value in os.environ.items()}
    for name in ('PYTHONPATH', 'PYTHONHOME', 'LD_LIBRARY_PATH', 'DYLD_LIBRARY_PATH', 'BASH_ENV', 'ENV', 'CDPATH', 'CC', 'CXX', 'AR', 'AS', 'LD', 'NM', 'RANLIB', 'STRIP', 'CFLAGS', 'CPPFLAGS', 'CXXFLAGS', 'LDFLAGS', 'MAKEFLAGS', 'PKG_CONFIG', 'PKG_CONFIG_PATH'):
        environment.pop(name, None)
    environment.update(MSYSTEM='UCRT64', MSYS2_PATH_TYPE='strict', CHERE_INVOKING='1')
    environment['PATH'] = os.pathsep.join(map(str, [toolchain/'ucrt64/bin', toolchain/'usr/bin', Path(environment['SYSTEMROOT'])/'System32']))
    with log.open('wb') as output:
        result = subprocess.run([str(toolchain/'usr/bin/bash.exe'), '--noprofile', '--norc', '-c',
            'set -eu; export PATH=/ucrt64/bin:/usr/bin; ' + command], env=environment, stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
    if result.returncode: raise RuntimeError('Audio build step failed; see ' + log.name)


def verify_toolchain(cache, toolchain, output):
    """Compare installed compiler/shell payload to the exact locked archives."""
    if output.exists(): raise ValueError('Fresh toolchain audit directory required')
    primary = json.loads(INPUT_LOCK.read_text()); packages = json.loads(TOOLCHAIN_LOCK.read_text())
    obtain(primary,cache); obtain(packages,cache)
    output.mkdir(parents=True)
    tar = Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32/tar.exe'
    subprocess.run([str(tar),'-xf',str(cache/packages['baseArchive']),'-C',str(output)],check=True)
    expected = output/'msys64'
    for item in packages['files']:
        if not item['file'].endswith('.pkg.tar.zst'): continue
        names = subprocess.check_output([str(tar),'-tf',str(cache/item['file'])],text=True).splitlines()
        if any(PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts or '\\' in name or ':' in name for name in names):
            raise ValueError('Unsafe compiler package member')
        subprocess.run([str(tar),'-xf',str(cache/item['file']),'-C',str(expected)],check=True)
    hashes = {}
    for directory in ('usr','ucrt64'):
        for path in (expected/directory).rglob('*'):
            if not path.is_file(): continue
            relative = path.relative_to(expected)
            if relative.as_posix() == 'usr/share/info/dir': continue  # Generated documentation index; not compiler input.
            actual = toolchain/relative
            checksum = digest(path)
            if not actual.is_file() or actual.is_symlink() or digest(actual)!=checksum:
                raise ValueError('Installed compiler payload differs from lock: '+relative.as_posix())
            hashes[relative.as_posix()] = checksum
    for directory in ('usr','ucrt64'):
        for path in (toolchain/directory).rglob('*'):
            if path.suffix.lower() in ('.exe','.dll','.a','.h','.pc') and path.is_file() and path.relative_to(toolchain).as_posix() not in hashes:
                raise ValueError('Unlisted installed compiler input')
    report = {'schema':1,'passed':True,'files':hashes,'generatedNonBuildMetadata':['usr/share/info/dir'],
        'inputLockSha256':digest(INPUT_LOCK),'toolchainLockSha256':digest(TOOLCHAIN_LOCK)}
    (output/'toolchain-audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def bootstrap(cache, output):
    """Offline replay of exact archives/packages; all changes stay in output."""
    if output.exists(): raise ValueError('Fresh portable-toolchain output required')
    lock = json.loads(INPUT_LOCK.read_text())
    package_lock = json.loads(TOOLCHAIN_LOCK.read_text())
    obtain(lock, cache)
    obtain(package_lock, cache)
    output.mkdir(parents=True)
    archive = cache / package_lock['baseArchive']
    with tarfile.open(archive) as source:
        for member in source:
            path = PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or '\\' in member.name or ':' in member.name:
                raise ValueError('Unsafe portable-toolchain member')
    subprocess.run(['tar', '-xf', str(archive), '-C', str(output)], check=True)
    root = output/'msys64'
    shell(root, 'bash /usr/bin/pacman-key --init && bash /usr/bin/pacman-key --populate msys2', output/'keyring.log')
    packages = [shlex.quote(posix(cache/item['file'])) for item in package_lock['files'] if item['file'].endswith('.pkg.tar.zst')]
    shell(root, '/usr/bin/pacman -U --noconfirm ' + ' '.join(packages), output/'packages.log')
    return root


def verify_signature(toolchain, cache, output, fingerprint):
    home = output/'signature-keyring'
    home.mkdir()
    # Public-key conversion/verification needs neither a secret-key agent nor
    # a trust database. gpgv also avoids agent socket path limits in deep roots.
    keyring = home/'release-key.gpg'
    shell(toolchain, 'gpg --no-options --batch --dearmor --output ' + shlex.quote(posix(keyring)) + ' ' + shlex.quote(posix(cache/'ffmpeg-devel.asc')), output/'signature-import.log')
    shell(toolchain, 'gpgv --homedir ' + shlex.quote(posix(home)) + ' --keyring ' + shlex.quote(posix(keyring)) + ' --status-fd 1 ' + shlex.quote(posix(cache/'ffmpeg-9.0.2.tar.xz.asc')) + ' ' + shlex.quote(posix(cache/'ffmpeg-9.0.2.tar.xz')), output/'signature-verify.log')
    result = (output/'signature-verify.log').read_text(errors='replace')
    if '[GNUPG:] VALIDSIG ' + fingerprint + ' ' not in result: raise ValueError('Unexpected FFmpeg signing fingerprint')


def build(cache, toolchain, output, jobs=4):
    if os.name != 'nt': raise ValueError('Windows x64 build only')
    if output.exists(): raise ValueError('Fresh audio-build output required')
    lock = json.loads(INPUT_LOCK.read_text())
    obtain(lock, cache)
    obtain(json.loads(TOOLCHAIN_LOCK.read_text()), cache)
    if not (toolchain/'ucrt64/bin/gcc.exe').is_file(): raise ValueError('Portable compiler missing')
    output.mkdir(parents=True)
    toolchain_audit = verify_toolchain(cache,toolchain,output/'toolchain-audit')
    verify_signature(toolchain, cache, output, lock['signingFingerprint'])
    extract_source(cache/'opus-1.6.1.tar.gz', output/'opus-source')
    extract_source(cache/'ffmpeg-9.0.2.tar.xz', output/'ffmpeg-source')
    prefix = output/'install'
    opus = output/'opus-source/opus-1.6.1'
    ffmpeg = output/'ffmpeg-source/ffmpeg-9.0.2'
    configure_opus = ['./configure', '--host=x86_64-w64-mingw32', '--prefix='+posix(prefix), '--enable-shared', '--disable-static', '--disable-doc', '--disable-extra-programs', 'LDFLAGS=-static-libgcc']
    shell(toolchain, 'cd '+shlex.quote(posix(opus))+'; '+shlex.join(configure_opus)+'; make -j'+str(jobs)+'; make install', output/'opus-build.log')
    configure_ffmpeg = ['./configure', '--prefix='+posix(prefix), '--extra-cflags=-I'+posix(prefix/'include'), '--extra-ldflags=-L'+posix(prefix/'lib')+' -static-libgcc', *CONFIGURE]
    shell(toolchain, 'export PKG_CONFIG_PATH='+shlex.quote(posix(prefix/'lib/pkgconfig'))+'; cd '+shlex.quote(posix(ffmpeg))+'; '+shlex.join(configure_ffmpeg)+'; make -j'+str(jobs)+'; make install', output/'ffmpeg-build.log')
    bin_dir = prefix/'bin'
    # Resolve transitive imports from only the verified build outputs/toolchain.
    from pefile import PE
    queue = list(bin_dir.glob('*.exe')) + list(bin_dir.glob('*.dll'))
    seen = set()
    system = Path(os.environ.get('SystemRoot', os.environ.get('SYSTEMROOT', r'C:\Windows')))/'System32'
    dependencies = []
    while queue:
        binary = queue.pop()
        if binary.name.casefold() in seen: continue
        seen.add(binary.name.casefold())
        image = PE(str(binary))
        for entry in getattr(image, 'DIRECTORY_ENTRY_IMPORT', []):
            name = entry.dll.decode('ascii')
            if (bin_dir/name).is_file(): continue
            candidate = toolchain/'ucrt64/bin'/name
            if candidate.is_file():
                shutil.copy2(candidate, bin_dir/name)
                dependencies.append({'file':name, 'sha256':digest(candidate), 'origin':'hash-locked portable compiler package'})
                queue.append(bin_dir/name)
            elif not (system/name).is_file() and not name.lower().startswith(('api-ms-win-', 'ext-ms-win-')):
                raise ValueError('Unresolved audio binary dependency: '+name)
        image.close()
    source_dir = output/'corresponding-source'
    source_dir.mkdir()
    for item in lock['files']:
        if item['role'] in ('source','signature','public-key'): shutil.copy2(cache/item['file'], source_dir/item['file'])
    shutil.copy2(INPUT_LOCK, source_dir/INPUT_LOCK.name)
    shutil.copy2(TOOLCHAIN_LOCK, source_dir/TOOLCHAIN_LOCK.name)
    shutil.copy2(Path(__file__), source_dir/'audio_build.py')
    shutil.copy2(output/'toolchain-audit/toolchain-audit.json',source_dir/'toolchain-audit.json')
    notice_dir = output/'notices'; notice_dir.mkdir()
    notice_origins = {}
    for family,directory in [('ffmpeg',ffmpeg),('opus',opus),('compiler',toolchain/'ucrt64/share/licenses')]:
        for path in directory.rglob('*'):
            if path.is_file() and re.search(r'^(COPYING|LICENSE|NOTICE|PATENTS|AUTHORS)', path.name, re.I):
                name = family+'-'+hashlib.sha256(str(path.relative_to(directory)).encode()).hexdigest()[:12]+'-'+path.name
                shutil.copy2(path, notice_dir/name)
                notice_origins[name] = {'family':family,'originalPath':path.relative_to(directory).as_posix(),
                    'sha256':digest(notice_dir/name),'version':lock['ffmpegVersion'] if family=='ffmpeg' else '1.6.1' if family=='opus' else 'see compiler lock',
                    'scope':'compiler package notices may include build-only code; no assertion all packages are shipped'}
    (notice_dir/'notice-origins.json').write_text(json.dumps(notice_origins,indent=2)+'\n',encoding='utf-8')
    files = {path.name:digest(path) for path in sorted(bin_dir.iterdir()) if path.is_file() and path.suffix.lower() in ('.exe','.dll')}
    report = {'schema':1,'version':lock['ffmpegVersion'],'fingerprint':lock['signingFingerprint'],
        'sourceSignatureVerified':True,'inputLockSha256':digest(INPUT_LOCK),'toolchainLockSha256':digest(TOOLCHAIN_LOCK),
        'toolchainAuditSha256':digest(output/'toolchain-audit/toolchain-audit.json'),
        'configureOpus':configure_opus,'configureFFmpeg':configure_ffmpeg,'files':files,'compilerRuntimeDependencies':dependencies,
        'redistributionApproved':False,'compatibilityAccepted':False}
    (output/'audio-build.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'bin':str(bin_dir),'files':len(files),'report':str(output/'audio-build.json')}),flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--toolchain', type=Path)
    parser.add_argument('--online', action='store_true')
    parser.add_argument('--bootstrap', action='store_true')
    parser.add_argument('--jobs', type=int, default=4, choices=range(1,17))
    args = parser.parse_args()
    if args.online:
        obtain(json.loads(INPUT_LOCK.read_text()), args.cache, True)
        obtain(json.loads(TOOLCHAIN_LOCK.read_text()), args.cache, True)
    if args.bootstrap: bootstrap(args.cache.resolve(), args.output.resolve())
    else:
        if not args.toolchain: parser.error('--toolchain required for a build')
        build(args.cache.resolve(), args.toolchain.resolve(), args.output.resolve(), args.jobs)
