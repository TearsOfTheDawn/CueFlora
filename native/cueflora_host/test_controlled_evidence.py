import unittest
import json
import os
from unittest.mock import Mock, patch
from .quality_cli import handle_controlled_message


class ControlledEvidenceTests(unittest.TestCase):
    def test_production_translation_disk_failure_has_one_http_attempt(self):
        response = Mock(status_code=200)
        response.json.return_value = {'choices': [{'finish_reason': 'stop', 'message': {
            'content': json.dumps({'translations': [{'id': 0, 'text': 'Hello'}]})}}]}
        client = Mock()
        client.__enter__ = Mock(return_value=client)
        client.__exit__ = Mock(return_value=False)
        client.post.return_value = response
        capture = Mock(capture_id='capture')
        capture.record.side_effect = OSError('disk full')
        with patch.dict(os.environ, {'CUEFLORA_EVIDENCE_DIR': 'unused'}), \
                patch('cueflora_host.evidence.Capture.resume', return_value=capture), \
                patch('cueflora_host.translate.httpx.Client', return_value=client), \
                patch('cueflora_host.send_message'):
            result = handle_controlled_message({'type': 'TRANSLATE_NATIVE', 'jobId': 'job',
                'captureId': 'capture', 'cues': [{'text': '你好'}], 'systemPrompt': 'Translate',
                'translateConfig': {'apiKey': 'local', 'baseUrl': 'http://localhost:11434/v1', 'model': 'test'}})
        self.assertEqual(result['errorKind'], 'evidence')
        self.assertEqual(result['requestCount'], 1)
        self.assertEqual(result['translations'], ['Hello'])
        client.post.assert_called_once()

    @patch('cueflora_host.quality_cli.handle_translate')
    def test_incomplete_evidence_fails_once_without_losing_request_count(self, translate):
        translate.return_value = {'jobId': 'job', 'translations': ['Hello'], 'requestCount': 1,
                                  'evidence': {'complete': False, 'stages': {'translation-response': 'incomplete'}}}
        result = handle_controlled_message({'type': 'TRANSLATE_NATIVE', 'jobId': 'job'})
        self.assertEqual(result['errorKind'], 'evidence')
        self.assertEqual(result['requestCount'], 1)
        self.assertEqual(result['translations'], ['Hello'])
        translate.assert_called_once()

    @patch('cueflora_host.quality_cli.handle_transcribe')
    def test_missing_evidence_is_not_a_successful_control(self, transcribe):
        transcribe.return_value = {'cues': []}
        result = handle_controlled_message({'type': 'TRANSCRIBE_NATIVE'})
        self.assertEqual(result['errorKind'], 'evidence')
        transcribe.assert_called_once()

    @patch('cueflora_host.quality_cli.Capture.resume', side_effect=OSError('capture unavailable'))
    @patch('cueflora_host.quality_cli.handle_translate')
    def test_presentation_failure_cannot_invoke_translation(self, translate, resume):
        with self.assertRaises(OSError):
            handle_controlled_message({'type': 'CAPTURE_PRESENTATION', 'captureId': 'capture', 'jobId': 'job'})
        translate.assert_not_called()
