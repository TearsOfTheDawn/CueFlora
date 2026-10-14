"""Repeatable approved-recipe/functional checks; no private baseline or inference."""
import argparse
import base64
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from unittest.mock import patch
from audio_build import ROOT, CONFIGURE, digest
from verify_audio_tools import command, decoded, synthetic, whisper


def validate_recipe(folder):
    build_file = folder/'audio-build.json'
    build = json.loads(build_file.read_text())
    audit_file = folder/'corresponding-source/toolchain-audit.json'
    audit = json.loads(audit_file.read_text())
    policy = json.loads((ROOT/'packaging/audio-policy.json').read_text())
    if policy.get('schema') != 1 or policy['configureFFmpeg'] != CONFIGURE or policy['ffmpegVersion'] != '9.0.2':
        raise ValueError('Audio recipe changed without an explicit policy update')
    if build.get('version') != policy['ffmpegVersion'] or build.get('sourceSignatureVerified') is not True or build.get('inputLockSha256') != digest(ROOT/'packaging/audio-inputs.lock.json') or build.get('toolchainLockSha256') != digest(ROOT/'packaging/audio-toolchain.lock.json'):
        raise ValueError('Audio inputs do not match approved pinned recipe')
    if audit.get('passed') is not True or not audit.get('files') or digest(audit_file) != build.get('toolchainAuditSha256'):
        raise ValueError('Audio compiler audit is missing or mismatched')
    flags = build.get('configureFFmpeg',[])
    if flags[4:] != CONFIGURE or len(flags) != len(CONFIGURE)+4 or flags[0] != './configure' or not flags[1].startswith('--prefix=') or not flags[2].startswith('--extra-cflags=-I') or not flags[3].startswith('--extra-ldflags=-L'):
        raise ValueError('Audio configuration is not the approved recipe')
    opus = build.get('configureOpus',[])
    if len(opus) != 8 or opus[:2] != ['./configure','--host=x86_64-w64-mingw32'] or not opus[2].startswith('--prefix=') or opus[3:] != ['--enable-shared','--disable-static','--disable-doc','--disable-extra-programs','LDFLAGS=-static-libgcc']:
        raise ValueError('Opus configuration differs from approved recipe')
    files = build.get('files')
    if not isinstance(files,dict) or not {'ffmpeg.exe','ffprobe.exe'}.issubset(files): raise ValueError('Audio payload missing')
    for name,checksum in files.items():
        path = folder/'install/bin'/name
        if Path(name).name != name or ':' in name or path.suffix.lower() not in ('.exe','.dll') or path.is_symlink() or digest(path) != checksum:
            raise ValueError('Unsafe or changed audio payload')
    return build


def fixture_inputs(output, fixture_file=None):
    path = fixture_file or ROOT/'packaging/fixtures/synthetic-audio.json'
    record = json.loads(path.read_text())
    if record.get('schema') != 1 or set(record.get('files',{})) != {'tone.m4a','tone.mp3','tone.flac','tone.ogg','tone.webm'}:
        raise ValueError('Incomplete public synthetic audio fixtures')
    result = []
    for name,item in record['files'].items():
        content = base64.b64decode(item['base64'],validate=True)
        if not content or len(content)>1024*1024 or hashlib.sha256(content).hexdigest() != item['sha256'] or item['durationSeconds'] != 0.5:
            raise ValueError('Changed synthetic fixture or metadata')
        target = output/name; target.write_bytes(content); result.append((target,0.5))
    return result


def verify(candidate, output):
    if output.exists(): raise ValueError('Fresh audio conformance output required')
    if os.name == 'nt': ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002 | 0x8000)
    build = validate_recipe(candidate)
    output.mkdir(parents=True)
    report = {'schema':1,'kind':'approved-recipe-conformance','passed':False,'audioBuildSha256':digest(candidate/'audio-build.json'),
        'candidateFileHashes':build['files'],'policySha256':digest(ROOT/'packaging/audio-policy.json'),
        'fixtureSha256':digest(ROOT/'packaging/fixtures/synthetic-audio.json'),
        'privateBaselineRequired':False,'inference':False,'semanticAcceptance':False,'cases':[]}
    report_path = output/'audio-conformance.json'
    def save(): report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    save()
    tools = candidate/'install/bin'
    try:
        source = output/'synthetic-stereo.wav'; synthetic(source)
        inputs = [(source,32.0),*fixture_inputs(output)]
        for source,duration in inputs:
            folder = output/source.suffix.removeprefix('.'); folder.mkdir()
            original = folder/source.name; shutil.copy2(source,original)
            with patch.object(whisper,'_resolve_binary',side_effect=lambda name:str(tools/(name+'.exe'))):
                prepared = whisper.compress_audio(str(original))
                chunks = whisper._split_into_chunks(prepared,12,2,str(folder))
            samples = decoded(tools/'ffmpeg.exe',prepared)
            actual_duration = len(samples)/48000
            if abs(actual_duration-duration)>0.1 or not chunks or Path(prepared).stat().st_size >= whisper.MAX_SINGLE_UPLOAD_BYTES:
                raise ValueError('Audio duration/coverage/upload conformance failed')
            if not any(abs(value)>0.05 for value in samples) or any(abs(value)>1.1 for value in samples): raise ValueError('Audio signal lost or invalid')
            if duration==32 and [chunk['start_s'] for chunk in chunks] != [0,10,20,30]: raise ValueError('Production chunk boundaries changed')
            report['cases'].append({'format':source.suffix,'durationSeconds':actual_duration,'uploadBytes':Path(prepared).stat().st_size,
                'chunks':[{key:chunk[key] for key in ('start_s','end_s','keep_from_s','keep_to_s')} for chunk in chunks]})
            save()
        malformed = output/'malformed.wav'; malformed.write_bytes(b'not audio')
        with patch.object(whisper,'_resolve_binary',side_effect=lambda name:str(tools/(name+'.exe'))):
            try: whisper.compress_audio(str(malformed))
            except RuntimeError: report['malformedInputRejected']=True
            else: raise ValueError('Malformed audio accepted')
        with tempfile.TemporaryDirectory(prefix='音频 tools with spaces ',dir=output) as temporary:
            isolated = Path(temporary)
            for name in build['files']: shutil.copy2(tools/name,isolated/name)
            environment = {key.upper():value for key,value in os.environ.items()}
            environment['PATH']=str(Path(environment.get('SYSTEMROOT',r'C:\Windows'))/'System32')
            for name in ('ffmpeg','ffprobe'): command([isolated/(name+'.exe'),'-version'],environment)
            report['restrictedPathUnicodePassed']=True
            required = next(isolated.glob('avcodec-*.dll')); required.rename(required.with_suffix('.withheld'))
            try: failure=subprocess.run([str(isolated/'ffmpeg.exe'),'-version'],capture_output=True,timeout=15,env=environment)
            except OSError: failure=None
            if failure is not None and failure.returncode==0: raise ValueError('Missing DLL did not fail')
            report['missingDllRejected']=True
        report['passed']=True; save()
        print(json.dumps({'passed':True,'formats':len(inputs),'privateBaselineRequired':False,'semanticAcceptance':False}),flush=True)
        return report
    except Exception as error:
        report['failure']=type(error).__name__+': '+str(error); save(); raise


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('candidate','output'): parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args(); verify(args.candidate.resolve(),args.output.resolve())
