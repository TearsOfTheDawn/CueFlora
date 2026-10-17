import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from repository_notice_evidence import safe_repository,inspect_notice_archive,obtain_inputs,raw_notice_pins,obtain_raw_notices,validate_evidence
from release_inputs import ROOT


class RepositoryNoticeTests(unittest.TestCase):
    def raw_fixture(self,folder):
        data=b'synthetic original public-domain notice\n'; sha=hashlib.sha256(data).hexdigest()
        blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        repository='https://github.com/test-owner/test-repo'; commit='b'*40; name='c'*24+'.txt'
        record={'file':sha+'.txt','url':'https://raw.githubusercontent.com/test-owner/test-repo/'+commit+'/UNLICENSE',
            'sha256':sha,'gitBlobSha':blob,'bytes':len(data)}
        entry={'repository':repository,'vcs':{'git':{'sha1':commit}},'noticeSources':{'UNLICENSE':record},
            'notices':{name:{'sourceEntry':'UNLICENSE','repository':repository,'commit':commit,'sha256':sha}}}
        return folder/record['file'],entry,name,data

    def test_original_notice_only_bytes_retain_unlicense_without_claiming_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp); path,entry,name,data=self.raw_fixture(folder); path.write_bytes(data)
            self.assertEqual(inspect_notice_archive({},entry,folder)[name][0],data)
            self.assertNotIn('sourceArchive',entry)
            entry['noticeSources']['UNLICENSE']['gitBlobSha']='a'*40
            with self.assertRaisesRegex(ValueError,'Git blob mismatch'): inspect_notice_archive({},entry,folder)

    def test_notice_only_cache_hit_and_offline_missing_never_request_network(self):
        with tempfile.TemporaryDirectory() as temp,patch('repository_notice_evidence.urlopen') as network:
            folder=Path(temp); path,entry,name,data=self.raw_fixture(folder)
            with self.assertRaisesRegex(ValueError,'Missing exact'): obtain_raw_notices(entry,folder)
            path.write_bytes(data); obtain_raw_notices(entry,folder)
            network.assert_not_called()

    def test_notice_only_download_is_bounded_and_saved_only_after_verification(self):
        with tempfile.TemporaryDirectory() as temp,patch('repository_notice_evidence.urlopen') as network:
            folder=Path(temp); path,entry,name,data=self.raw_fixture(folder)
            response=network.return_value.__enter__.return_value
            response.geturl.return_value=entry['noticeSources']['UNLICENSE']['url']; response.read.return_value=data
            obtain_raw_notices(entry,folder,online=True)
            response.read.assert_called_once_with(len(data)+1)
            self.assertEqual(path.read_bytes(),data)
            network.assert_called_once_with(entry['noticeSources']['UNLICENSE']['url'],timeout=30)

    def test_notice_only_wrong_download_or_redirect_does_not_create_cached_file(self):
        for changed,redirect in [(b'changed',False),(b'',False),(b'oversized'*100,False),(None,True)]:
            with self.subTest(changed=changed,redirect=redirect),tempfile.TemporaryDirectory() as temp,patch('repository_notice_evidence.urlopen') as network:
                folder=Path(temp); path,entry,name,data=self.raw_fixture(folder)
                response=network.return_value.__enter__.return_value
                response.geturl.return_value='https://example.invalid/' if redirect else entry['noticeSources']['UNLICENSE']['url']
                response.read.return_value=changed
                with self.assertRaises(ValueError): obtain_raw_notices(entry,folder,online=True)
                self.assertFalse(path.exists())

    def test_notice_only_malformed_origins_and_ambiguous_sources_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp); path,original,name,data=self.raw_fixture(folder)
            changes=[('url','https://raw.githubusercontent.com/test-owner/test-repo/main/UNLICENSE'),
                ('url','https://raw.githubusercontent.com.evil.invalid/UNLICENSE'),('url','http://raw.githubusercontent.com/a'),
                ('bytes',True),('bytes',1024*1024+1),('gitBlobSha','bad'),('file','../notice.txt'),('sha256','a'*64)]
            for field,value in changes:
                entry=json.loads(json.dumps(original)); entry['noticeSources']['UNLICENSE'][field]=value
                with self.subTest(field=field,value=value),self.assertRaises(ValueError): raw_notice_pins(entry)
            entry=json.loads(json.dumps(original)); entry['sourceArchive']={}
            with self.assertRaises(ValueError): raw_notice_pins(entry)
            entry=json.loads(json.dumps(original)); entry['noticeSources']['extra']=entry['noticeSources']['UNLICENSE']
            with self.assertRaises(ValueError): raw_notice_pins(entry)
            entry=json.loads(json.dumps(original)); entry['notices'][name]['sourceEntry']='../UNLICENSE'
            with self.assertRaises(ValueError): raw_notice_pins(entry)

    def test_notice_only_symlink_is_refused_even_for_expected_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp); path,entry,name,data=self.raw_fixture(folder); path.write_bytes(data)
            with patch.object(Path,'is_symlink',return_value=True),self.assertRaisesRegex(ValueError,'linked'):
                inspect_notice_archive({},entry,folder)

    def test_notice_only_report_cannot_change_pinned_origin_while_retaining_notice_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); (root/'packaging').mkdir(); folder=root/'evidence'; folder.mkdir(); (folder/'notices').mkdir()
            path,entry,name,data=self.raw_fixture(folder/'notices'); path=folder/'notices'/name; path.write_bytes(data)
            entry.update({'name':'synthetic-crate','version':'1.0.0','status':'notices-found',
                'reason':None,'licenceApplicabilityProven':False})
            policy={'repositoryNoticeInputSha256':'a'*64,'cargoLockSha256':'b'*64,'denoSourceSha256':'c'*64}
            (root/'packaging/deno-cargo-policy.json').write_text(json.dumps(policy))
            (root/'packaging/repository-notice-inputs.lock.json').write_text(json.dumps({'packages':[entry]}))
            report={'schema':1,'redistributionApproved':False,'licenceApplicabilityProven':False,'binaryDependencyClosureComplete':False,
                'inputInventorySha256':policy['repositoryNoticeInputSha256'],'cargoLockSha256':policy['cargoLockSha256'],
                'sourceInput':{'sha256':policy['denoSourceSha256']},'packages':[entry],'recoveredPackageCount':1,
                'noticeFiles':{name:hashlib.sha256(data).hexdigest()}}
            report_path=folder/'repository-notice-inventory.json'; report_path.write_text(json.dumps(report))
            with patch('release_inputs.ROOT',root):
                self.assertEqual(validate_evidence(folder)['recoveredPackageCount'],1)
                report['packages'][0]['noticeSources']['UNLICENSE']['url']='https://example.invalid/notice'
                report_path.write_text(json.dumps(report))
                with self.assertRaisesRegex(ValueError,'origin changed'): validate_evidence(folder)

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


