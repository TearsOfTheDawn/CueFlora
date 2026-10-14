import unittest
from .quality_benchmark import character_error_rate


class BenchmarkMetricTests(unittest.TestCase):
    def test_punctuation_does_not_mask_lexical_errors(self):
        self.assertEqual(character_error_rate('你好，世界！','你好世界')['cer'], 0)
        self.assertEqual(character_error_rate('不可以','可以')['errors'], 1)

    def test_empty_reference_is_not_a_perfect_score(self):
        self.assertIsNone(character_error_rate('', 'invented')['cer'])
        self.assertEqual(character_error_rate('', 'invented')['errors'], 8)
