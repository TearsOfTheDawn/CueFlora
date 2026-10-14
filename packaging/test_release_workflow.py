import unittest
from release_inputs import ROOT


class WorkflowTests(unittest.TestCase):
    def test_windows_workflow_builds_all_from_public_inputs_but_does_not_publish(self):
        workflow=(ROOT/'.github/workflows/runtime-prototype.yml').read_text()
        for marker in ('bootstrap_public_cache.py','bootstrap_offline.py','prepare_windows.py','--audio-cache','attest-build-provenance@','licenceEvidenceComplete','share_review_candidate'):
            self.assertIn(marker,workflow)
        for marker in ('secrets.','contents: write','action-gh-release','wxt submit','--allow-prototype','FIREFOX_EXTENSION_ID'):
            self.assertNotIn(marker,workflow)
        self.assertIn("node-version: '24.19.0'",workflow)
        self.assertIn('github.event.repository.private == true ||',workflow)
