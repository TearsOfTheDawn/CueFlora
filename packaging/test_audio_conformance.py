import base64
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from audio_build import CONFIGURE, ROOT, digest
from verify_audio_conformance import fixture_inputs, validate_recipe


class ConformanceTests(unittest.TestCase):
    def test_public_fixtures_are_hash_verified_and_not_speech(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=fixture_inputs(Path(directory))
            self.assertEqual(len(paths),5)
            self.assertTrue(all(path.is_file() and duration==0.5 for path,duration in paths))
            data=json.loads((ROOT/'packaging/fixtures/synthetic-audio.json').read_text())
            data['files']['tone.mp3']['sha256']='0'*64
            fixture=Path(directory)/'bad.json'; fixture.write_text(json.dumps(data))
            with self.assertRaises(ValueError): fixture_inputs(Path(directory),fixture)

    def test_changed_recipe_extra_flags_and_tool_bytes_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'install/bin').mkdir(parents=True); (root/'corresponding-source').mkdir()
            for name in ('ffmpeg.exe','ffprobe.exe'): (root/'install/bin'/name).write_bytes(name.encode())
            audit=root/'corresponding-source/toolchain-audit.json'; audit.write_text(json.dumps({'passed':True,'files':{'compiler':'a'*64}}))
            build={'version':'9.0.2','sourceSignatureVerified':True,'inputLockSha256':digest(ROOT/'packaging/audio-inputs.lock.json'),
                'toolchainLockSha256':digest(ROOT/'packaging/audio-toolchain.lock.json'),'toolchainAuditSha256':digest(audit),
                'configureFFmpeg':['./configure','--prefix=/synthetic','--extra-cflags=-I/synthetic','--extra-ldflags=-L/synthetic',*CONFIGURE],
                'configureOpus':['./configure','--host=x86_64-w64-mingw32','--prefix=/synthetic','--enable-shared','--disable-static','--disable-doc','--disable-extra-programs','LDFLAGS=-static-libgcc'],
                'files':{name:digest(root/'install/bin'/name) for name in ('ffmpeg.exe','ffprobe.exe')}}
            manifest=root/'audio-build.json'; manifest.write_text(json.dumps(build)); validate_recipe(root)
            for key,value in [('version','latest'),('sourceSignatureVerified',False),('inputLockSha256','b'*64),('configureFFmpeg',build['configureFFmpeg']+['--enable-gpl']),('configureOpus',build['configureOpus']+['extra'])]:
                broken=copy.deepcopy(build); broken[key]=value; manifest.write_text(json.dumps(broken))
                with self.subTest(field=key),self.assertRaises(ValueError): validate_recipe(root)
            manifest.write_text(json.dumps(build)); (root/'install/bin/ffmpeg.exe').write_bytes(b'changed')
            with self.assertRaises(ValueError): validate_recipe(root)
