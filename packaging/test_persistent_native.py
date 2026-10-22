import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
from persistent_native import exchange
from probe_runtime import probe


class PersistentNativeTests(unittest.TestCase):
    def test_two_frames_are_answered_before_stdin_is_closed(self):
        script = """
import sys,json,struct
for _ in range(2):
    header=sys.stdin.buffer.read(4)
    if len(header)!=4:sys.exit(6)
    size=struct.unpack('<I',header)[0]
    value=json.loads(sys.stdin.buffer.read(size))
    assert value=={'type':'PING'}
    raw=json.dumps({'status':'PONG'}).encode()
    sys.stdout.buffer.write(struct.pack('<I',len(raw))+raw);sys.stdout.buffer.flush()
assert sys.stdin.buffer.read()==b''
"""
        replies,timings=exchange([sys.executable,'-u','-c',script],[{'type':'PING'},{'type':'PING'}],timeout=5)
        self.assertEqual(replies,[{'status':'PONG'},{'status':'PONG'}])
        self.assertEqual(len(timings),2)

    def test_truncated_oversized_and_missing_responses_are_bounded(self):
        scripts=["import sys;sys.stdout.buffer.write(b'xx');sys.stdout.buffer.flush()",
                 "import sys,struct;sys.stdout.buffer.write(struct.pack('<I',1024*1024+1));sys.stdout.buffer.flush()",
                 "import time;time.sleep(10)"]
        for script in scripts:
            with self.subTest(script=script),self.assertRaises(RuntimeError):
                exchange([sys.executable,'-u','-c',script],[{'type':'PING'}],timeout=.3)

    def test_runtime_gate_uses_persistent_exchange_and_checks_each_reply(self):
        healthy={'status':'PONG','tools':{name:{'available':True} for name in ('yt-dlp','ffmpeg','ffprobe','deno')}}
        with tempfile.TemporaryDirectory() as directory:
            exe=Path(directory)/'host.exe';exe.write_bytes(b'synthetic')
            with patch('probe_runtime.exchange',return_value=([healthy,healthy],[1,1])) as call:
                result=probe(exe,repeats=1)
                self.assertTrue(result['persistentPort'])
                self.assertEqual(call.call_args.args[1],[{'type':'PING'},{'type':'PING'}])
            with patch('probe_runtime.exchange',return_value=([healthy,{'status':'bad'}],[1,1])):
                with self.assertRaises(RuntimeError):probe(exe,repeats=1)
