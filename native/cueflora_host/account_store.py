"""Native-only, user-scoped DPAPI account storage. No browser token vault."""
import base64
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import threading
import time
import uuid
from .credentials import _crypt

_thread_lock = threading.RLock()
_entropy = hashlib.sha256(b'CueFlora/native-chatgpt-accounts/v1').digest()


def private_root():
    if os.name != 'nt' or not os.environ.get('LOCALAPPDATA'):
        raise RuntimeError('ChatGPT sign-in requires the Windows CueFlora helper')
    return Path(os.environ['LOCALAPPDATA']) / 'CueFlora' / 'auth'


def safe_directory(root):
    root = Path(root).absolute()
    for candidate in [root, *root.parents]:
        if candidate.is_symlink() or (hasattr(candidate, 'is_junction') and candidate.is_junction()):
            raise RuntimeError('Unsafe CueFlora private storage path')
    root.mkdir(parents=True, exist_ok=True)
    return root


class AccountStore:
    def __init__(self, root=None, crypt=_crypt):
        self.root = Path(root) if root is not None else private_root()
        self.crypt = crypt

    @contextmanager
    def transaction(self):
        with _thread_lock:
            root = safe_directory(self.root)
            lock = root / '.accounts.lock'
            if lock.is_symlink(): raise RuntimeError('Unsafe account lock')
            with lock.open('a+b') as stream:
                if stream.tell() == 0: stream.write(b'0'); stream.flush()
                started = time.monotonic()
                while True:
                    stream.seek(0)
                    try:
                        if os.name == 'nt':
                            import msvcrt
                            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                        else:
                            import fcntl
                            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except OSError:
                        if time.monotonic() - started > 12: raise RuntimeError('ChatGPT session is busy. Retry shortly.') from None
                        time.sleep(0.05)
                try: yield self
                finally:
                    stream.seek(0)
                    if os.name == 'nt':
                        import msvcrt
                        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def read(self):
        path = self.root / 'accounts.dpapi.json'
        if path.is_symlink(): raise RuntimeError('Unsafe account record')
        if not path.exists(): return {'schema':1, 'hostId':'urn:uuid:'+str(uuid.uuid4()), 'accounts':{}}
        if path.stat().st_size > 160000: raise RuntimeError('Invalid account store')
        try:
            record = json.loads(path.read_bytes())
            if record.get('schema') != 1 or record.get('method') != 'windows-dpapi-v1': raise ValueError()
            data = json.loads(self.crypt(base64.b64decode(record['blob'], validate=True), _entropy, decrypt=True))
            if data.get('schema') != 1 or not isinstance(data.get('accounts'), dict) or len(data['accounts']) > 8 or not data.get('hostId','').startswith('urn:uuid:'): raise ValueError()
            for ref in data['accounts']: uuid.UUID(ref)
            return data
        except Exception:
            raise RuntimeError('ChatGPT accounts cannot be opened by this Windows user. Repair or reconnect; no plaintext fallback is used.') from None

    def write(self, data):
        root = safe_directory(self.root)
        plaintext = json.dumps(data, ensure_ascii=False, separators=(',',':')).encode('utf-8')
        if len(plaintext) > 90000: raise RuntimeError('Too many saved ChatGPT accounts')
        blob = self.crypt(plaintext, _entropy)
        if self.crypt(blob, _entropy, decrypt=True) != plaintext: raise RuntimeError('Account protection verification failed')
        target = root / 'accounts.dpapi.json'
        if target.is_symlink(): raise RuntimeError('Unsafe account record')
        temporary = root / ('.pending-'+uuid.uuid4().hex)
        try:
            with temporary.open('xb') as stream:
                stream.write(json.dumps({'schema':1,'method':'windows-dpapi-v1','blob':base64.b64encode(blob).decode('ascii')}).encode('ascii'))
                stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if temporary.exists(): temporary.unlink()

    def public_status(self):
        with self.transaction():
            data = self.read()
            return [{'accountRef':ref, 'label':account['label'], 'connected':bool(account.get('access_token')),
                     'planEnabled':'chatgpt.tokens.use.direct' in account.get('scopes',[])} for ref,account in data['accounts'].items()]
