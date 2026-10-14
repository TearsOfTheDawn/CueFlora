"""Actual production preparation compatibility on synthetic audio; no ASR/HTTP."""
import argparse
import array
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import wave
from unittest.mock import patch
from audio_build import digest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'native'))
from cueflora_host import whisper


def command(parts, environment=None):
    result = subprocess.run(list(map(str,parts)),capture_output=True,timeout=120,env=environment)
    if result.returncode: raise RuntimeError('Audio compatibility command failed: '+Path(parts[0]).name)
    return result.stdout


def synthetic(path):
    with wave.open(str(path),'wb') as audio:
        audio.setnchannels(2); audio.setsampwidth(2); audio.setframerate(44100)
        data = bytearray()
        for index in range(32*44100):
            seconds = index/44100
            value = 0 if seconds < 2 or 15 < seconds < 17 else int(9000*math.sin(2*math.pi*(220+40*int(seconds)%5)*seconds)+3000*math.sin(2*math.pi*760*seconds))
            data.extend(struct.pack('<hh',value,value//2))
        audio.writeframes(data)


def decoded(executable, path):
    data = command([executable,'-v','error','-i',path,'-map','0:a','-ar','48000','-ac','1','-f','f32le','pipe:1'])
    result = array.array('f'); result.frombytes(data)
    if not result or not all(math.isfinite(value) for value in result): raise ValueError('Invalid decoded audio samples')
    return result


def verify(candidate, baseline, output):
    if os.name == 'nt': ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002 | 0x8000)
    if output.exists(): raise ValueError('Fresh audio-compatibility output required')
    output.mkdir(parents=True)
    report_path = output/'audio-compatibility.json'
    build = json.loads((candidate/'audio-build.json').read_text())
    bin_dir = candidate/'install/bin'
    if build.get('version') != '9.0.2' or build.get('sourceSignatureVerified') is not True:
        raise ValueError('Approved audio build required')
    for name, checksum in build['files'].items():
        if digest(bin_dir/name) != checksum: raise ValueError('Changed candidate audio binary')
    report = {'schema':1,'passed':False,'audioBuildSha256':digest(candidate/'audio-build.json'),
        'candidateFileHashes':build['files'],'baselineFileHashes':{name:digest(baseline/(name+'.exe')) for name in ('ffmpeg','ffprobe')},
        'syntheticAudioOnly':True,'inference':False,'semanticAcceptance':False,'cases':[]}
    def save(): report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    save()
    try:
        source = output/'synthetic-stereo.wav'; synthetic(source)
        formats = [('wav',None),('m4a','aac'),('mp3','libmp3lame'),('flac','flac'),('ogg','libvorbis'),('webm','libopus')]
        for extension, encoder in formats:
            original = output/('input.'+extension)
            if encoder:
                command([baseline/'ffmpeg.exe','-v','error','-y','-i',source,'-c:a',encoder,original])
            else: shutil.copy2(source,original)
            results = {}
            for label, tools in [('baseline',baseline),('candidate',bin_dir)]:
                folder = output/(label+'-'+extension); folder.mkdir()
                input_file = folder/original.name; shutil.copy2(original,input_file)
                started = time.monotonic()
                with patch.object(whisper,'_resolve_binary',side_effect=lambda name,t=tools:str(t/(name+'.exe'))):
                    prepared = whisper.compress_audio(str(input_file))
                    chunks = whisper._split_into_chunks(prepared,12,2,str(folder))
                if not chunks: raise ValueError('Production chunking returned no chunks')
                samples = decoded(tools/'ffmpeg.exe',prepared)
                chunk_records = [{key:chunk[key] for key in ('start_s','end_s','keep_from_s','keep_to_s')} for chunk in chunks]
                results[label] = {'seconds':round(time.monotonic()-started,3),'uploadBytes':Path(prepared).stat().st_size,
                    'decodedSamples':len(samples),'samples':samples,'chunks':chunk_records}
                if results[label]['uploadBytes'] >= whisper.MAX_SINGLE_UPLOAD_BYTES: raise ValueError('Unexpected oversized synthetic upload')
            previous = results['baseline'].pop('samples'); current = results['candidate'].pop('samples')
            count = min(len(previous),len(current))
            rmse = math.sqrt(sum((previous[index]-current[index])**2 for index in range(count))/count)
            if abs(len(previous)-len(current)) > 2400: raise ValueError('Prepared audio duration changed by more than 50ms')
            old_chunks,new_chunks = results['baseline']['chunks'],results['candidate']['chunks']
            if len(old_chunks)!=len(new_chunks) or any(abs(a[field]-b[field])>0.05 for a,b in zip(old_chunks,new_chunks) for field in a):
                raise ValueError('Production chunk-boundary compatibility failed')
            report['cases'].append({'format':extension,'baseline':results['baseline'],'candidate':results['candidate'],
                'decodedPCMIdentical':previous==current,'decodedRMSE':rmse,'interpretation':'Measured signal difference, not a recognition/meaning score.'})
            save()
        malformed = output/'malformed.wav'; malformed.write_bytes(b'not audio')
        with patch.object(whisper,'_resolve_binary',side_effect=lambda name:str(bin_dir/(name+'.exe'))):
            try: whisper.compress_audio(str(malformed))
            except RuntimeError: report['malformedInputRejected'] = True
            else: raise ValueError('Malformed audio was accepted')
        with tempfile.TemporaryDirectory(prefix='路径 with spaces ',dir=output) as directory:
            isolated = Path(directory)
            for name in build['files']: shutil.copy2(bin_dir/name,isolated/name)
            environment = {key.upper():value for key,value in os.environ.items()}
            environment['PATH'] = str(Path(environment['SYSTEMROOT'])/'System32')
            version = command([isolated/'ffmpeg.exe','-version'],environment).decode()
            command([isolated/'ffprobe.exe','-version'],environment)
            if not version.startswith('ffmpeg version 9.0.2'): raise ValueError('Wrong candidate audio version')
            report['restrictedPathUnicodePassed'] = True
            required = next(isolated.glob('avcodec-*.dll'))
            withheld = required.with_suffix('.withheld'); required.rename(withheld)
            try:
                failure = subprocess.run([str(isolated/'ffmpeg.exe'),'-version'],capture_output=True,timeout=15,env=environment)
            except OSError:
                failure = None
            if failure is not None and failure.returncode == 0: raise ValueError('Missing required audio DLL did not fail')
            report['missingDllRejected'] = True
        report['passed'] = True; save()
        shutil.copy2(report_path,candidate/'audio-compatibility.json')
        print(json.dumps({'passed':True,'formats':len(formats),'pcmIdenticalCases':sum(item['decodedPCMIdentical'] for item in report['cases']),
            'semanticAcceptance':False}),flush=True)
        return report
    except Exception as error:
        report['failure'] = type(error).__name__+': '+str(error); save()
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--baseline',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    verify(args.candidate.resolve(),args.baseline.resolve(),args.output.resolve())
