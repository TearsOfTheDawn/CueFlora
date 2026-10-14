from pathlib import Path
import tempfile
import unittest
import zipfile
from source_export import inventory, export, source_identity


class SourceExportTests(unittest.TestCase):
    def test_source_identity_does_not_depend_on_json_pretty_format_or_order(self):
        self.assertEqual(source_identity({'b':'b'*64,'a':'a'*64}),source_identity({'a':'a'*64,'b':'b'*64}))

    def fixture(self, root):
        (root/'LICENSE.md').write_text('MIT notice')
        (root/'README.md').write_text('Public source')
        (root/'native').mkdir()

    def test_actual_untracked_sources_and_no_environment_capture_or_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.fixture(root)
            (root/'native/new.py').write_text('print("source")')
            (root/'native/.venv').mkdir(); (root/'native/.venv/secret.txt').write_text('not public')
            (root/'artifacts').mkdir(); (root/'artifacts/private.json').write_text('not public')
            records, issues = inventory(root)
            self.assertFalse(issues); self.assertIn('native/new.py', records)
            self.assertNotIn('native/.venv/secret.txt', records)
            report = export(root/'export',root)
            with zipfile.ZipFile(root/'export/CueFlora-source.zip') as package:
                self.assertEqual(set(package.namelist()),set(records))
            self.assertTrue(report['passed'])

    def test_reports_paths_not_secret_contents_and_refuses_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.fixture(root)
            (root/'native/key.py').write_text('token = "'+'sk-'+'Z'*32+'"')
            (root/'native/capture.wav').write_bytes(b'private')
            _, issues = inventory(root)
            self.assertEqual({item['reason'] for item in issues},{'possible-secret','binary-media-or-generated-file'})
            self.assertNotIn('Z'*32,str(issues))
            with self.assertRaises(ValueError): export(root/'export',root)
            self.assertFalse((root/'export/CueFlora-source.zip').exists())
