import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch, Mock
from .runtime_tools import packaged_tool, resolve_deno, download_runtime_options, download_process_environment


class DenoTests(unittest.TestCase):
    def test_packaged_download_cannot_inherit_permission_broker_authority(self):
        original={'DENO_PERMISSION_BROKER_PATH':'synthetic-pipe',
            'deno_permission_broker_path':'synthetic-lowercase',
            'PATH':'synthetic-path','HTTPS_PROXY':'https://proxy.example.invalid',
            'SSL_CERT_FILE':'synthetic-certificate','DENO_PATH':'C:/explicit/deno.exe'}
        with patch.object(sys,'frozen',True,create=True),patch.dict('os.environ',original,clear=True):
            result=download_process_environment()
            self.assertFalse(any(name.upper()=='DENO_PERMISSION_BROKER_PATH' for name in result))
            for name in ('PATH','HTTPS_PROXY','SSL_CERT_FILE','DENO_PATH'):
                self.assertEqual(result[name],original[name])

    def test_unfrozen_developer_broker_is_retained_in_an_independent_copy(self):
        with patch.object(sys,'frozen',False,create=True),patch.dict('os.environ',
                {'DENO_PERMISSION_BROKER_PATH':'synthetic-pipe'},clear=True):
            result=download_process_environment()
            self.assertEqual(result['DENO_PERMISSION_BROKER_PATH'],'synthetic-pipe')
            result.clear()
            self.assertEqual(download_process_environment()['DENO_PERMISSION_BROKER_PATH'],'synthetic-pipe')

    def test_production_download_passes_the_isolated_environment_to_yt_dlp(self):
        from .download import download_audio
        with tempfile.TemporaryDirectory() as temporary,patch.object(sys,'frozen',True,create=True),\
                patch.dict('os.environ',{'DENO_PERMISSION_BROKER_PATH':'synthetic-pipe'},clear=True),\
                patch('cueflora_host.download._resolve_yt_dlp_executable',return_value='synthetic-ytdlp'),\
                patch('cueflora_host.download.download_runtime_options',return_value=[]),\
                patch('cueflora_host.download._real_stdout',None),\
                patch('cueflora_host.download.subprocess.Popen',side_effect=FileNotFoundError) as launch:
            with self.assertRaises(RuntimeError): download_audio('abcdefghijk',temporary)
            self.assertNotIn('DENO_PERMISSION_BROKER_PATH',launch.call_args.kwargs['env'])
            self.assertIn('worstaudio',launch.call_args.args[0])

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
