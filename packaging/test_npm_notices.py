import json
from pathlib import Path
import tempfile
import unittest
from npm_notices import ROOT, supplemental_notices


class NpmNoticeTests(unittest.TestCase):
    def test_original_release_notice_has_exact_hash_and_package_identity(self):
        notice, = supplemental_notices('wxt', '0.21.4')
        self.assertEqual(notice['sha256'], '7b0b00fcdbc6a036078aad84d0bc0fae240ac67144b86c911149c2daa37c9f85')
        self.assertIn(b'Copyright (c) 2023 Aaron', notice['path'].read_bytes())
        with self.assertRaisesRegex(ValueError, 'identity'): supplemental_notices('wxt', '0.20.20')
        self.assertEqual(supplemental_notices('unlisted-package', '1.0.0'), [])

    def test_missing_identity_changed_notice_and_unsafe_paths_fail(self):
        original = json.loads((ROOT/'packaging/npm-notices.lock.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'packaging/notices').mkdir(parents=True)
            (root/'packaging/npm-notices.lock.json').write_text(json.dumps(original))
            (root/'package-lock.json').write_text('{"packages":{}}')
            with self.assertRaisesRegex(ValueError, 'identity'): supplemental_notices('wxt', '0.21.4', root)
            item=original['packages'][0]
            (root/'package-lock.json').write_text(json.dumps({'packages':{'node_modules/wxt':{'version':item['version'],'integrity':item['integrity']}}}))
            (root/'packaging/notices'/item['file']).write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'hash'): supplemental_notices('wxt', '0.21.4', root)
            for name in ('../LICENSE', '.', '..'):
                item['file']=name
                (root/'packaging/npm-notices.lock.json').write_text(json.dumps(original))
                with self.assertRaisesRegex(ValueError, 'identity'): supplemental_notices('wxt', '0.21.4', root)
