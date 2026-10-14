"""Keep an observed semantic failure even though structural validation passes.

This fixture is an evaluation case, not a blacklist or subtitle replacement.
Any future global quality intervention must be evaluated against it.
"""
import json
from pathlib import Path
import unittest

from .translate import _ordered_translation_texts


class TranslationSemanticBoundaryTests(unittest.TestCase):
    def test_observed_fabrication_is_not_detectable_by_id_validation(self):
        case = json.loads((Path(__file__).parent / 'fixtures' /
            'translation_fabrication_case.json').read_text(encoding='utf-8'))
        source = json.loads(case['request']['messages'][1]['content'])['cues']
        choice = case['response']['choices'][0]
        output = _ordered_translation_texts(json.loads(choice['message']['content']),
            len(source), choice['finish_reason'], {})
        self.assertEqual(len(output), 30)
        self.assertEqual(source[26]['text'], '把那个后面的石头一起把它挪走，以这个平面平过来。')
        self.assertEqual(output[26], "Thank you for watching. I'll see you in the next video!")
