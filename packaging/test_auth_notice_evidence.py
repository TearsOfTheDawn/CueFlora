import copy
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from auth_notice_evidence import collect,validate
from licence_attribution import completeness


class AuthenticationNoticeTests(unittest.TestCase):
    def fixture(self,root):
        inputs=root/'inputs';cache=root/'cache';inputs.mkdir();cache.mkdir()
        def archive(path,entries):
            with tarfile.open(path,'w:gz') as output:
                for name,data in entries.items():
                    member=tarfile.TarInfo(name);member.size=len(data);output.addfile(member,io.BytesIO(data))
        archive(cache/'crate-1.crate',{'crate-1/LICENSE':b'Original synthetic licence, not a replacement'})
        archive(inputs/'cffi-2.1.1.tar.gz',{'cffi-2.1.1/LICENSE':b'Original synthetic cffi licence',
            'cffi-2.1.1/src/c/libffi_x86_x64/ffi.c':b'/* Original synthetic libffi permission/copyright block */\nint function(void);'})
        checksum=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
        lock={'schema':1,'files':[{'name':'crate','version':'1','file':'crate-1.crate','sha256':checksum(cache/'crate-1.crate'),'scope':'synthetic source'}],
            'inputFiles':{'cffi-2.1.1.tar.gz':checksum(inputs/'cffi-2.1.1.tar.gz')},'cargoLockSha256':'a'*64,'rustSbomSha256':'b'*64,'opensslSbomSha256':'c'*64,
            'scope':'Synthetic original-byte fixture only'}
        lockpath=root/'lock.json';lockpath.write_text(json.dumps(lock))
        return inputs,cache,lock,lockpath

    def test_original_vendored_text_and_archive_bytes_are_retained_and_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);inputs,cache,lock,lockpath=self.fixture(root)
            with patch('auth_notice_evidence.LOCK',lockpath),patch('auth_notice_evidence.obtain',return_value=lock):
                report=collect(inputs,cache,root/'evidence');self.assertEqual(validate(root/'evidence'),report)
            self.assertFalse(report['redistributionApproved']);self.assertEqual(len(report['components']),2)
            text=b''.join(path.read_bytes() for path in (root/'evidence/notices').iterdir())
            self.assertIn(b'Original synthetic libffi permission/copyright block',text)
            self.assertEqual((root/'evidence/sources/crate-1.crate').read_bytes(),(cache/'crate-1.crate').read_bytes())

    def test_changed_missing_component_and_forged_original_notices_fail(self):
        for mutation in ('component','notice','source'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);inputs,cache,lock,lockpath=self.fixture(root)
                with patch('auth_notice_evidence.LOCK',lockpath),patch('auth_notice_evidence.obtain',return_value=lock):
                    report=collect(inputs,cache,root/'evidence')
                    if mutation=='component':
                        report['components'].pop();(root/'evidence/auth-notice-evidence.json').write_text(json.dumps(report))
                    elif mutation=='notice':next((root/'evidence/notices').iterdir()).write_bytes(b'not original')
                    else:(root/'evidence/sources/crate-1.crate').write_bytes(b'changed')
                    with self.assertRaises(ValueError):validate(root/'evidence')

    def test_unknown_native_notice_gap_is_mandatory_not_an_automatic_review_pass(self):
        report={'rows':[{'id':'native:_rust.pyd'}],'unassignedRuntimeFiles':[]}
        result=completeness(report)
        self.assertIn({'component':'Authentication native notices','reason':'exact native dependency original notices and source evidence missing'},result['unresolvedEvidence'])
        result=completeness({**report,'authNativeNoticeEvidence':{'supplied':True}})
        self.assertTrue(any(item['component']=='Authentication native dependencies' for item in result['unresolvedEvidence']))
        self.assertFalse(result['redistributionApproved']);self.assertFalse(result['licenceEvidenceComplete'])
