import tempfile
from pathlib import Path
import unittest
from bundle_sources import bundle


class SourceBundleTests(unittest.TestCase):
    def test_verified_bundle_does_not_approve_partial_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); audio=root/'audio'; audio.mkdir(); evidence=root/'evidence'; evidence.mkdir()
            (audio/'ffmpeg-9.0.2.tar.xz').write_bytes(b'synthetic-source')
            (evidence/'notice.txt').write_text('synthetic notice')
            result=bundle(audio,evidence,root/'output')
            self.assertEqual(result['verifiedMembers'],3)
            self.assertFalse(result['redistributionApproved'])
            self.assertFalse(result['completeCorrespondingSourceClosure'])

    def test_executable_evidence_fails_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); audio=root/'audio'; audio.mkdir(); evidence=root/'evidence'; evidence.mkdir()
            (audio/'ffmpeg-9.0.2.tar.xz').write_bytes(b'synthetic-source'); (evidence/'private.exe').write_bytes(b'not source')
            with self.assertRaises(ValueError): bundle(audio,evidence,root/'output')
            self.assertFalse((root/'output').exists())
