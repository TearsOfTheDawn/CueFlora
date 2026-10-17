import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile
from v8_submodule_notices import ROOT,load,notice_name,validate_collected


class V8SubmoduleTests(unittest.TestCase):
    def fixture(self,path):
        (path/'packaging/source-metadata').mkdir(parents=True)
        shutil.copy2(ROOT/'packaging/v8-submodule-notices.lock.json',path/'packaging/v8-submodule-notices.lock.json')
        for item in (ROOT/'packaging/source-metadata').glob('V8-submodule-*'):
            shutil.copy2(item,path/'packaging/source-metadata'/item.name)
        return path/'packaging/v8-submodule-notices.lock.json'

    def test_all_actual_originals_and_git_blobs_verify_offline(self):
        contents,origins,sources,evidence=load()
        self.assertEqual(len(contents),13)
        self.assertEqual(evidence['selectedOrigins'],10)
        self.assertTrue(evidence['allSelectedOriginsVerified'])
        self.assertEqual(set(contents),set(origins))
        self.assertGreater(len(sources),len(contents))
        validate_collected(evidence,{n:hashlib.sha256(r).hexdigest() for n,r in contents.items()})

    def test_missing_or_changed_original_evidence_is_not_approved(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp); self.fixture(path)
            item=next((path/'packaging/source-metadata').glob('*.txt'))
            item.write_bytes(b'altered')
            with self.assertRaisesRegex(ValueError,'Missing/changed'): load(path)
            item.unlink()
            with self.assertRaisesRegex(ValueError,'Missing/changed'): load(path)

    def test_bad_unsafe_and_duplicate_pins_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp); lock_path=self.fixture(path); original=json.loads(lock_path.read_text())
            for field,value in (('file','../notice.txt'),('sourceEntry','LICENSE.cc'),('url','https://example.invalid/latest'),('bytes',False),('gitBlobSha','0'*40)):
                lock=copy.deepcopy(original); lock['notices'][0][field]=value
                lock_path.write_text(json.dumps(lock))
                with self.assertRaises(ValueError): load(path)
            for key in ('trees','notices'):
                lock=copy.deepcopy(original); lock[key].append(lock[key][0])
                lock_path.write_text(json.dumps(lock))
                with self.assertRaises(ValueError): load(path)

    def test_origin_host_redirect_or_moving_commit_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp); lock_path=self.fixture(path); original=json.loads(lock_path.read_text())
            for key,value in (('repository','https://chromium.googlesource.com.evil.invalid/a'),('commit','main'),('url',original['trees'][0]['url']+'&token=private')):
                lock=copy.deepcopy(original); lock['trees'][0][key]=value
                lock_path.write_text(json.dumps(lock))
                with self.assertRaises(ValueError): load(path)

    def test_changed_dependency_source_and_missing_collected_notice_fail(self):
        with self.assertRaisesRegex(ValueError,'dependency source changed'): load(deps=b'other DEPS')
        _,_,_,evidence=load()
        with self.assertRaisesRegex(ValueError,'binding'): validate_collected(evidence,{})
        with self.assertRaisesRegex(ValueError,'binding'): validate_collected({**evidence,'allSelectedOriginsVerified':False},evidence['noticeFiles'])

    def test_copying_phase_source_code_is_not_a_licence_file(self):
        for name in ('LICENSE','LICENSE-APACHE','LICENSE.TXT','COPYING','NOTICE.md'):
            self.assertTrue(notice_name(name))
        for name in ('copying-phase.cc','copying-phase.h','LICENSE.rs','../LICENSE','src/LICENSE','README.md'):
            self.assertFalse(notice_name(name))
