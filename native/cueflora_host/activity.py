"""Crash-released cross-profile Run leases and an exclusive installation gate."""
from contextlib import contextmanager
import os
from pathlib import Path
import re
import threading
import uuid
from .account_store import safe_directory

_lock=threading.RLock()


def _acquire(stream):
    stream.seek(0,2)
    if stream.tell()==0:stream.write(b'0');stream.flush()
    stream.seek(0)
    if os.name=='nt':
        import msvcrt
        msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
    else:
        import fcntl
        fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)


def _release(stream):
    stream.seek(0)
    if os.name=='nt':
        import msvcrt
        msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
    else:
        import fcntl
        fcntl.flock(stream.fileno(),fcntl.LOCK_UN)


def root_directory():
    if os.name!='nt' or not os.environ.get('LOCALAPPDATA'):raise RuntimeError('Windows activity tracking unavailable')
    return Path(os.environ['LOCALAPPDATA'])/'CueFlora'


def assert_no_native_jobs(root):
    """Also identify pre-0.2 installed hosts, which did not hold Run leases."""
    if os.name!='nt':return
    import ctypes
    from ctypes import wintypes
    class ProcessEntry(ctypes.Structure):
        _fields_=[('size',wintypes.DWORD),('usage',wintypes.DWORD),('pid',wintypes.DWORD),('heap',ctypes.c_size_t),
            ('module',wintypes.DWORD),('threads',wintypes.DWORD),('parent',wintypes.DWORD),('priority',wintypes.LONG),
            ('flags',wintypes.DWORD),('name',wintypes.WCHAR*260)]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD];kernel.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
    kernel.Process32FirstW.argtypes=[wintypes.HANDLE,ctypes.POINTER(ProcessEntry)];kernel.Process32NextW.argtypes=kernel.Process32FirstW.argtypes
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    snapshot=kernel.CreateToolhelp32Snapshot(2,0)
    if snapshot==wintypes.HANDLE(-1).value:raise RuntimeError('Cannot verify CueFlora native activity. Close CueFlora and retry Setup.')
    try:
        entry=ProcessEntry();entry.size=ctypes.sizeof(entry);available=kernel.Process32FirstW(snapshot,ctypes.byref(entry))
        while available:
            if entry.pid!=os.getpid() and entry.name.casefold()=='cueflora-host.exe':
                process=kernel.OpenProcess(0x1000,False,entry.pid)
                if not process:raise RuntimeError('Cannot verify a running CueFlora helper. Close it before Setup.')
                try:
                    buffer=ctypes.create_unicode_buffer(32768);size=wintypes.DWORD(len(buffer))
                    if not kernel.QueryFullProcessImageNameW(process,0,buffer,ctypes.byref(size)):raise RuntimeError('Cannot verify a running CueFlora helper. Close it before Setup.')
                    if Path(buffer.value).resolve().is_relative_to(Path(root).resolve()/'versions'):raise RuntimeError('A CueFlora helper is still running. Finish or cancel all Runs and account tasks, then retry Setup.')
                finally:kernel.CloseHandle(process)
            available=kernel.Process32NextW(snapshot,ctypes.byref(entry))
    finally:kernel.CloseHandle(snapshot)


@contextmanager
def activity_gate(root,install=False):
    with _lock:
        root=safe_directory(root);path=root/'.activity.lock'
        if path.is_symlink():raise RuntimeError('Unsafe CueFlora activity lock')
        with path.open('a+b') as stream:
            try:_acquire(stream)
            except OSError:raise RuntimeError('CueFlora is starting a Run or installing. Retry shortly.') from None
            try:
                leases=root/'activity'
                if install and leases.exists():
                    safe_directory(leases)
                    for entry in leases.iterdir():
                        if not re.fullmatch(r'[0-9a-f]{32}\.lease',entry.name) or entry.is_symlink() or not entry.is_file():raise RuntimeError('Unsafe CueFlora activity record')
                        with entry.open('r+b') as lease:
                            try:_acquire(lease)
                            except OSError:raise RuntimeError('A CueFlora Run is still active in a tab, profile or helper. Finish or cancel it before installing.') from None
                            _release(lease)
                yield
            finally:_release(stream)


class RunLease:
    def __init__(self,root=None):self.root=Path(root) if root is not None else root_directory();self.stream=None
    def __enter__(self):
        with activity_gate(self.root):
            folder=safe_directory(self.root/'activity');self.path=folder/(uuid.uuid4().hex+'.lease')
            self.stream=self.path.open('x+b');_acquire(self.stream)
        return self
    def __exit__(self,*_):
        if self.stream:
            _release(self.stream);self.stream.close();self.stream=None
            # Only this process's exact created lease is removed.
            self.path.unlink(missing_ok=True)
