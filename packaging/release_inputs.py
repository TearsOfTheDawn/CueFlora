"""Strict, offline-capable build inputs. Hashes are integrity, not release approval."""
import ast
import hashlib
import importlib.metadata
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import urllib.request
import zipfile
import io
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
TOOLS = {'yt-dlp', 'ffmpeg', 'ffprobe', 'deno'}


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def validate_lock(lock):
    if not isinstance(lock, dict) or lock.get('schema') != 1 or lock.get('platform') != 'Windows-x64':
        raise ValueError('Unsupported input lock')
    files = lock.get('files')
    if not isinstance(files, list) or not files:
        raise ValueError('Empty input lock')
    names = set()
    for item in files:
        if not isinstance(item, dict):
            raise ValueError('Invalid input entry')
        name = item.get('file', '')
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', name) or name in ('.', '..') or name.casefold() in names:
            raise ValueError('Unsafe/duplicate input name')
        names.add(name.casefold())
        if not re.fullmatch('[0-9a-f]{64}', str(item.get('sha256', ''))):
            raise ValueError('Invalid input hash')
        url = item.get('url')
        if url is not None:
            if not isinstance(url,str): raise ValueError('Invalid input URL')
            parsed = urlsplit(url)
            if parsed.scheme != 'https' or parsed.netloc not in ('github.com','codeload.github.com','raw.githubusercontent.com','files.pythonhosted.org') or parsed.query or parsed.fragment:
                raise ValueError('Unapproved input origin')
    tools = lock.get('tools')
    if not isinstance(tools, dict) or set(tools) != TOOLS or any(name not in {i['file'] for i in files} for name in tools.values()):
        raise ValueError('All four pinned tools required')
    wheels = lock.get('pythonWheels')
    if not isinstance(wheels, list) or not wheels or any(not isinstance(w,dict) or w.get('file') not in {i['file'] for i in files} for w in wheels):
        raise ValueError('Pinned Python wheels required')
    native=lock.get('wheelNativeFiles',[]);native_names=set()
    if not isinstance(native,list):raise ValueError('Invalid native wheel inventory')
    for item in native:
        if not isinstance(item,dict) or set(item)!={'wheel','file','sha256'} or item['wheel'] not in {wheel['file'] for wheel in wheels}:raise ValueError('Invalid native wheel origin')
        path=PurePosixPath(str(item['file']));identity=(item['wheel'],item['file'])
        if path.is_absolute() or '..' in path.parts or path.as_posix()!=item['file'] or '\\' in item['file'] or ':' in item['file'] or path.suffix not in ('.pyd','.dll') or identity in native_names or not re.fullmatch('[0-9a-f]{64}',str(item['sha256'])):raise ValueError('Invalid native wheel member')
        native_names.add(identity)
    if not re.fullmatch(r'\d+\.\d+\.\d+',str(lock.get('pythonVersion',''))):
        raise ValueError('Pinned Python version required')
    interpreter = lock.get('interpreterFiles')
    if not isinstance(interpreter,list) or not interpreter: raise ValueError('Interpreter hashes required')
    seen = set()
    for item in interpreter:
        if not isinstance(item,dict) or not isinstance(item.get('file'),str): raise ValueError('Invalid interpreter entry')
        path = PurePosixPath(item['file'])
        if path.is_absolute() or '..' in path.parts or path.as_posix() != item['file'] or '\\' in item['file'] or ':' in item['file'] or item['file'].casefold() in seen or not re.fullmatch('[0-9a-f]{64}',str(item.get('sha256',''))):
            raise ValueError('Unsafe interpreter input')
        seen.add(item['file'].casefold())
    if lock.get('publicReleaseAuthorized') is not False or lock.get('redistributionApproved') is not False:
        raise ValueError('Input lock cannot grant release approval')
    return lock


def obtain_inputs(lock, cache, offline=True, source_audio=False):
    validate_lock(lock)
    cache = Path(cache).resolve()
    cache.mkdir(parents=True, exist_ok=True)
    for item in lock['files']:
        if source_audio and (item['file'] in ('ffmpeg.exe','ffprobe.exe','python-3.13.15-local-base.zip') or item['file'].startswith('FFmpeg-5d4d3bdc61-')):
            continue  # Generated audio outputs and official Python replace private bootstrap inputs.
        path = cache / item['file']
        if path.exists():
            if path.is_symlink() or not path.is_file() or digest(path) != item['sha256']:
                raise ValueError('Mismatched cached input: ' + item['file'])
            continue
        if offline or not item.get('url'):
            if item['file'] == 'deno.exe' and (cache / 'deno-2.9.7-windows-x64.zip').is_file():
                with zipfile.ZipFile(cache / 'deno-2.9.7-windows-x64.zip') as archive:
                    if archive.namelist() != ['deno.exe']:
                        raise ValueError('Unexpected Deno archive')
                    with path.open('xb') as stream:
                        stream.write(archive.read('deno.exe'))
                if digest(path) != item['sha256']:
                    raise ValueError('Extracted Deno hash mismatch')
                continue
            raise ValueError('Missing pinned input: ' + item['file'])
        # Exclusive partial files prevent interrupted downloads being accepted.
        partial = path.with_name(path.name + '.partial')
        with urllib.request.urlopen(item['url'], timeout=60) as response, partial.open('xb') as stream:
            shutil.copyfileobj(response, stream)
        if digest(partial) != item['sha256']:
            raise ValueError('Downloaded input hash mismatch: ' + item['file'])
        partial.rename(path)
    for item in lock.get('wheelNativeFiles',[]):
        with zipfile.ZipFile(cache/item['wheel']) as archive:
            if archive.namelist().count(item['file'])!=1 or hashlib.sha256(archive.read(item['file'])).hexdigest()!=item['sha256']:raise ValueError('Native member does not match its exact wheel origin')
    return cache


