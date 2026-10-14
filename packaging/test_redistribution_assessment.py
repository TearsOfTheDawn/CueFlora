import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from redistribution_assessment import verify,ledger_identity


class RedistributionAssessmentTests(unittest.TestCase):
    def fixture(self,root):
        # Synthetic reviewer decisions/evidence are confined to unit tests.
        bindings={'sourceInventorySha256':'a'*64,'runtimeInventorySha256':'b'*64,'setupSha256':'c'*64,'extensionSha256':'d'*64}
        path=root/'original-notice.txt'; path.write_bytes(b'synthetic original notice evidence')
        reference={'path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'purpose':'notice'}
        issues=[{'component':name,'reason':'Synthetic unresolved review question'} for name in ('yt-dlp native dependencies','Deno/V8','CPython native dependencies')]
        ledger={'unresolvedEvidence':issues,'unassignedRuntimeFiles':[],'correspondingSourceComplete':False}
        record={'gate':'licences','status':'passed','artifacts':bindings,'reviewedBy':'Synthetic fixture reviewer',
            'redistributionAssessment':{'schema':1,'ledgerSha256':ledger_identity(ledger),'reviewedBy':'Synthetic fixture reviewer',
                'findings':[{**issue,'disposition':'no-corresponding-source-required','basis':'Synthetic explicit reason grounded in the referenced original licence terms.',
                    'references':[dict(reference)]} for issue in issues]}}
        return bindings,ledger,record

    def test_exact_recorded_review_can_resolve_review_questions_not_approve_automatically(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); bindings,ledger,record=self.fixture(root)
            result=verify(record,ledger,bindings,root)
            self.assertTrue(result['acceptedRecordedAssessment']); self.assertEqual(result['findingCount'],3)
            with self.assertRaises(ValueError): verify({**record,'status':'waived'},ledger,bindings,root)
            with self.assertRaises(ValueError): verify({**record,'status':'pending'},ledger,bindings,root)

    def test_wrong_ledger_bindings_missing_findings_and_duplicate_findings_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); bindings,ledger,record=self.fixture(root)
            changed=copy.deepcopy(record); changed['redistributionAssessment']['ledgerSha256']='e'*64
            with self.assertRaises(ValueError): verify(changed,ledger,bindings,root)
            with self.assertRaises(ValueError): verify(record,ledger,{**bindings,'setupSha256':'e'*64},root)
            changed=copy.deepcopy(record); changed['redistributionAssessment']['findings'].pop()
            with self.assertRaises(ValueError): verify(changed,ledger,bindings,root)
            changed=copy.deepcopy(record); changed['redistributionAssessment']['findings'][1]=changed['redistributionAssessment']['findings'][0]
            with self.assertRaises(ValueError): verify(changed,ledger,bindings,root)

    def test_missing_real_source_and_unknown_file_attribution_cannot_be_reviewed_away(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); bindings,ledger,record=self.fixture(root)
            for issue in ({'component':'FFmpeg/Opus','reason':'matching-source-or-recipe-missing'},{'component':'javascript:example','reason':'missing notice'}):
                changed={**ledger,'unresolvedEvidence':[issue]}; record['redistributionAssessment']['ledgerSha256']=ledger_identity(changed)
                with self.assertRaisesRegex(ValueError,'Mandatory missing'): verify(record,changed,bindings,root)
            changed={**ledger,'unassignedRuntimeFiles':['unknown.dll']}; record['redistributionAssessment']['ledgerSha256']=ledger_identity(changed)
            with self.assertRaises(ValueError): verify(record,changed,bindings,root)

    def test_changed_missing_and_outside_reference_files_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); bindings,ledger,record=self.fixture(root)
            for path in ('missing.txt','../outside.txt','C:/outside.txt','folder/./notice.txt'):
                changed=copy.deepcopy(record); changed['redistributionAssessment']['findings'][0]['references'][0]['path']=path
                with self.assertRaises(ValueError): verify(changed,ledger,bindings,root)
            (root/'original-notice.txt').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'changed dependency'): verify(record,ledger,bindings,root)

    def test_nonshipment_requires_scope_evidence_and_waiver_dispositions_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); bindings,ledger,record=self.fixture(root)
            changed=copy.deepcopy(record); changed['redistributionAssessment']['findings'][0]['disposition']='not-shipped'
            with self.assertRaisesRegex(ValueError,'binary scope'): verify(changed,ledger,bindings,root)
            changed['redistributionAssessment']['findings'][0]['references'][0]['purpose']='binary-scope'
            self.assertTrue(verify(changed,ledger,bindings,root)['acceptedRecordedAssessment'])
            changed['redistributionAssessment']['findings'][0]['disposition']='waived'
            with self.assertRaises(ValueError): verify(changed,ledger,bindings,root)

    def test_full_readiness_requires_hashed_review_not_a_passed_flag_alone(self):
        from test_approval_evidence import ApprovalTests
        from release_readiness import assess
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); helper=ApprovalTests(); decisions=helper.records(root)
            ignored,ledger,assessment=self.fixture(root)
            bindings=helper.bindings()
            record=json.loads((root/'licences.json').read_text())
            assessment['redistributionAssessment']['reviewedBy']=record['reviewedBy']
            record['redistributionAssessment']=assessment['redistributionAssessment']
            ledger['remainingObligations']=['Review required']; ledger['correspondingSourceComplete']=False
            record['redistributionAssessment']['ledgerSha256']=ledger_identity(ledger)
            (root/'licences.json').write_text(json.dumps(record))
            decisions['gates']['licences']['reportSha256']=hashlib.sha256((root/'licences.json').read_bytes()).hexdigest()
            engineering={'engineeringPassed':True,'artifactBindings':bindings}; source={'passed':True,'issues':[],'sourceInventorySha256':'a'*64}
            result=assess(engineering,source,ledger,helper.configuration(),decisions,root,root)
            self.assertTrue(result['publicReleaseReady']); self.assertIsNotNone(result['dependencyAssessment'])
            record.pop('redistributionAssessment'); (root/'licences.json').write_text(json.dumps(record))
            decisions['gates']['licences']['reportSha256']=hashlib.sha256((root/'licences.json').read_bytes()).hexdigest()
            self.assertFalse(assess(engineering,source,ledger,helper.configuration(),decisions,root,root)['publicReleaseReady'])
