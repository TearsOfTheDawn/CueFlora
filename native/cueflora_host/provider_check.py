"""User-triggered bounded metadata requests; never invokes inference."""
import json
import re
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
        with httpx.Client(timeout=10, follow_redirects=False) as client:
            with client.stream('GET', base.rstrip('/') + '/models', headers=headers) as response:
                if response.status_code in (401, 403):
                    return {**result, 'reason': 'auth'}
                if response.status_code in (404, 405, 501):
                    return {**result, 'status': 'unsupported', 'reason': 'unsupported'}
                if response.status_code != 200:
                    return {**result, 'reason': 'http'}
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 256 * 1024:
                        return {**result, 'reason': 'oversized'}
        payload = json.loads(raw)
        data = payload.get('data') if isinstance(payload, dict) else None
        if not isinstance(data, list):
            return result
        ids = []
        for item in data:
            identifier = item.get('id') if isinstance(item, dict) else None
            if not isinstance(identifier, str) or not re.fullmatch(r'[\w.:/\-]{1,200}', identifier, flags=re.ASCII):
                return result
            if key and key in identifier:
                return result
            ids.append(identifier)
            if len(ids) > 500:
                return {**result, 'reason': 'oversized'}
        return {**result, 'status': 'connected', 'reason': 'ok', 'models': sorted(set(ids))}
    except httpx.HTTPError:
        return {**result, 'reason': 'network'}
    except (ValueError, TypeError, KeyError):
        return result
