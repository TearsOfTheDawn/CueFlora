"""Only terminate the process tree started by this invocation, never by image name."""
import os
import signal
import subprocess


class OwnedProcess:
    def __init__(self, command, **kwargs):
        self.job = None
        if os.name == 'nt':
            import ctypes
            from ctypes import wintypes
            class Basic(ctypes.Structure):
                _fields_ = [('user', ctypes.c_int64), ('job', ctypes.c_int64), ('flags', wintypes.DWORD),
                            ('min', ctypes.c_size_t), ('max', ctypes.c_size_t), ('active', wintypes.DWORD),
                            ('affinity', ctypes.c_size_t), ('priority', wintypes.DWORD), ('scheduling', wintypes.DWORD)]
            class IO(ctypes.Structure):
                _fields_ = [(name, ctypes.c_uint64) for name in ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]
            class Limits(ctypes.Structure):
                _fields_ = [('basic', Basic), ('io', IO), ('process_memory', ctypes.c_size_t),
                            ('job_memory', ctypes.c_size_t), ('peak_process', ctypes.c_size_t), ('peak_job', ctypes.c_size_t)]
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
            kernel.CreateJobObjectW.restype = wintypes.HANDLE
            kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
            kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            self.kernel = kernel
            self.job = kernel.CreateJobObjectW(None, None)
            limits = Limits(); limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not self.job or not kernel.SetInformationJobObject(self.job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
                self.close(); raise RuntimeError('Cannot create owned download process group')
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW | 0x4  # CREATE_SUSPENDED: no child can escape before job assignment.
        else:
            kwargs['start_new_session'] = True
        try:
            self.process = subprocess.Popen(command, **kwargs)
            if os.name == 'nt' and not self.kernel.AssignProcessToJobObject(self.job, int(self.process._handle)):
                self.process.kill(); self.process.wait(timeout=5)
                raise RuntimeError('Cannot isolate owned download process group')
            if os.name=='nt':
                # Resume the single initial thread using documented Toolhelp/Thread APIs.
                class ThreadEntry(ctypes.Structure):
                    _fields_=[('size',wintypes.DWORD),('usage',wintypes.DWORD),('tid',wintypes.DWORD),('owner',wintypes.DWORD),('priority',wintypes.LONG),('delta',wintypes.LONG),('flags',wintypes.DWORD)]
                kernel.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD];kernel.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
                kernel.Thread32First.argtypes=[wintypes.HANDLE,ctypes.POINTER(ThreadEntry)];kernel.Thread32Next.argtypes=kernel.Thread32First.argtypes
                kernel.OpenThread.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenThread.restype=wintypes.HANDLE
                kernel.ResumeThread.argtypes=[wintypes.HANDLE];kernel.ResumeThread.restype=wintypes.DWORD
                snapshot=kernel.CreateToolhelp32Snapshot(4,0);resumed=False
                if snapshot==wintypes.HANDLE(-1).value:raise RuntimeError('Cannot inspect owned initial thread')
                try:
                    entry=ThreadEntry();entry.size=ctypes.sizeof(entry);present=kernel.Thread32First(snapshot,ctypes.byref(entry))
                    while present:
                        if entry.owner==self.process.pid:
                            thread=kernel.OpenThread(2,False,entry.tid)
                            if not thread:raise RuntimeError('Cannot resume owned initial thread')
                            try:resumed=kernel.ResumeThread(thread)!=0xffffffff
                            finally:kernel.CloseHandle(thread)
                            break
                        present=kernel.Thread32Next(snapshot,ctypes.byref(entry))
                finally:kernel.CloseHandle(snapshot)
                if not resumed:raise RuntimeError('Cannot resume owned download process')
        except BaseException:
            self.close(); raise

    def close(self):
        if self.job:
            self.kernel.CloseHandle(self.job); self.job = None
        elif hasattr(self, 'process') and os.name != 'nt':
            try: os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
        if hasattr(self, 'process'):
            try: self.process.wait(timeout=5)
            except subprocess.TimeoutExpired: self.process.kill(); self.process.wait(timeout=5)
