"""Controlled translation replay: exact saved request versus temperature alone.

Developer-only experiment. Never changes production prompts, recovery or settings.
Requires an explicitly named capture and records every request/result append-only.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import time

import httpx

from .evidence import Capture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', required=True)
    parser.add_argument('--request', required=True, help='Saved translation-request JSON basename')
    parser.add_argument('--endpoint', required=True, help='Explicit translation API base URL')
    args = parser.parse_args()
    path = Path(args.capture).resolve()
    request = (path / args.request).resolve()
    if not request.is_relative_to(path):
        raise ValueError('Request escaped capture')
    original = json.loads(request.read_text(encoding='utf-8'))['body']
    manifest = json.loads(next(path.glob('run-*.json')).read_text(encoding='utf-8'))
    capture = Capture(path, manifest['captureId'])
    for repetition in range(3):
        for label, temperature in [('control', original['temperature']), ('temperature-zero', 0)]:
            body = copy.deepcopy(original)
            body['temperature'] = temperature
            saved = capture.record('translation-experiment-request', {
                'originalRecord': request.name, 'variant': label, 'repetition': repetition,
                'endpoint': args.endpoint, 'body': body})
            started = time.monotonic()
            response = httpx.post(args.endpoint.rstrip('/')+'/chat/completions', json=body,
                headers={'Authorization': 'Bearer '+os.environ.get('CUEFLORA_TRANSLATION_KEY', 'local')},
                timeout=300)
            capture.record('translation-experiment-result', {'requestRecord': saved,
                'status': response.status_code, 'durationMs': round((time.monotonic()-started)*1000),
                'body': response.json()})
            response.raise_for_status()
            print(json.dumps({'variant':label, 'repetition':repetition, 'status':response.status_code}), flush=True)


if __name__ == '__main__':
    main()
