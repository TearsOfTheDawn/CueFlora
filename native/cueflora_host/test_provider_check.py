import json
import unittest
from unittest.mock import patch
import httpx
from .provider_check import check_provider


class ProviderCheckTests(unittest.TestCase):
    def request(self, response, provider=None):
        calls = []
        def handler(request):
            calls.append(request)
            return response
        client = httpx.Client(transport=httpx.MockTransport(handler))
        with patch('cueflora_host.provider_check.httpx.Client', return_value=client):
            result = check_provider({'requestId': 'check-1', 'provider': provider or {
                'baseUrl': 'https://fixture.invalid/v1', 'apiKey': 'private-test-key'}})
        return result, calls

    def test_hosted_metadata_only_with_key(self):
        result, calls = self.request(httpx.Response(200, json={'data': [{'id': 'b'}, {'id': 'a'}, {'id': 'a'}]}))
        self.assertEqual(result, {'requestId': 'check-1', 'status': 'connected', 'reason': 'ok', 'models': ['a','b']})
        self.assertEqual([request.method for request in calls], ['GET'])
        self.assertEqual(str(calls[0].url), 'https://fixture.invalid/v1/models')
        self.assertEqual(calls[0].headers['Authorization'], 'Bearer private-test-key')
        self.assertNotIn('private-test-key', json.dumps(result))

    def test_local_metadata_has_no_authorization_when_key_empty(self):
        result, calls = self.request(httpx.Response(200, json={'data': []}), {'baseUrl': 'http://localhost:1234/v1', 'apiKey': ''})
        self.assertEqual(result['status'], 'connected')
        self.assertNotIn('Authorization', calls[0].headers)

    def test_failure_codes_and_no_redirect(self):
        for code, reason in [(401,'auth'), (403,'auth'), (404,'unsupported'), (405,'unsupported'), (501,'unsupported'), (302,'http'), (500,'http')]:
            result, calls = self.request(httpx.Response(code, headers={'Location': 'https://other.invalid/private'}))
            self.assertEqual(result['reason'], reason)
            self.assertEqual(len(calls), 1)

    def test_malformed_oversized_and_secret_model_payloads(self):
        for response in [httpx.Response(200, content=b'not json'), httpx.Response(200, json={'data': [{'id': '<html>'}]}),
                         httpx.Response(200, json={'data': [{'id': 'private-test-key'}]})]:
            result, _ = self.request(response)
            self.assertEqual(result['reason'], 'invalid-response')
        for response in [httpx.Response(200, content=b'x'*262145), httpx.Response(200, json={'data':[{'id':'model'}]*501})]:
            result, _ = self.request(response)
            self.assertEqual(result['reason'], 'oversized')

    def test_invalid_endpoints_make_no_http_request(self):
        for base in ['file:///secret', 'https://name:key@fixture.invalid/v1', 'http://remote.invalid/v1', 'https://fixture.invalid/v1?key=secret']:
            result, calls = self.request(httpx.Response(200), {'baseUrl': base})
            self.assertEqual(result['status'], 'unavailable')
            self.assertEqual(calls, [])

    def test_network_error_is_redacted(self):
        with patch('cueflora_host.provider_check.httpx.Client', side_effect=httpx.ConnectError('private-test-key https://secret.invalid')):
            result = check_provider({'requestId':'check-1', 'provider': {'baseUrl':'https://fixture.invalid/v1'}})
        self.assertEqual(result['reason'], 'network')
        self.assertNotIn('private-test-key', json.dumps(result))

    def test_unconfigured_dispatch_never_invokes_inference(self):
        from . import handle_transcribe, handle_translate
        for function, target in [(handle_transcribe, 'cueflora_host.transcribe'), (handle_translate, 'cueflora_host.translate')]:
            with patch(target) as inference:
                output = function({'jobId': 'test', 'videoId': 'fixture1234', 'cues': [{'text':'hello'}], 'systemPrompt':'Translate'})
            inference.assert_not_called()
            self.assertTrue(output.get('error'))

    def test_keyless_translation_omits_authentication_but_keeps_one_request(self):
        from .translate import translate
        calls=[]
        def handler(request):
            calls.append(request)
            return httpx.Response(200,json={'choices':[{'message':{'content':'{"translations":[{"id":0,"text":"Hello"}]}'},'finish_reason':'stop'}]})
        client=httpx.Client(transport=httpx.MockTransport(handler))
        with patch('cueflora_host.translate.httpx.Client',return_value=client):
            result=translate([{'text':'你好'}],'Translate','','http://localhost:1234/v1','user-model')
        self.assertEqual(result['translations'],['Hello'])
        self.assertEqual(result['requestCount'],1)
        self.assertEqual(len(calls),1)
        self.assertNotIn('Authorization',calls[0].headers)

    def test_keyless_transcription_omits_authentication(self):
        from .whisper import transcribe
        with patch('cueflora_host.whisper.compress_audio',return_value='prepared.ogg'), \
             patch('cueflora_host.whisper.os.path.getsize',return_value=10), \
             patch('cueflora_host.whisper._probe_duration_seconds',return_value=1), \
             patch('cueflora_host.whisper._post_transcription',return_value={'segments':[]}) as post:
            transcribe('source.wav','','http://localhost:1234/v1','user-model',on_progress=lambda *args,**kwargs:None)
        self.assertEqual(post.call_args.args[2],{})
