import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from collect_v8_notices import ROOT,validate,obtain,match_versions,validate_evidence
from v8_submodule_notices import load as submodule_notices


class V8NoticeTests(unittest.TestCase):
    def setUp(self):
        self.lock=json.loads((ROOT/'packaging/v8-notice-inputs.lock.json').read_text())

    def test_sources_must_be_exact_primary_commit_pins_not_latest(self):
        validate(self.lock)
        for change in ({'redistributionApproved':True},{'files':[]},{'v8Version':'latest'},{'bindingCommit':'main'}):
            with self.assertRaises(ValueError): validate({**self.lock,**change})
        for change in ({'file':'../source.zip'},{'url':'https://codeload.github.com.evil.invalid/source'},
            {'url':self.lock['files'][0]['url']+'?token=not-allowed'},{'sha256':'bad'},{'root':'other-commit'}):
            value=copy.deepcopy(self.lock); value['files'][0].update(change)
            with self.assertRaises(ValueError): validate(value)

    def test_offline_missing_input_never_downloads(self):
        with tempfile.TemporaryDirectory() as folder,patch('collect_v8_notices.urlopen') as network:
            with self.assertRaisesRegex(ValueError,'Missing exact'): obtain(Path(folder))
            network.assert_not_called()

    def test_version_match_keeps_dirty_vcs_warning_not_binary_source_proof(self):
        cargo={'package':[{'name':'v8','version':'150.4.0','checksum':'a'*64}]}
        vcs={'git':{'sha1':self.lock['bindingCommit'],'dirty':True}}
        version='deno 2.9.7\nv8 15.0.245.2-rusty\ntypescript 6.0.3'
        self.assertEqual(match_versions(self.lock,cargo,vcs,b'header',b'header',version),'a'*64)
        self.assertTrue(vcs['git']['dirty'])
        for c,v,first,second,text in (({'package':[]},vcs,b'h',b'h',version),
            (cargo,{'git':{'sha1':'b'*40}},b'h',b'h',version),(cargo,vcs,b'first',b'second',version),
            (cargo,vcs,b'h',b'h',version.replace('15.0.245.2','15.0.245.3'))):
            with self.assertRaises(ValueError): match_versions(self.lock,c,v,first,second,text)

    def evidence_fixture(self,folder):
        (folder/'notices').mkdir(); (folder/'notices/core.txt').write_bytes(b'synthetic original notice')
        icu=self.lock['icu']; (folder/'notices'/icu['noticeFile']).write_bytes((ROOT/'packaging/source-metadata'/icu['noticeFile']).read_bytes())
        deno=folder/'deno.exe'; deno.write_bytes(b'synthetic binary')
        digest=lambda data:hashlib.sha256(data).hexdigest()
        report={'coreNoticesRestored':True,'denoSha256':digest(deno.read_bytes()),
            'lockSha256':digest((ROOT/'packaging/v8-notice-inputs.lock.json').read_bytes()),'sourceInputs':self.lock['files'],
            'redistributionApproved':False,'binaryDependencyClosureComplete':False,
            'icuEvidence':{'pins':icu,'dataLineageVerified':True,'originalNoticeRestored':True},
            'noticeFiles':{'core.txt':digest(b'synthetic original notice'),icu['noticeFile']:icu['noticeSha256']},
            'notices':{'core.txt':{'sha256':digest(b'synthetic original notice')},icu['noticeFile']:{'sha256':icu['noticeSha256']}}}
        content,origins,_,sub_evidence=submodule_notices()
        report['submoduleEvidence']=sub_evidence
        for name,raw in content.items():
            (folder/'notices'/name).write_bytes(raw)
            report['noticeFiles'][name]=digest(raw)
            report['notices'][name]=origins[name]
        (folder/'v8-notice-evidence.json').write_text(json.dumps(report))
        return deno,report

    def test_evidence_binds_binary_and_all_notice_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp); deno,report=self.evidence_fixture(folder)
            self.assertFalse(validate_evidence(folder,deno)['binaryDependencyClosureComplete'])
            (folder/'notices/core.txt').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'Changed'): validate_evidence(folder,deno)
            (folder/'notices/core.txt').write_bytes(b'synthetic original notice'); deno.write_bytes(b'other binary')
            with self.assertRaisesRegex(ValueError,'binding'): validate_evidence(folder,deno)

    def test_evidence_cannot_grant_approval_or_hide_extra_notice(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp); deno,report=self.evidence_fixture(folder)
            for field in ('redistributionApproved','binaryDependencyClosureComplete'):
                value={**report,field:True}; (folder/'v8-notice-evidence.json').write_text(json.dumps(value))
                with self.assertRaises(ValueError): validate_evidence(folder,deno)
            (folder/'v8-notice-evidence.json').write_text(json.dumps(report))
            (folder/'notices/extra.txt').write_bytes(b'extra')
            with self.assertRaises(ValueError): validate_evidence(folder,deno)

    def test_icu_lineage_and_notice_cannot_be_omitted_or_claimed_for_other_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp); deno,report=self.evidence_fixture(folder)
            for evidence in (None,'bad',{}, {**report['icuEvidence'],'dataLineageVerified':False},
                    {**report['icuEvidence'],'pins':{}}):
                (folder/'v8-notice-evidence.json').write_text(json.dumps({**report,'icuEvidence':evidence}))
                with self.assertRaisesRegex(ValueError,'ICU'): validate_evidence(folder,deno)
