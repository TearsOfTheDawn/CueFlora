import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from check_new_whitespace import check_export


class ExportWhitespaceTests(unittest.TestCase):
    def fixture(self,root):
        (root/'LICENSE.md').write_text('Synthetic project licence\n')
        (root/'package.json').write_text('{}\n')
        (root/'packaging/notices').mkdir(parents=True)
        content=b'Original upstream licence retains spaces.  \n'
        (root/'packaging/notices/upstream.txt').write_bytes(content)
        (root/'packaging/inputs-windows.lock.json').write_text(json.dumps({'files':[{'file':'upstream.txt','sha256':hashlib.sha256(content).hexdigest(),'role':'licence-source-evidence'}]}))

    def test_exact_upstream_notice_is_not_rewritten_or_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); self.fixture(root)
            before=(root/'packaging/notices/upstream.txt').read_bytes(); check_export(root)
            self.assertEqual((root/'packaging/notices/upstream.txt').read_bytes(),before)
            (root/'packaging/notices/upstream.txt').write_bytes(before+b'changed')
            with self.assertRaisesRegex(ValueError,'pinned original'): check_export(root)

    def test_ordinary_source_whitespace_is_still_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); self.fixture(root)
            (root/'packaging/example.py').write_text('value = 1  \n')
            with self.assertRaisesRegex(ValueError,'Trailing source'): check_export(root)
