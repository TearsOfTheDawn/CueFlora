import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from runtime_notices import collect_interpreter_notices


class NoticeTests(unittest.TestCase):
    def test_available_and_missing_notices_are_distinguished(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'LICENSE.txt').write_text('fixture notice')
            bundle = root / 'bundle'
            with patch('runtime_notices.sys.base_prefix', str(root)):
                collect_interpreter_notices(bundle)
            records = json.loads((bundle / 'licenses/interpreter/notice-inventory.json').read_text())
            self.assertEqual([r['noticeFound'] for r in records], [True, False, False])
            self.assertTrue(all(r['redistributionApproved'] is False for r in records))
            self.assertEqual((bundle / records[0]['file']).read_text(), 'fixture notice')
