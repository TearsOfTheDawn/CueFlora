"""User-triggered bounded metadata requests; never invokes inference."""
import json
import re
import time
from urllib.parse import urlsplit
import httpx
from .provider_security import validate_transport
from .credentials import resolve_key


def check_provider(message):
    result = {'requestId': message.get('requestId'), 'status': 'unavailable', 'reason': 'invalid-response', 'models': []}
    provider = message.get('provider')
    if not isinstance(provider, dict):
        return result
    try:
        base = validate_transport(provider, message.get('transportPolicy', 'preview'))
        key = resolve_key(provider, message.get('stage', 'transcription'))
        headers = {'Authorization': 'Bearer ' + key} if key else {}
        is_openrouter = urlsplit(base).hostname == 'openrouter.ai' and urlsplit(base).path.rstrip('/') == '/api/v1'
        endpoint = base.rstrip('/') + '/models'
        if is_openrouter and message.get('stage') == 'transcription':
            endpoint += '?output_modalities=transcription'
        started = time.monotonic()
        with httpx.Client(timeout=10, follow_redirects=False) as client:
            with client.stream('GET', endpoint, headers=headers) as response:
                result['reachable'] = True
                if response.status_code in (401, 403):
                    return {**result, 'reason': 'auth'}
                if response.status_code in (404, 405, 501):
                    return {**result, 'status': 'unsupported', 'reason': 'unsupported'}
                if response.status_code != 200:
                    return {**result, 'reason': 'http'}
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if time.monotonic() - started > 10:
                        return {**result, 'reason':'timeout'}
                    if len(raw) > 4 * 1024 * 1024:
                        return {**result, 'reason': 'oversized'}
        payload = json.loads(raw)
        data = payload.get('data') if isinstance(payload, dict) else None
        if not isinstance(data, list):
            return result
        ids = []
        partial = False
        for item in data:
            identifier = item.get('id') if isinstance(item, dict) else None
            if not isinstance(identifier, str) or not re.fullmatch(r'[\w.:/\-]{1,200}', identifier, flags=re.ASCII):
                return result
            if key and key in identifier:
                return result
            if message.get('stage') == 'translation':
                architecture = item.get('architecture')
                outputs = architecture.get('output_modalities') if isinstance(architecture, dict) else None
                inputs = architecture.get('input_modalities') if isinstance(architecture, dict) else None
                parameters = item.get('supported_parameters')
                if isinstance(outputs, list) and 'text' not in outputs: continue
                if isinstance(inputs, list) and 'text' not in inputs: continue
                if isinstance(parameters, list) and not {'response_format','structured_outputs'}.intersection(parameters): continue
            if identifier not in ids:
                if len(ids) < 500: ids.append(identifier)
                else: partial = True
        return {**result, 'status': 'connected', 'reason': 'ok', 'models': sorted(ids),
                'partial':partial, 'modelListAvailable':True, 'generationCompatibility':'unverified'}
    except httpx.TimeoutException:
        return {**result, 'reason': 'timeout'}
    except httpx.HTTPError:
        return {**result, 'reason': 'network'}
    except (ValueError, TypeError, KeyError):
        return result
