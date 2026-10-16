import hashlib
from pathlib import Path
import tempfile
import unittest
from prepare_windows import ROOT, copy_extension_sources
from npm_notices import supplemental_notices


class ExtensionWorkspaceTests(unittest.TestCase):
    def test_real_isolated_workspace_retains_plugin_inputs_and_exact_notices(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace=Path(directory)/'extension'
            copy_extension_sources(ROOT,workspace)
            for name in ('package-lock.json','scripts/build-profile.mjs','scripts/npm-notices.mjs',
                    'packaging/npm-notices.lock.json','packaging/notices/wxt-0.21.4-LICENSE.txt'):
                self.assertEqual(hashlib.sha256((workspace/name).read_bytes()).digest(),
                    hashlib.sha256((ROOT/name).read_bytes()).digest())
            notice,=supplemental_notices('wxt','0.21.4',workspace)
            self.assertEqual(notice['sha256'],'7b0b00fcdbc6a036078aad84d0bc0fae240ac67144b86c911149c2daa37c9f85')
            for name in ('artifacts','.git','node_modules','.packaging-venv'):
                self.assertFalse((workspace/name).exists())

    def test_missing_source_input_is_not_silently_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'incomplete'; root.mkdir()
            with self.assertRaises(FileNotFoundError): copy_extension_sources(root,Path(directory)/'output')
