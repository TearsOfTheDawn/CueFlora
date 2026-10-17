import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from approval_evidence import GATES, pending, verified_decisions
from release_readiness import assess


class ApprovalTests(unittest.TestCase):
    def bindings(self):
        return {name:character*64 for name,character in zip(('sourceInventorySha256','runtimeInventorySha256','setupSha256','extensionSha256'),'abcd')}

    def records(self,root,waiver=False):
        bindings=self.bindings(); result=pending(bindings)
        for gate in GATES:
            status='waived' if waiver and gate in ('chromeRun','cleanWindows') else 'passed'
            record={'artifacts':bindings,'gate':gate,'status':status,'reviewedBy':'Synthetic unit test','reason':'Synthetic evidence only'}
            path=root/(gate+'.json'); path.write_text(json.dumps(record))
            result['gates'][gate]={'status':status,'reviewedBy':record['reviewedBy'],'reason':record['reason'],'report':path.name,'reportSha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        return result

    def configuration(self):
        return {'schema':2,'mode':'public','product':'cueflora','owner':'Synthetic fixture only','extensionIds':{'chrome':'a'*32},
            'privacyUrl':'https://fixture.example.com/privacy','downloadUrl':'https://fixture.example.com/download','supportUrl':'https://fixture.example.com/support',
            'sourceInventorySha256':'a'*64,'runtimeInventorySha256':'b'*64,'signing':'unsigned','publicReleaseAuthorized':False,'redistributionApproved':False}

    def test_pending_never_becomes_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            result=verified_decisions(pending(self.bindings()),Path(directory),self.bindings())
            self.assertEqual(set(result.values()),{'pending'})

    def test_complete_evidence_and_explicit_manual_waiver_are_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); records=self.records(root,waiver=True)
            statuses=verified_decisions(records,root,self.bindings())
            self.assertEqual(statuses['chromeRun'],'waived'); self.assertEqual(statuses['licences'],'passed')
            result=assess({'engineeringPassed':True,'artifactBindings':self.bindings()},
                {'passed':True,'issues':[],'sourceInventorySha256':'a'*64},{'correspondingSourceComplete':True,'remainingObligations':[]},self.configuration(),records,root)
            self.assertTrue(result['publicReleaseReady']); self.assertFalse(result['published'])
            self.assertEqual(set(result['waived']),{'chromeRun','cleanWindows'})
            result=assess({'engineeringPassed':True,'artifactBindings':self.bindings()},
                {'passed':True,'issues':[],'sourceInventorySha256':'a'*64},{'correspondingSourceComplete':False,'remainingObligations':['unresolved']},self.configuration(),records,root)
            self.assertFalse(result['publicReleaseReady'])

    def test_flags_cannot_bypass_missing_content_or_different_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); records=self.records(root)
            for edit in ('hash','path','binding','claim','reviewer','missing'):
                bad=copy.deepcopy(records)
                if edit=='hash': bad['gates']['publication']['reportSha256']='f'*64
                elif edit=='path': bad['gates']['publication']['report']='../outside.json'
                elif edit=='binding': bad['artifacts']['setupSha256']='f'*64
                elif edit=='claim': bad['gates']['publication']['status']='waived'
                elif edit=='reviewer': bad['gates']['publication']['reviewedBy']=''
                else: bad['gates']['publication']['report']='missing.json'
                with self.subTest(edit=edit),self.assertRaises(ValueError): verified_decisions(bad,root,self.bindings())
            (root/'publication.json').write_text('{}')
            with self.assertRaises(ValueError): verified_decisions(records,root,self.bindings())

    def test_waivers_cannot_clear_licensing_policy_security_or_screenshots(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); records=self.records(root)
            for gate in set(GATES)-{'cleanWindows','chromeRun'}:
                bad=copy.deepcopy(records); bad['gates'][gate]['status']='waived'
                with self.subTest(gate=gate),self.assertRaises(ValueError): verified_decisions(bad,root,self.bindings())

    def test_unknown_fields_status_and_noncanonical_paths_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); records=self.records(root)
            for report in ['C:/secret.json','/absolute','./publication.json','a//publication.json','a\\publication.json']:
                bad=copy.deepcopy(records); bad['gates']['publication']['report']=report
                with self.subTest(path=report),self.assertRaises(ValueError): verified_decisions(bad,root,self.bindings())
            bad=copy.deepcopy(records); bad['gates']['publication']['status']='approved'
            with self.assertRaises(ValueError): verified_decisions(bad,root,self.bindings())

    def test_helper_hosting_does_not_require_store_approval_or_screenshot_assumptions(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); records=self.records(root)
            for name in ('screenshots','publicLocations','storeApproval','cleanWindows','chromeRun'):
                records['gates'][name]={'status':'pending','reviewedBy':None,'reason':None,'report':None,'reportSha256':None}
            arguments=({'engineeringPassed':True,'artifactBindings':self.bindings()},
                {'passed':True,'issues':[],'sourceInventorySha256':'a'*64},
                {'correspondingSourceComplete':True,'remainingObligations':[]},self.configuration())
            result=assess(*arguments,records,root)
            self.assertTrue(result['helperDownloadReady'])
            self.assertFalse(result['publicReleaseReady'])
            self.assertEqual(result['decisions']['screenshots'],'pending')
            for gate in ('licences','nativeSecurity','downloadPolicy','publication'):
                bad=copy.deepcopy(records)
                bad['gates'][gate]={'status':'pending','reviewedBy':None,'reason':None,'report':None,'reportSha256':None}
                with self.subTest(gate=gate):
                    self.assertFalse(assess(*arguments,bad,root)['helperDownloadReady'])
            bad=copy.deepcopy(records); bad['apiKey']='synthetic'
            with self.assertRaises(ValueError): verified_decisions(bad,root,self.bindings())
