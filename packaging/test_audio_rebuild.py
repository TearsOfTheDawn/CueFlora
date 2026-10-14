import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from verify_audio_rebuild import compare,preserve_working
from audio_build import CONFIGURE,digest,ROOT


class AudioRebuildTests(unittest.TestCase):
    def fixture(self,root,content):
        (root/'install/bin').mkdir(parents=True); (root/'corresponding-source').mkdir()
        paths=[root/'install/bin'/name for name in ('ffmpeg.exe','ffprobe.exe')]
        for path in paths: path.write_bytes(content)
        audit=root/'corresponding-source/toolchain-audit.json'; audit.write_text(json.dumps({'passed':True,'files':{'compiler.exe':'a'*64}}))
        report={'version':'9.0.2','sourceSignatureVerified':True,'inputLockSha256':digest(ROOT/'packaging/audio-inputs.lock.json'),
            'toolchainLockSha256':digest(ROOT/'packaging/audio-toolchain.lock.json'),'toolchainAuditSha256':digest(audit),
            'configureFFmpeg':['./configure','--prefix=/same','--extra-cflags=-I/same/include','--extra-ldflags=-L/same/lib',*CONFIGURE],
            'configureOpus':['./configure','--host=x86_64-w64-mingw32','--prefix=/same','--enable-shared','--disable-static','--disable-doc','--disable-extra-programs','LDFLAGS=-static-libgcc'],
            'files':{path.name:digest(path) for path in paths}}
        (root/'audio-build.json').write_text(json.dumps(report))
        return report

    def test_only_own_fresh_experiment_paths_are_moved_recoverably(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); working=root/'working'; working.mkdir(); (working/'evidence').write_bytes(b'preserved')
            with self.assertRaises(ValueError): preserve_working(working,root/'foreign',root)
            preserve_working(working,root/'first',root)
            self.assertEqual((root/'first/evidence').read_bytes(),b'preserved')
            working.mkdir()
            with self.assertRaises(ValueError): preserve_working(working,root/'first',root)
            with self.assertRaises(ValueError): preserve_working(root,root/'second',root)

    def test_unexplained_payload_change_fails_comparison(self):
        with tempfile.TemporaryDirectory() as temp:
            first,second=Path(temp)/'first',Path(temp)/'second'
            self.fixture(first,b'first'); self.fixture(second,b'second')
            with patch('verify_audio_rebuild.normalized_pe',side_effect=lambda path:(digest(path),[])):
                result=compare(first,second)
            self.assertFalse(result['passed']); self.assertEqual(result['unexplainedFiles'],['ffmpeg.exe','ffprobe.exe'])

    def test_configuration_changes_empty_manifests_and_changed_payload_never_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            first,second=Path(temp)/'first',Path(temp)/'second'
            self.fixture(first,b'same'); report=self.fixture(second,b'same')
            with patch('verify_audio_rebuild.normalized_pe',return_value=('a'*64,[])):
                self.assertTrue(compare(first,second)['passed'])
                report['configureFFmpeg'][1]='--prefix=/different'; (second/'audio-build.json').write_text(json.dumps(report))
                with self.assertRaisesRegex(ValueError,'effective input'): compare(first,second)
                report['files']={}; (second/'audio-build.json').write_text(json.dumps(report))
                with self.assertRaises(ValueError): compare(first,second)