def verify_environment(lock):
    if sys.version.split()[0] != lock['pythonVersion']:
        raise ValueError('Pinned Python interpreter version required')
    for wheel in lock['pythonWheels']:
        if importlib.metadata.version(wheel['name']) != wheel['version']:
            raise ValueError('Build environment version mismatch: ' + wheel['name'])
    for item in lock['interpreterFiles']:
        if digest(Path(sys.base_prefix) / item['file']) != item['sha256']:
            raise ValueError('Interpreter input mismatch: ' + item['file'])


def inspect_ejs(executable):
    from PyInstaller.archive.readers import CArchiveReader
    archive = CArchiveReader(str(executable))
    names = {n.replace('\\', '/'): n for n in archive.toc}
    required = ['yt_dlp_ejs/yt/solver/core.min.js', 'yt_dlp_ejs/yt/solver/lib.min.js']
    if any(name not in names for name in required):
        raise ValueError('Pinned yt-dlp is missing local EJS solver components')
    return {name: hashlib.sha256(archive.extract(names[name])).hexdigest() for name in required}


def source_inventory():
    from source_export import inventory
    records, issues = inventory(ROOT)
    if issues: raise ValueError('Source publication audit has unresolved path/reason flags')
    return records


def shipped_python(analysis):
    toc = ast.literal_eval(Path(analysis).read_text(encoding='utf-8'))
    def tuples(value):
        if isinstance(value, (list, tuple)):
            if len(value) == 3 and isinstance(value[0], str) and value[2] == 'PYMODULE':
                yield value[0].split('.')[0]
            else:
                for child in value:
                    yield from tuples(child)
    mapping = importlib.metadata.packages_distributions()
    dependencies = sorted({name for module in tuples(toc) for name in mapping.get(module, [])})
    return [{'name': name, 'version': importlib.metadata.version(name), 'scope': 'analysis-observed Python module'} for name in dependencies]


def compare_outputs(first, second):
    def inventory(root):
        return {p.relative_to(root).as_posix(): digest(p) for p in root.rglob('*') if p.is_file()}
    left, right = inventory(Path(first)), inventory(Path(second))
    return {'sameNames': left.keys() == right.keys(), 'identical': left == right,
            'differentFiles': [name for name in sorted(left.keys() | right.keys()) if left.get(name) != right.get(name)],
            'interpretation': 'Compare source/input hashes separately. PE build timestamps, frozen bytecode, archive metadata and bundle manifests can differ; input equality alone does not establish binary reproducibility.'}


def explain_frozen_differences(first, second):
    import pefile
    from PyInstaller.archive.readers import CArchiveReader
    paths = [Path(first), Path(second)]
    pe = [pefile.PE(str(path), fast_load=True) for path in paths]
    normalized = []
    normalized_fields = []
    for path, image in zip(paths, pe):
        data = bytearray(path.read_bytes())
        image.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_DEBUG']])
        fields = [('IMAGE_FILE_HEADER.TimeDateStamp', image.FILE_HEADER.get_field_absolute_offset('TimeDateStamp')),
                  ('OPTIONAL_HEADER.CheckSum', image.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum'))]
        fields += [('IMAGE_DEBUG_DIRECTORY.TimeDateStamp',entry.struct.get_field_absolute_offset('TimeDateStamp')) for entry in getattr(image,'DIRECTORY_ENTRY_DEBUG',[])]
        normalized_fields.append([{'field':name,'offset':offset} for name,offset in fields])
        for _,offset in fields:
            data[offset:offset+4] = b'\0'*4
        normalized.append(hashlib.sha256(data).hexdigest())
    archives = [CArchiveReader(str(path)) for path in paths]
    names = set(archives[0].toc) | set(archives[1].toc)
    changed = [name for name in sorted(names) if name not in archives[0].toc or name not in archives[1].toc or archives[0].extract(name) != archives[1].extract(name)]
    return {'peTimestamps':[image.FILE_HEADER.TimeDateStamp for image in pe], 'normalizedFields':normalized_fields,
        'equalAfterNormalizingPeTimestampAndChecksum':normalized[0] == normalized[1],
        'archiveEntryDifferences':changed,
        'interpretation':'Host PE-only differences can be verified using normalized hashes. Setup additionally embeds differing runtime ZIP/header/inventory/binding bytes; compare the listed entries, not merely the whole EXE hash.'}


def explain_library_order(first, second):
    with zipfile.ZipFile(first) as left, zipfile.ZipFile(second) as right:
        names = set(left.namelist()) | set(right.namelist())
        changed = [name for name in sorted(names) if name not in left.namelist() or name not in right.namelist() or left.read(name) != right.read(name)]
        return {'entryCount':len(names),'sameEntryOrder':left.namelist() == right.namelist(),
            'differentEntryContents':changed,
            'interpretation':'Different ZIP entry order with identical entry contents explains an archive hash difference; it is not altered Python source or inference behavior.'}
