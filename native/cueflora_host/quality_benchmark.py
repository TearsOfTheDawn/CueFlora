"""Controlled audio comparisons; never invent audio-reviewed reference scores.

Uploads fixed clips once per variant to the existing local endpoint. Full-run
upload replay is a separate quality_cli command. No production settings change.
"""
import argparse
from array import array
import json
import math
import os
from pathlib import Path
import subprocess
import time

from .download import _resolve_yt_dlp_executable
from .evidence import Capture, sha256
from .whisper import _post_transcription, _resolve_binary, _probe_duration_seconds


REGIONS = {
    "U_V6Jqg7PV4": [(0,20),(400,20),(535,20),(555,20),(575,20),(595,20),(833,20)],
    "zEpLJgf_4u0": [(0,20),(280,20),(60,20),(80,20),(100,15),(535,20),(555,14)],
}


def character_error_rate(reference, hypothesis):
    """Ignore whitespace/punctuation; retain substitutions, insertions, deletions.

    CER is reported only for reference text explicitly reviewed against audio.
    It is never a substitute for the separate meaning-error annotations.
    """
    a = ''.join(c for c in reference if c.isalnum())
    b = ''.join(c for c in hypothesis if c.isalnum())
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        nxt = [i]
        for j, y in enumerate(b, 1):
            nxt.append(min(nxt[-1] + 1, row[j] + 1, row[j-1] + (x != y)))
        row = nxt
    return {"errors": row[-1], "referenceCharacters": len(a),
            "cer": row[-1] / len(a) if a else None}


