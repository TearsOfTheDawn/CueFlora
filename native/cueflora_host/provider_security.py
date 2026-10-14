"""Provider transport policy; independent of subtitle/inference configuration."""
from urllib.parse import urlsplit, urlunsplit
import json
from pathlib import Path
import sys

LOOPBACK = {'localhost', '127.0.0.1', '::1'}


def normalize_endpoint(value):
    if not isinstance(value, str) or not value or len(value) > 2048 or '\\' in value or any(c.isspace() for c in value):
        raise ValueError('Invalid service address')
    parsed = urlsplit(value)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise ValueError('Use an HTTP(S) service address without embedded credentials')
    host = parsed.hostname.lower()
    port = parsed.port
    authority = '[' + host + ']' if ':' in host else host
    if port and port != (443 if parsed.scheme == 'https' else 80):
        authority += ':' + str(port)
    return urlunsplit((parsed.scheme, authority, parsed.path.rstrip('/'), '', ''))


def validate_transport(provider, policy='preview'):
    if policy not in ('preview', 'https-remote'):
        raise ValueError('Invalid transport policy')
    if getattr(sys, 'frozen', False):
        manifest = Path(sys.executable).parent / 'runtime-manifest.json'
        try:
            packaged_policy = json.loads(manifest.read_text(encoding='utf-8')).get('transportPolicy', 'preview')
        except (OSError, ValueError):
            raise ValueError('Runtime transport policy is unavailable; repair CueFlora') from None
        if packaged_policy not in ('preview', 'https-remote'):
            raise ValueError('Invalid runtime transport policy; repair CueFlora')
        if packaged_policy == 'https-remote': policy = packaged_policy
    endpoint = normalize_endpoint(provider.get('baseUrl'))
    parsed = urlsplit(endpoint)
    if parsed.scheme == 'http' and parsed.hostname not in LOOPBACK:
        if policy == 'https-remote':
            raise ValueError('Remote services require HTTPS in store candidates')
        if provider.get('allowRemoteHttp') is not True:
            raise ValueError('Acknowledge unencrypted non-loopback HTTP first')
    return endpoint
