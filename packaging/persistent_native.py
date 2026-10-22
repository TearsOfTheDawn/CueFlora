"""Persistent native ports must be exercised before input is closed."""
import json
import os
import queue
import struct
import subprocess
import threading
import time


def exchange(command, requests, *, env=None, cwd=None, timeout=45):
    """Bounded framed exchanges; leave stdin open through every response."""
    options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, env=env, cwd=cwd, **options)
    replies = queue.Queue()
    def exact(size):
        data = bytearray()
        while len(data) < size:
            chunk = process.stdout.read(size-len(data))
            if not chunk:
                raise ValueError('Truncated persistent native response')
            data.extend(chunk)
        return bytes(data)
    def read():
        try:
            for _ in requests:
                size = struct.unpack('<I', exact(4))[0]
                if size > 1024*1024:
                    raise ValueError('Oversized persistent native response')
                value = json.loads(exact(size))
                if not isinstance(value, dict):
                    raise ValueError('Invalid persistent native response')
                replies.put(value)
        except Exception as error:
            replies.put(error)
    # Drain stderr without retaining arbitrary errors, paths or provider data.
    def drain():
        while process.stderr.read(4096):
            pass
    reader = threading.Thread(target=read, daemon=True)
    stderr = threading.Thread(target=drain, daemon=True)
    reader.start(); stderr.start()
    responses=[]; timings=[]
    try:
        for request in requests:
            started=time.monotonic()
            raw=json.dumps(request).encode()
            process.stdin.write(struct.pack('<I',len(raw))+raw); process.stdin.flush()
            try:
                value=replies.get(timeout=timeout)
            except queue.Empty:
                raise RuntimeError('Persistent native response timed out') from None
            if isinstance(value, Exception):
                raise RuntimeError('Invalid persistent native protocol response') from None
            responses.append(value); timings.append(round((time.monotonic()-started)*1000,2))
        process.stdin.close()
        process.wait(timeout=5)
        if process.returncode:
            raise RuntimeError('Persistent native host exited unsuccessfully')
        reader.join(timeout=1); stderr.join(timeout=1)
        if process.stdout.read(1):
            raise RuntimeError('Unrequested bytes in persistent native protocol')
        return responses,timings
    finally:
        if process.poll() is None:
            process.kill(); process.wait(timeout=5)
        for stream in (process.stdin,process.stdout,process.stderr):
            if stream and not stream.closed:
                stream.close()
        reader.join(timeout=1); stderr.join(timeout=1)
