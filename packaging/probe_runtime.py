"""Non-UI framed PING and startup benchmark. Does not prove browser registration."""
import argparse
import json
import os
from pathlib import Path
import statistics
import struct
import subprocess
import time


def probe(executable, repeats=5):
    body = json.dumps({'type': 'PING'}).encode()
    packet = struct.pack('<I', len(body)) + body
    timings = []
    result = None
    env = {key: value for key, value in os.environ.items()
           if key not in ('PYTHONPATH', 'PYTHONHOME', 'YT_DLP_PATH', 'FFMPEG_PATH', 'FFPROBE_PATH', 'DENO_PATH', 'CUEFLORA_EVIDENCE_DIR')}
    env['PATH'] = os.environ.get('SystemRoot', '/usr') + ('\\System32' if os.name == 'nt' else '/bin')
    for _ in range(repeats):
        start = time.perf_counter()
        response = subprocess.run([str(executable.resolve())], input=packet, capture_output=True, timeout=45,
                                  cwd=executable.parent, env=env)
        elapsed = (time.perf_counter() - start) * 1000
        data = response.stdout
        if response.returncode or len(data) < 4 or struct.unpack('<I', data[:4])[0] != len(data) - 4:
            raise RuntimeError('Invalid framed PING/exit status')
        result = json.loads(data[4:])
        if result.get('status') != 'PONG' or not all(result.get('tools', {}).get(tool, {}).get('available') for tool in ['yt-dlp','ffmpeg','ffprobe','deno']):
            raise RuntimeError(f'Unhealthy bundle: {result}')
        timings.append(round(elapsed, 2))
    return {'ping': result, 'startupMs': timings, 'medianMs': statistics.median(timings),
            'bundleBytes': sum(p.stat().st_size for p in executable.parent.rglob('*') if p.is_file()),
            'browserRegistrationVerified': False, 'cleanMachineVerified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    report = probe(args.executable)
    with args.report.open('x', encoding='utf-8') as output:
        json.dump(report, output, indent=2)
    print(json.dumps(report, indent=2))