def waveform_check(ffmpeg, low, high, start, duration):
    """Alignment screen only. Strong correlation does not replace listening."""
    waves = []
    for source in (low, high):
        data = subprocess.check_output([ffmpeg, '-v', 'error', '-ss', str(start), '-i', str(source),
            '-t', str(duration), '-ac', '1', '-ar', '1000', '-f', 's16le', 'pipe:1'])
        samples = array('h', data)
        mean = sum(samples) / max(1, len(samples))
        waves.append([x - mean for x in samples])
    a,b = waves
    best = (-1.0, 0)
    for lag in range(-250, 251, 10):
        aa = a[max(0,lag):min(len(a),len(b)+lag)]
        bb = b[max(0,-lag):max(0,-lag)+len(aa)]
        if not aa or len(aa) != len(bb):
            continue
        denom = math.sqrt(sum(x*x for x in aa) * sum(x*x for x in bb))
        correlation = sum(x*y for x,y in zip(aa,bb)) / denom if denom else 0
        if correlation > best[0]:
            best = (correlation, lag)
    return {"correlation": round(best[0], 5), "lagMs": best[1],
            "listeningVerified": False, "eligibleForCausalComparison": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture')
    parser.add_argument('--high-format', help='Explicit same-track candidate format, e.g. 234')
    parser.add_argument('--prepare-only', action='store_true', help='Prepare all hashed inputs without requiring ASR')
    parser.add_argument('--replay-prepared', help='Run ASR on existing prepared inputs without downloading/re-encoding')
    parser.add_argument('--endpoint', help='Explicit transcription API base URL')
    parser.add_argument('--reference', help='Optional audio-reviewed JSON references indexed by clip start seconds')
    parser.add_argument('--only-starts', help='Comma-separated subset of the predefined clip starts')
    args = parser.parse_args()
    if not args.prepare_only and not args.endpoint:
        parser.error('Inference requires an explicit --endpoint')
    references = json.loads(Path(args.reference).read_text(encoding='utf-8')) if args.reference else {}
    subset = set(map(int,args.only_starts.split(','))) if args.only_starts else None
    if args.replay_prepared:
        path = Path(args.replay_prepared).resolve()
        manifest = json.loads(next(path.glob('run-*.json')).read_text(encoding='utf-8'))
        config = json.loads(next(path.glob('benchmark-config-*.json')).read_text(encoding='utf-8'))
        run = Capture(path, manifest['captureId'])
        for file in sorted(path.glob('benchmark-input-*.json')):
            item = json.loads(file.read_text(encoding='utf-8'))
            if subset is not None and item['start'] not in subset:
                continue
            audio = (path / item['input']['file']).resolve()
            if not audio.is_relative_to(path) or sha256(audio) != item['input']['sha256']:
                raise ValueError('Prepared input hash/path mismatch')
            started = time.monotonic()
            response = _post_transcription(audio,args.endpoint.rstrip('/')+'/audio/transcriptions',
                {'Authorization':'Bearer '+os.environ.get('CUEFLORA_ASR_KEY','local')},config['params'],
                'audio/ogg' if audio.suffix == '.ogg' else 'audio/flac',1)
            ref = references.get(str(item['start']), {})
            reviewed = ref.get('audioReviewed') is True and ref.get('uncertain') is False
            score = character_error_rate(ref['text'], response.get('text','')) if reviewed else None
            run.record('benchmark-result', {**item,'response':response,
                'durationMs':round((time.monotonic()-started)*1000),'cer':score,
                'meaningErrors':None,'missedSpeechSpans':None,'inventedSpeechSpans':None,
                'timingAccuracy':None,'eligibleForPromotion':False,'referenceStatus':'reviewed' if reviewed else 'missing'})
            print(json.dumps({'start':item['start'],'variant':item['variant'],
                'chars':len(response.get('text',''))}),flush=True)
        return
    if not args.capture or not args.high_format:
        parser.error('--capture and --high-format are required for a new benchmark')
    base = Path(args.capture).resolve()
    def read_one(kind):
        return json.loads(next(base.glob(kind+'-*.json')).read_text(encoding='utf-8'))
    manifest, preparation, config = read_one('run'), read_one('audio-preparation'), read_one('asr-config')
    video = manifest['videoId']
    source = preparation['source']
    low = (base / source['file']).resolve()
    if not low.is_relative_to(base) or sha256(low) != source['sha256']:
        raise ValueError('Baseline source hash/path mismatch')
    run = Capture.create(video, 'controlled-benchmark')
    if not run:
        raise ValueError('Set CUEFLORA_EVIDENCE_DIR explicitly')
    print('BENCHMARK_CAPTURE',run.capture_id,flush=True)
    fields = 'id,title,format_id,format_note,language,audio_channels,acodec,asr,abr,duration,manifest_stream_number'
    command = [_resolve_yt_dlp_executable(), '--format', args.high_format, '--no-playlist', '--no-warnings',
        '--output', str(run.path / 'higher-source.%(ext)s'), '--print', 'after_move:%(.{'+fields+'})j',
        '--print', 'after_move:filepath', 'https://www.youtube.com/watch?v='+video]
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', timeout=180, check=True)
    lines = result.stdout.strip().splitlines()
    high = Path(lines[-1]).resolve()
    if not high.is_relative_to(run.path):
        raise ValueError('Downloader output escaped capture')
    metadata = json.loads(lines[-2])
    ffmpeg = _resolve_binary('ffmpeg')
    # yt-dlp can return raw AAC despite a .mp4 suffix. Input-side seeking in
    # that stream estimates offsets from bitrate, selecting different content.
    # Decode once to native-rate/channel float PCM before accurate WAV seeking.
    # These are controlled intermediates, never the original production upload.
    decoded = []
    for label, source_path in [('low', low), ('high', high)]:
        target = run.path / f'decoded-{label}.wav'
        subprocess.run([ffmpeg, '-v', 'error', '-n', '-i', str(source_path),
            '-map', '0:a:0', '-c:a', 'pcm_f32le', str(target)], check=True, capture_output=True)
        decoded.append(target)
    low, high_decoded = decoded
    run.record('benchmark-config', {'baselineCapture': manifest['captureId'],
        'kind': 'controlled-clips-not-production-upload-replay', 'higherFormat': metadata,
        'lowerFormat': read_one('source-metadata'), 'higherSource': {'file':high.name, 'sha256':sha256(high)},
        'preparationVersion': 'decoded-float-pcm-seek-v2',
        'decodedSources': [{'file':p.name,'sha256':sha256(p)} for p in decoded],
        'params':config['params'], 'endpoint':args.endpoint,
        'maxUploadBytes':config['maxUploadBytes'],
        'durationLow':_probe_duration_seconds(low), 'durationHigh':_probe_duration_seconds(high_decoded),
        'speechReviewRequired':True, 'sameContentListeningRequired':True})
    high = high_decoded
    for start,duration in REGIONS[video]:
        if subset is not None and start not in subset:
            continue
        alignment = waveform_check(ffmpeg, low, high, start, duration)
        run.record('track-alignment', {'start':start,'duration':duration,**alignment})
        # 16 kHz is a separate resampling arm, not folded into the codec comparison.
        variants = [('A',low,'libopus',48000),('B',high,'libopus',48000),
                    ('C',low,'flac',48000),('D',high,'flac',48000),('D16',high,'flac',16000)]
        for label, source_path, codec, rate in variants:
            extension = 'ogg' if codec == 'libopus' else 'flac'
            output = run.path / f'clip-{start}-{label}.{extension}'
            cmd = [ffmpeg,'-v','error','-n','-ss',str(start),'-i',str(source_path),'-t',str(duration),
                   '-ar',str(rate),'-ac','1','-map','0:a','-c:a',codec]
            if codec == 'libopus':
                cmd += ['-b:a','24000']
            else:
                cmd += ['-sample_fmt','s16']
            subprocess.run(cmd+[str(output)],check=True,capture_output=True)
            # Fixed boundaries, no size-dependent re-chunking.
            if output.stat().st_size > config['maxUploadBytes']:
                raise ValueError('Controlled clip exceeds baseline upload limit')
            input_record = {'start':start,'duration':duration,'variant':label,'sampleRate':rate,'channels':1,
                'input':{'file':output.name,'sha256':sha256(output),'bytes':output.stat().st_size},
                'params':config['params']}
            run.record('benchmark-input',input_record)
            if args.prepare_only:
                print(json.dumps({'start':start,'variant':label,'prepared':True}),flush=True)
                continue
            started = time.monotonic()
            response = _post_transcription(output,args.endpoint.rstrip('/')+'/audio/transcriptions',
                {'Authorization':'Bearer '+os.environ.get('CUEFLORA_ASR_KEY','local')},config['params'],
                'audio/ogg' if codec == 'libopus' else 'audio/flac',1)
            ref = references.get(str(start),{})
            reviewed = ref.get('audioReviewed') is True and ref.get('uncertain') is False
            score = character_error_rate(ref['text'],response.get('text','')) if reviewed else None
            record = {'start':start,'duration':duration,'variant':label,'sampleRate':rate,'channels':1,
                'input':{'file':output.name,'sha256':sha256(output),'bytes':output.stat().st_size},
                'response':response,'durationMs':round((time.monotonic()-started)*1000),
                'cer':score,'meaningErrors':None,'missedSpeechSpans':None,'inventedSpeechSpans':None,
                'timingAccuracy':None,'eligibleForPromotion':False,'referenceStatus':'reviewed' if reviewed else 'missing'}
            run.record('benchmark-result',record)
            print(json.dumps({'start':start,'variant':label,'chars':len(response.get('text','')),
                              'durationMs':record['durationMs'],'cer':score}),flush=True)
    print('COMPLETE_NO_AUTOMATIC_PROMOTION',run.capture_id,flush=True)


if __name__ == '__main__':
    main()
