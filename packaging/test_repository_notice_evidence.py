import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from repository_notice_evidence import safe_repository,inspect_notice_archive,obtain_inputs
from release_inputs import ROOT


class RepositoryNoticeTests(unittest.TestCase):
    def test_repository_tree_urls_normalize_without_following_branches(self):
        self.assertEqual(safe_repository('https://github.com/owner/repo.git'),'https://github.com/owner/repo')
        self.assertEqual(safe_repository('https://github.com/owner/repo/tree/main/crate'),'https://github.com/owner/repo')
        for url in ('http://github.com/owner/repo','https://github.com.evil.invalid/owner/repo','https://user:password@github.com/owner/repo','https://github.com/owner/repo?token=secret'):
            self.assertIsNone(safe_repository(url))

    def fixture(self,folder):
        path=folder/('a'*64+'.zip'); data=b'synthetic original notice'
        commit='b'*40; repository='https://github.com/test-owner/test-repo'; name='c'*24+'.txt'
        with zipfile.ZipFile(path,'w') as archive: archive.writestr('test-repo-'+commit+'/LICENSE',data)
        entry={'repository':repository,'vcs':{'git':{'sha1':commit}},
            'sourceArchive':{'file':path.name,'url':'https://codeload.github.com/test-owner/test-repo/zip/'+commit,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()},
            'notices':{name:{'sourceEntry':'LICENSE','repository':repository,'commit':commit,'sha256':hashlib.sha256(data).hexdigest()}}}
        return path,entry,name,data

    def test_original_notice_bytes_are_checked_against_exact_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp); path,entry,name,data=self.fixture(folder)
            self.assertEqual(inspect_notice_archive({},entry,folder)[name][0],data)
            entry['notices'][name]['sha256']='d'*64
            with self.assertRaisesRegex(ValueError,'content mismatch'): inspect_notice_archive({},entry,folder)

    def test_path_commit_and_changed_source_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp); path,entry,name,data=self.fixture(folder)
            entry['notices'][name]['sourceEntry']='../LICENSE'
            with self.assertRaises(ValueError): inspect_notice_archive({},entry,folder)
            path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'source hash'): inspect_notice_archive({},entry,folder)

    def test_offline_missing_sources_and_tampered_selection_never_download(self):
        with tempfile.TemporaryDirectory() as temp,patch('repository_notice_evidence.urlopen') as network:
            folder=Path(temp); source=ROOT/'packaging/repository-notice-inputs.lock.json'
            with self.assertRaisesRegex(ValueError,'Missing exact'): obtain_inputs(folder,source)
            data=json.loads(source.read_text()); data['redistributionApproved']=True
            changed=folder/'changed.json'; changed.write_text(json.dumps(data))
            with self.assertRaises(ValueError): obtain_inputs(folder,changed,online=True)
            network.assert_not_called()
