"""Append objective benchmark summaries; never label disagreement as accuracy."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics

from .evidence import Capture


def summarize(path):
    manifest = json.loads(next(path.glob('run-*.json')).read_text(encoding='utf-8'))
    records = [json.loads(p.read_text(encoding='utf-8')) for p in path.glob('benchmark-result-*.json')]
    groups = defaultdict(list)
    variants = defaultdict(list)
    for item in records:
        groups[(item['start'], item['variant'], item['input']['sha256'])].append(item)
        variants[item['variant']].append(item)
    alignment = [json.loads(p.read_text(encoding='utf-8')) for p in path.glob('track-alignment-*.json')]
    summary = {'captureId': manifest['captureId'], 'resultCount': len(records),
        'uniqueInputs': len(groups), 'repeatedInputs': sum(len(g)>1 for g in groups.values()),
        'textVariedOnIdenticalInput': sum(len({r['response'].get('text','') for r in g})>1 for g in groups.values()),
        'correlationRange': [min(a['correlation'] for a in alignment), max(a['correlation'] for a in alignment)],
        'maxAbsoluteLagMs': max(abs(a['lagMs']) for a in alignment),
        'variants': {k: {'requests':len(v), 'meanUploadBytes':round(statistics.mean(r['input']['bytes'] for r in v)),
            'meanDurationMs': round(statistics.mean(r['durationMs'] for r in v)),
            'emptyOutputCount':sum(not r['response'].get('text','').strip() for r in v)} for k,v in sorted(variants.items())},
        'accuracyStatus':'unscored-no-audio-reviewed-reference', 'eligibleForPromotion':False}
    Capture(path, manifest['captureId']).record('benchmark-summary', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', nargs='+')
    args = parser.parse_args()
    for path in args.capture:
        print(json.dumps(summarize(Path(path).resolve()), indent=2))


if __name__ == '__main__':
    main()
