from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from .runtime_tools import packaged_tool


class RuntimeToolTests(unittest.TestCase):
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
