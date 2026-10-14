import io
from pathlib import Path
import tempfile
import unittest
import zipfile
from verify_two_builds import verify,zip_members


class TwoBuildTests(unittest.TestCase):
    def test_extra_member_or_changed_nonmetadata_bytes_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); first=root/'first'; second=root/'second'; first.mkdir(); second.mkdir()
            (first/'tool.exe').write_bytes(b'original'); (second/'tool.exe').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'Unexplained'): verify(first,second,root/'a',root/'b')
            (second/'extra').write_bytes(b'extra')
            with self.assertRaisesRegex(ValueError,'membership'): verify(first,second,root/'a',root/'b')

    def test_zip_order_is_ignored_but_member_content_and_duplicates_are_not(self):
        first,second=io.BytesIO(),io.BytesIO()
        with zipfile.ZipFile(first,'w') as archive: archive.writestr('a',b'a'); archive.writestr('b',b'b')
        with zipfile.ZipFile(second,'w') as archive: archive.writestr('b',b'b'); archive.writestr('a',b'a')
        self.assertEqual(zip_members(first.getvalue()),zip_members(second.getvalue()))
        changed=io.BytesIO()
        with zipfile.ZipFile(changed,'w') as archive: archive.writestr('a',b'changed'); archive.writestr('b',b'b')
        self.assertNotEqual(zip_members(first.getvalue()),zip_members(changed.getvalue()))
