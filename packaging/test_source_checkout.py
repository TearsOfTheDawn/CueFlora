import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import source_export
import verify_source_checkout


class CleanSourceCheckoutTests(unittest.TestCase):
    def fixture(self, root):
        source = root/'source'; source.mkdir()
        (source/'LICENSE.md').write_text('Synthetic test licence\n', encoding='utf-8')
        (source/'package.json').write_text('{"name":"synthetic-fixture"}\n', encoding='utf-8')
        (source/'native').mkdir()
        return source

    def test_actual_source_export_and_commands_use_clean_child_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = self.fixture(root); output = root/'verification'
            poison = {name:'synthetic-do-not-propagate' for name in ('PYTHONPATH','PYTHONHOME','PYTHONSTARTUP',
                'PYTHONUSERBASE','NODE_PATH','NODE_OPTIONS','CUEFLORA_PROVIDER_CONFIG','CUEFLORA_EVIDENCE_DIR',
                'YT_DLP_PATH','FFMPEG_PATH','FFPROBE_PATH','DENO_PATH','CUEFLORA_PUBLIC_CONFIG','CUEFLORA_BUILD_PROFILE')}
            with patch.dict(os.environ, poison), patch.object(verify_source_checkout, 'export',
                    side_effect=lambda path: source_export.export(path, source)), patch.object(
                    verify_source_checkout.subprocess, 'run', return_value=SimpleNamespace(returncode=0)) as command:
                report = verify_source_checkout.verify(root/'cache', output)
                self.assertTrue(report['passed'])
                self.assertEqual(len(report['checks']), 8)
                self.assertEqual(report['sourceArchiveSha256'], json.loads((output/'export/source-audit.json').read_text())['archiveSha256'])
                self.assertFalse(report['gitHistoryRequired'])
                self.assertFalse(report['privateInputsRequired'])
                for call in command.call_args_list:
                    environment = call.kwargs['env']
                    self.assertTrue(set(poison).isdisjoint(environment))
                    self.assertEqual(environment['PYTHONNOUSERSITE'], '1')
                    self.assertIn(call.kwargs['cwd'], (output/'checkout', output/'checkout/native'))
                self.assertEqual(os.environ['NODE_OPTIONS'], poison['NODE_OPTIONS'])

    def test_first_failed_command_records_failure_without_running_later_steps(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = self.fixture(root); output = root/'verification'
            with patch.object(verify_source_checkout, 'export', side_effect=lambda path: source_export.export(path, source)), patch.object(
                    verify_source_checkout.subprocess, 'run', return_value=SimpleNamespace(returncode=1)) as command:
                with self.assertRaises(ValueError): verify_source_checkout.verify(root/'cache', output)
                self.assertEqual(command.call_count, 1)
                report = json.loads((output/'clean-source-verification.json').read_text())
                self.assertFalse(report['passed'])
                self.assertEqual(report['checks'][0]['exitCode'], 1)
