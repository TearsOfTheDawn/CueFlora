"""Non-UI framed PING and startup benchmark. Does not prove browser registration."""
import argparse
import json
import os
from pathlib import Path
import statistics
import time
from persistent_native import exchange


def probe(executable, repeats=5):
    timings = []
    result = None
    env = {key: value for key, value in os.environ.items()
           if key not in ('PYTHONPATH', 'PYTHONHOME', 'YT_DLP_PATH', 'FFMPEG_PATH', 'FFPROBE_PATH', 'DENO_PATH', 'CUEFLORA_EVIDENCE_DIR')}
    env['PATH'] = os.environ.get('SystemRoot', '/usr') + ('\\System32' if os.name == 'nt' else '/bin')
    for _ in range(repeats):
        start = time.perf_counter()
        responses, _ = exchange([str(executable.resolve())], [{'type':'PING'}, {'type':'PING'}],
                                       cwd=executable.parent, env=env)
        elapsed = (time.perf_counter() - start) * 1000
        for result in responses:
            if result.get('status') != 'PONG' or not all(result.get('tools', {}).get(tool, {}).get('available') for tool in ['yt-dlp','ffmpeg','ffprobe','deno']):
                raise RuntimeError('Unhealthy persistent native bundle')
        timings.append(round(elapsed, 2))
    return {'ping': result, 'startupMs': timings, 'medianMs': statistics.median(timings),
            'bundleBytes': sum(p.stat().st_size for p in executable.parent.rglob('*') if p.is_file()),
            'persistentPort':True, 'responsesBeforeClosingInput':2,
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