class FollowupNoticePinsTests(unittest.TestCase):
    def test_original_monorepo_notices_are_build_inputs_without_approval(self):
        from release_inputs import ROOT,digest
        from repository_notice_evidence import raw_notice_pins
        inventory_path=ROOT/'packaging/repository-notice-inputs.lock.json'
        inventory=json.loads(inventory_path.read_text(encoding='utf-8'))
        policy=json.loads((ROOT/'packaging/deno-cargo-policy.json').read_text(encoding='utf-8'))
        self.assertEqual(digest(inventory_path),policy['repositoryNoticeInputSha256'])
        expected={
            ('libffi-sys','4.1.0'):('7b1471ad430dd899046280f79066fc2d9b0fac90',{'LICENSE-APACHE','LICENSE-MIT'}),
            ('objc2-foundation','0.3.2'):('7b1abfd750a2cacaea71d6a56ecfb83cb7de560b',{'LICENSE.md'}),
            ('opentelemetry-proto','0.32.0'):('ec289cb3c6f8260951699c51df968560943c1451',{'LICENSE'})}
        selected={(row['name'],row['version']):row for row in inventory['packages']
            if (row['name'],row['version']) in expected}
        self.assertEqual(set(selected),set(expected))
        for key,(commit,names) in expected.items():
            with self.subTest(package=key):
                row=selected[key]
                self.assertEqual(row['vcs']['git']['sha1'],commit)
                self.assertEqual(set(raw_notice_pins(row)),names)
                self.assertEqual(row['status'],'notices-found')
                self.assertFalse(row['licenceApplicabilityProven'])
                self.assertNotIn('sourceArchive',row)
        for field in ('redistributionApproved','licenceApplicabilityProven','binaryDependencyClosureComplete'):
            self.assertFalse(inventory[field])
