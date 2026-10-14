"""User-scoped, non-interactive Windows DPAPI; no plaintext persistence/fallback."""
import base64
import ctypes
import hashlib
import json
import os
from .provider_security import normalize_endpoint

METHOD = 'windows-dpapi-v1'
MAX_BLOB = 100000


def _context(stage, endpoint):
    if stage not in ('transcription', 'translation'):
        raise ValueError('Invalid credential stage')
    return {'schema': 1, 'product': 'cueflora', 'stage': stage, 'endpoint': normalize_endpoint(endpoint)}


def _crypt(data, entropy, decrypt=False):
    if os.name != 'nt':
        raise RuntimeError('Windows credential protection unavailable; use the Windows helper')

    class Blob(ctypes.Structure):
        _fields_ = [('size', ctypes.c_ulong), ('data', ctypes.POINTER(ctypes.c_ubyte))]

    source_buffer = ctypes.create_string_buffer(data)
    entropy_buffer = ctypes.create_string_buffer(entropy)
    source = Blob(len(data), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_ubyte)))
    context = Blob(len(entropy), ctypes.cast(entropy_buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    free = kernel.LocalFree
    free.argtypes = [ctypes.c_void_p]
    free.restype = ctypes.c_void_p
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.POINTER(Blob), ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(Blob)]
    function.restype = ctypes.c_int
    try:
        # UI_FORBIDDEN only. Never LOCAL_MACHINE or a prompt structure.
        if not function(ctypes.byref(source), None, ctypes.byref(context), None, None, 1, ctypes.byref(output)):
            raise RuntimeError('Windows credential protection failed; re-enter the key or repair the helper')
        if output.size > MAX_BLOB:
            raise ValueError('Invalid credential size')
        return ctypes.string_at(output.data, output.size)
    finally:
        ctypes.memset(source_buffer, 0, len(source_buffer))
        if output.data:
            ctypes.memset(output.data, 0, output.size)
            free(output.data)


def _entropy(context):
    return hashlib.sha256(json.dumps(context, sort_keys=True).encode()).digest()


def protect(key, stage, endpoint):
    if not isinstance(key, str) or not key or len(key) > 8192:
        raise ValueError('Invalid API key')
    context = _context(stage, endpoint)
    payload = json.dumps({**context, 'key': key}, ensure_ascii=False).encode('utf-8')
    encrypted = _crypt(payload, _entropy(context))
    result = {'schema': 1, 'method': METHOD, 'blob': base64.b64encode(encrypted).decode('ascii')}
    # Verify the replacement before allowing the browser to persist it.
    if unprotect(result, stage, endpoint) != key:
        raise RuntimeError('Windows credential verification failed')
    return result


def unprotect(credential, stage, endpoint):
    context = _context(stage, endpoint)
    if not isinstance(credential, dict) or set(credential) != {'schema', 'method', 'blob'} or credential.get('schema') != 1 or credential.get('method') != METHOD:
        raise ValueError('Invalid protected credential')
    blob = credential.get('blob')
    if not isinstance(blob, str) or not blob or len(blob) > MAX_BLOB:
        raise ValueError('Invalid protected credential')
    try:
        raw = base64.b64decode(blob, validate=True)
        payload = json.loads(_crypt(raw, _entropy(context), decrypt=True))
        if not isinstance(payload, dict) or set(payload) != {*context, 'key'} or any(payload.get(k) != v for k, v in context.items()):
            raise ValueError('Credential context mismatch')
        key = payload.get('key')
        if not isinstance(key, str) or not key or len(key) > 8192:
            raise ValueError('Invalid protected key')
        return key
    except Exception:
        raise ValueError('Protected key cannot be opened; re-enter it or repair the Windows helper') from None


def resolve_key(provider, stage):
    if provider.get('credential') is not None:
        if provider.get('apiKey'):
            raise ValueError('Ambiguous credential input')
        return unprotect(provider['credential'], stage, provider.get('baseUrl'))
    # A newly typed metadata-check key or explicit development CLI input exists
    # only in memory. Production saved providers always use protected blobs.
    key = provider.get('apiKey', '')
    if not isinstance(key, str) or len(key) > 8192:
        raise ValueError('Invalid API key')
    return key


def handle_protect(message):
    try:
        stage, endpoint = message.get('stage'), message.get('baseUrl')
        if message.get('credential') is not None:
            key = unprotect(message['credential'], stage, message.get('previousBaseUrl'))
        else:
            key = message.get('apiKey')
        return {'requestId': message.get('requestId'), 'credential': protect(key, stage, endpoint)}
    except Exception:
        return {'requestId': message.get('requestId'), 'error': 'Windows key protection failed or is unavailable. Upgrade/Repair CueFlora or re-enter the key; no plaintext was saved.'}


def redact(value, *secrets):
    text = str(value)
    for secret in secrets:
        if isinstance(secret, str) and secret:
            text = text.replace(secret, '[redacted]')
    return text
