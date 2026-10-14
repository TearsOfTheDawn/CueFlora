import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from verify_archive import verify_archive


class ArchiveTests(unittest.TestCase):
    def test_inventory_and_failure_cases(self):
        with tempfile.TemporaryDirectory() as folder:
            for variant in ('valid', 'altered', 'missing', 'extra', 'unsafe'):
                with self.subTest(variant=variant):
                    path = Path(folder) / (variant + '.zip')
                    with zipfile.ZipFile(path, 'w') as archive:
                        archive.writestr('CueFlora Setup/SHA256SUMS.json', json.dumps(
                            {'file': hashlib.sha256(b'original').hexdigest()}))
                        if variant != 'missing':
                            archive.writestr('CueFlora Setup/file', b'changed' if variant == 'altered' else b'original')
                        if variant in ('extra', 'unsafe'):
                            archive.writestr('CueFlora Setup/' + ('../escape' if variant == 'unsafe' else 'extra'), b'x')
                    if variant == 'valid':
                        self.assertEqual(verify_archive(path)['verifiedFiles'], 1)
                    else:
                        with self.assertRaises(ValueError):
                            verify_archive(path)
