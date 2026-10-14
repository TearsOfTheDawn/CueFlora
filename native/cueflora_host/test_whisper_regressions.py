import unittest

from cueflora_host.whisper import parse_cues, _split_cue


class WhisperRegressionTests(unittest.TestCase):
    def test_long_text_short_duration_does_not_access_uninitialized_time_split(self):
        text = 'word ' * 60
        cues = _split_cue({'start': 0, 'end': 4000, 'text': text})
        self.assertEqual(' '.join(c['text'] for c in cues), text.strip())
        self.assertEqual(cues[0]['start'], 0)
        self.assertEqual(cues[-1]['end'], 4000)

    def test_long_coarse_segment_is_not_given_invented_subtimings(self):
        cue = {'start': 0, 'end': 10000, 'text': '字' * 150, 'coarse_timing': True}
        self.assertEqual(_split_cue(cue), [{k: cue[k] for k in ('start','end','text')}])

    def test_closing_punctuation_after_pause_stays_with_preceding_text(self):
        words = [{'word': text, 'start': s, 'end': e} for text, s, e in [
            ('今', 0, .2), ('天', .45, .65), ('很', .9, 1.1), ('好', 1.35, 1.55),
            ('，', 2.1, 2.16), ('你', 2.7, 2.9), ('好', 3.1, 3.3)]]
        cues = parse_cues({'segments':[{'start':0, 'end':4, 'text':'今天很好，你好', 'words':words}]})
        self.assertTrue(cues[0]['text'].endswith('，'))
        self.assertEqual(''.join(c['text'] for c in cues), '今天很好，你好')
        actual = [(w['text'], round(w['startMs'], 3), round(w['endMs'], 3)) for c in cues for w in c['words']]
        self.assertEqual(actual, [(w['word'], w['start']*1000, w['end']*1000) for w in words])
        self.assertTrue(all(a['endMs'] < b['startMs'] for a,b in zip(cues,cues[1:])))

    def test_opening_punctuation_stays_with_following_text(self):
        words = [{'word':t, 'start':s, 'end':s+.1} for t,s in [('你',0),('好',1.4),('「',1.7),('世',2.6),('界',3.0),('」',3.2)]]
        cues = parse_cues({'segments':[{'start':0,'end':4,'text':'你好「世界」','words':words}]})
        self.assertEqual(''.join(c['text'] for c in cues), '你好「世界」')
        self.assertFalse(any(c['text'].endswith('「') for c in cues))

    def test_ordinary_segment_is_preserved(self):
        diagnostics = {}
        cues = parse_cues(
            {"segments": [{"start": 0, "end": 2, "text": "今天天气很好。"}]},
            diagnostics=diagnostics,
        )
        self.assertEqual(len(cues), 1)
        self.assertIn("今天天气很好", cues[0]["text"])
        self.assertEqual(diagnostics["repetitionSanitizations"], 0)

    def test_pathological_coarse_repetition_is_sanitized(self):
        diagnostics = {}
        repeated = "真的" + ("你想想看" * 40) + "然后我们继续"
        cues = parse_cues(
            {"segments": [{"start": 10, "end": 16, "text": repeated, "words": []}]},
            diagnostics=diagnostics,
        )
        self.assertGreater(len(cues), 0)
        self.assertEqual(diagnostics["repetitionSanitizations"], 1)
        self.assertLess(sum(len(cue["text"]) for cue in cues), len(repeated) // 2)

    def test_long_non_periodic_text_is_not_sanitized(self):
        diagnostics = {}
        text = "".join(chr(0x4E00 + index) for index in range(140))
        parse_cues(
            {"segments": [{"start": 0, "end": 6, "text": text, "words": []}]},
            diagnostics=diagnostics,
        )
        self.assertEqual(diagnostics["repetitionSanitizations"], 0)

    def test_short_punctuation_fragment_is_made_readable(self):
        cues = parse_cues({
            "segments": [
                {"start": 0, "end": 1.0, "text": "你好"},
                {"start": 1.01, "end": 1.06, "text": "。"},
            ]
        })
        self.assertTrue(cues)
        self.assertTrue(all(cue["endMs"] - cue["startMs"] >= 1500 for cue in cues))


if __name__ == "__main__":
    unittest.main()
