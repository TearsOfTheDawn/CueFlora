import tempfile
from pathlib import Path
import unittest
from licence_attribution import augment,completeness
from dependency_ledger import file_evidence
from npm_notices import supplemental_notices


class AttributionTests(unittest.TestCase):
    def test_only_exact_observed_distribution_metadata_is_attributed(self):
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            runtime=Path(directory);known='_internal/cryptography-50.0.2.dist-info/sboms/sbom.json'
            unknown='_internal/unknown-1.dist-info/METADATA';wrong='_internal/cryptography-49.dist-info/METADATA'
            target=runtime/known;target.parent.mkdir(parents=True);target.write_bytes(b'metadata')
            checksum=hashlib.sha256(b'metadata').hexdigest()
            metadata={'hostVersion':'synthetic','python':'3.13.15','files':{known:checksum,unknown:'b'*64,wrong:'c'*64},
                'dependencies':[{'name':'cryptography','version':'50.0.2'}],'buildEnvironmentDependencies':[]}
            report={'rows':[]};augment(metadata,report,runtime);coverage=file_evidence(metadata['files'],report['rows'])
            self.assertTrue(coverage[known]['components']);self.assertFalse(coverage[unknown]['components']);self.assertFalse(coverage[wrong]['components'])
            row=next(row for row in report['rows'] if row['id']=='metadata:cryptography')
            self.assertFalse(row['originVerified']);self.assertTrue(row['reviewRequired'])
            target.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'metadata differs'):augment(metadata,{'rows':[]},runtime)

    def supplemental_fixture(self, runtime):
        notice,=supplemental_notices('wxt','0.21.4')
        name='licenses/upstream/'+notice['file']
        target=runtime/name; target.parent.mkdir(parents=True)
        target.write_bytes(notice['path'].read_bytes())
        metadata={'hostVersion':'synthetic','python':'3.13.15','files':{name:notice['sha256']},
            'dependencies':[],'buildEnvironmentDependencies':[]}
        return metadata,notice,target

    def test_original_supplemental_notice_is_attributed_not_native_code_or_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime=Path(directory); metadata,notice,_=self.supplemental_fixture(runtime)
            report={'rows':[]}; augment(metadata,report,runtime)
            result=file_evidence(metadata['files'],report['rows'])
            self.assertTrue(all(item['components'] for item in result.values()))
            row=next(item for item in report['rows'] if item['id']=='extension-original-notice:wxt')
            self.assertFalse(row['packageCodeShippedByThisRow'])
            self.assertTrue(row['originVerified']); self.assertTrue(row['reviewRequired'])
            self.assertEqual(row['noticeOrigin']['sha256'],notice['sha256'])
            closure=completeness({**report,'unassignedRuntimeFiles':[]})
            self.assertTrue(closure['fileAttributionComplete'])
            self.assertFalse(closure['redistributionApproved']); self.assertFalse(closure['licenceEvidenceComplete'])

    def test_changed_runtime_notice_bytes_or_inventory_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime=Path(directory); metadata,notice,target=self.supplemental_fixture(runtime)
            target.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'origin mismatch'): augment(metadata,{'rows':[]},runtime)
            target.write_bytes(notice['path'].read_bytes())
            metadata['files'][next(iter(metadata['files']))]='a'*64
            with self.assertRaisesRegex(ValueError,'origin mismatch'): augment(metadata,{'rows':[]},runtime)

    def test_unknown_upstream_notice_does_not_acquire_a_guessed_owner(self):
        metadata={'hostVersion':'synthetic','python':'3.13.15','files':{'licenses/upstream/unknown-LICENSE.txt':'a'*64},
            'dependencies':[],'buildEnvironmentDependencies':[]}
        report={'rows':[]}
        with tempfile.TemporaryDirectory() as directory: augment(metadata,report,Path(directory))
        self.assertEqual(file_evidence(metadata['files'],report['rows'])['licenses/upstream/unknown-LICENSE.txt']['components'],[])

    def test_known_own_files_and_exact_notices_are_attributed_not_approved(self):
        metadata={'hostVersion':'synthetic','python':'3.13.15','files':{'_internal/cueflora_host/whisper.py':'a'*64,'licenses/httpx/LICENSE':'b'*64},
            'noticeOrigins':{'licenses/httpx/LICENSE':{'component':'httpx','version':'0.28.1','sha256':'b'*64,'licence':'BSD-3-Clause','scope':'runtime dependency notice'}},
            'dependencies':[],'buildEnvironmentDependencies':[]}
        report={'rows':[]}
        with tempfile.TemporaryDirectory() as directory:
            augment(metadata,report,Path(directory))
        result=file_evidence(metadata['files'],report['rows'])
        self.assertTrue(all(item['components'] for item in result.values()))
        result=completeness({**report,'unassignedRuntimeFiles':[]})
        self.assertTrue(result['fileAttributionComplete']); self.assertFalse(result['redistributionApproved'])
        self.assertFalse(result['licenceEvidenceComplete'])
        metadata['noticeOrigins']['licenses/httpx/LICENSE']['sha256']='c'*64
        with self.assertRaises(ValueError): augment(metadata,report,Path('.'))

    def test_unknown_files_and_missing_js_notices_remain_specific_blockers(self):
        result=completeness({'rows':[{'id':'javascript:example','noticeEvidenceComplete':False}], 'unassignedRuntimeFiles':['unknown.dll']})
        self.assertFalse(result['fileAttributionComplete']); self.assertFalse(result['correspondingSourceComplete'])
        self.assertIn('unknown.dll',str(result['remainingObligations']))
        self.assertIn('javascript:example',str(result['remainingObligations']))
