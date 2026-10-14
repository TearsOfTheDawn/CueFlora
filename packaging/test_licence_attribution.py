import tempfile
from pathlib import Path
import unittest
from licence_attribution import augment,completeness
from dependency_ledger import file_evidence


class AttributionTests(unittest.TestCase):
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
