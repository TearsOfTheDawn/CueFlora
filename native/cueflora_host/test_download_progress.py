import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import httpx
from .owned_process import OwnedProcess
from .download import _consume_download
from .whisper import _post_transcription


class DownloadProgressTests(unittest.TestCase):
    def child(self,script):return OwnedProcess([sys.executable,'-c',script],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    def test_both_streams_are_drained_and_advancing_download_does_not_stall(self):
        script="import sys,time;[(sys.stdout.write('x'*100+'\\n'),sys.stdout.flush(),sys.stderr.write('cueflora_progress:'+str(i)+'|20|2048\\n'),sys.stderr.flush(),time.sleep(.01)) for i in range(20)]"
        progress=[]
        with patch('cueflora_host.download._send_on_real_stdout',side_effect=progress.append):
            output=_consume_download(self.child(script),'job',inactivity=2,overall=5)
        self.assertEqual(len(output),20);self.assertGreater(len(progress),0)
        self.assertIn('KiB/s',progress[-1]['speed'])
    def test_cancellation_inactivity_and_overall_limits_close_owned_tree(self):
        for mode in ('cancel','inactivity','overall'):
            owned=self.child('import time;time.sleep(30)');cancel=threading.Event()
            if mode=='cancel':cancel.set()
            with self.assertRaises(RuntimeError):_consume_download(owned,'job',cancel,inactivity=0 if mode=='inactivity' else 10,overall=0 if mode=='overall' else 10)
            self.assertIsNotNone(owned.process.poll())
    def test_errors_are_bounded_and_media_urls_are_redacted(self):
        owned=self.child("import sys;print('failure https://fixture.invalid/signed?key=synthetic',file=sys.stderr);sys.exit(2)")
        with self.assertRaises(RuntimeError) as raised:_consume_download(owned,'job')
        self.assertNotIn('signed',str(raised.exception));self.assertLess(len(str(raised.exception)),1700)
    def test_frozen_tools_ignore_global_overrides_but_allow_namespaced_opt_in(self):
        from .runtime_tools import packaged_tool
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'tools').mkdir();tool=root/'tools'/('ffmpeg.exe' if os.name=='nt' else 'ffmpeg');tool.touch()
            override=root/'alternative.exe';override.touch()
            with patch('sys.frozen',True,create=True),patch('sys.executable',str(root/'host.exe')),patch.dict('os.environ',{'FFMPEG_PATH':'unrelated-invalid-global'},clear=True):
                self.assertEqual(packaged_tool('ffmpeg'),str(tool))
                with patch.dict('os.environ',{'CUEFLORA_DEV_FFMPEG_PATH':str(override)}):self.assertEqual(packaged_tool('ffmpeg'),str(override))
    def test_upload_body_stays_exact_and_waiting_stage_follows_upload(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.ogg';path.write_bytes(b'exact synthetic audio bytes')
            stages=[];calls=[]
            def handler(request):calls.append(request);return httpx.Response(200,json={'text':'synthetic'})
            client=httpx.Client(transport=httpx.MockTransport(handler))
            with patch('cueflora_host.whisper.httpx.Client',return_value=client):
                _post_transcription(str(path),'https://fixture.invalid/audio/transcriptions',{}, {},'audio/ogg',1,on_progress=lambda stage,message:stages.append(stage))
            self.assertEqual(stages,['upload','transcribe']);self.assertIn(path.read_bytes(),calls[0].content)


if __name__=='__main__':unittest.main()
