import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch, Mock
from .runtime_tools import packaged_tool, resolve_deno, download_runtime_options


class DenoTests(unittest.TestCase):
    def test_missing_frozen_deno_fails_without_path_fallback(self):
        with tempfile.TemporaryDirectory() as root, patch.object(sys, 'frozen', True, create=True), patch.object(sys, 'executable', str(Path(root) / 'host.exe')), patch.dict('os.environ', {}, clear=True), patch('shutil.which') as which:
            with self.assertRaisesRegex(RuntimeError, 'Bundled deno'):
                resolve_deno()
            which.assert_not_called()

    def test_frozen_download_selects_explicit_deno_and_disables_remote_components(self):
        with patch.object(sys, 'frozen', True, create=True), patch('cueflora_host.runtime_tools.resolve_deno', return_value='C:/Unicode Ω/tools/deno.exe'):
            options = download_runtime_options()
            self.assertIn('--no-remote-components', options)
            self.assertIn('--no-js-runtimes', options)
            self.assertIn('--ignore-config', options)
            self.assertIn('--no-plugin-dirs', options)
            self.assertEqual(options[-1], 'deno:C:/Unicode Ω/tools/deno.exe')

    def test_invalid_override_never_substitutes_path(self):
        with patch.dict('os.environ', {'DENO_PATH': 'relative.exe'}):
            with self.assertRaisesRegex(RuntimeError, 'override'):
                packaged_tool('deno')

    def test_unrunnable_or_unsupported_deno_fails(self):
        with patch('cueflora_host.runtime_tools.packaged_tool', return_value='deno.exe'), patch('subprocess.run', return_value=Mock(returncode=0, stdout='deno 1.0')):
            with self.assertRaisesRegex(RuntimeError, '2.3.0'):
                resolve_deno()
        with patch('cueflora_host.runtime_tools.packaged_tool', return_value='deno.exe'), patch('subprocess.run', side_effect=subprocess.TimeoutExpired('deno', 5)):
            with self.assertRaisesRegex(RuntimeError, 'cannot run'):
                resolve_deno()

    def test_healthy_version_is_metadata_only(self):
        with patch('cueflora_host.runtime_tools.packaged_tool', return_value='deno.exe'), patch('subprocess.run', return_value=Mock(returncode=0, stdout='deno 2.9.7')) as run:
            self.assertEqual(resolve_deno(), 'deno.exe')
            self.assertEqual(run.call_args.args[0], ['deno.exe', '--version'])
