import unittest
from release_readiness import assess


class ReadinessTests(unittest.TestCase):
    def test_engineering_success_does_not_clear_external_gates(self):
        result = assess({'engineeringPassed':True},{'passed':True,'issues':[]},{'correspondingSourceComplete':False,'remainingObligations':['source closure']})
        self.assertFalse(result['publicReleaseReady'])
        self.assertTrue(result['gates']['engineering'])
        self.assertIn('redistributionEvidence',result['remaining'])

    def test_flags_and_missing_identity_do_not_bypass_gates(self):
        result = assess({'engineeringPassed':True},{'passed':True,'issues':[]},{'correspondingSourceComplete':True,'remainingObligations':[]},
            {'publicReleaseAuthorized':True,'redistributionApproved':True})
        self.assertFalse(result['publicReleaseReady'])
        self.assertFalse(result['gates']['publicationAuthorized'])
