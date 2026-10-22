from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from .runtime_tools import packaged_tool
from .tool_process import tool_process_options
import ast
import os
import subprocess
import sys


class RuntimeToolTests(unittest.TestCase):
    def test_external_tools_and_setup_are_disconnected_from_control_streams(self):
        self.assertEqual(tool_process_options()['stdin'], subprocess.DEVNULL)
        detached=tool_process_options(detach_output=True)
        for stream in ('stdin','stdout','stderr'):
            self.assertEqual(detached[stream],subprocess.DEVNULL)
        if os.name=='nt':self.assertEqual(detached['creationflags'],subprocess.CREATE_NO_WINDOW)

    def test_every_native_audio_tool_call_uses_isolated_input(self):
        root=Path(__file__).parent
        for name in ('download.py','runtime_tools.py','whisper.py'):
            tree=ast.parse((root/name).read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Attribute):continue
                if not isinstance(node.func.value,ast.Name) or node.func.value.id!='subprocess' or node.func.attr not in ('run','check_output'):continue
                with self.subTest(file=name,line=node.lineno):
                    self.assertTrue(any(isinstance(item.value,ast.Call) and isinstance(item.value.func,ast.Name)
                        and item.value.func.id=='tool_process_options' for item in node.keywords))

    def test_owned_download_child_has_eof_without_reading_parent_input(self):
        from .owned_process import OwnedProcess
        owned=OwnedProcess([sys.executable,'-c','import sys;print(len(sys.stdin.buffer.read()))'],
                           stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            stdout,stderr=owned.process.communicate(timeout=5)
            self.assertEqual(owned.process.returncode,0)
            self.assertEqual(stdout.strip(),b'0')
            self.assertEqual(stderr,b'')
        finally:owned.close()

    def test_frozen_bundle_never_falls_back_to_path(self):
        with tempfile.TemporaryDirectory() as directory, patch('sys.frozen', True, create=True), \
                patch('sys.executable', str(Path(directory) / 'cueflora-host.exe')), patch.dict('os.environ', {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'Bundled ffmpeg'):
                packaged_tool('ffmpeg')
            tools = Path(directory) / 'tools'
            tools.mkdir()
            name = 'ffmpeg.exe' if __import__('os').name == 'nt' else 'ffmpeg'
            (tools / name).touch()
            self.assertEqual(packaged_tool('ffmpeg'), str(tools / name))

    def test_explicit_override_is_absolute_and_invalid_override_fails(self):
        with patch.dict('os.environ', {'FFMPEG_PATH': 'relative.exe'}):
            with self.assertRaisesRegex(RuntimeError, 'override'):
                packaged_tool('ffmpeg')
