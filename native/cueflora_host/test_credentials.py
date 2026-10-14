import base64
import json
import os
import unittest
from unittest.mock import patch
from .credentials import protect, unprotect, handle_protect, resolve_key, METHOD
from .provider_security import validate_transport


class CredentialTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt', 'Real DPAPI needs Windows')
    def test_real_user_scoped_round_trip_and_rebinding(self):
        key = 'synthetic-only-Ω-秘密'
        credential = protect(key, 'transcription', 'https://service.invalid/v1/')
        self.assertEqual(unprotect(credential, 'transcription', 'https://service.invalid/v1'), key)
        self.assertNotIn(key.encode(), base64.b64decode(credential['blob']))
        for stage, endpoint in [('translation','https://service.invalid/v1'), ('transcription','https://else.invalid/v1')]:
            with self.assertRaises(ValueError): unprotect(credential, stage, endpoint)
        result = handle_protect({'requestId':'id','stage':'transcription','baseUrl':'https://new.invalid/v1',
                                 'previousBaseUrl':'https://service.invalid/v1','credential':credential})
        self.assertEqual(unprotect(result['credential'], 'transcription', 'https://new.invalid/v1'), key)
        self.assertNotIn(key, json.dumps(result))

    def test_malformed_ciphertext_and_context_never_return_a_key(self):
        for credential in [None, {}, {'schema':1,'method':METHOD,'blob':'bad!'}, {'schema':2,'method':METHOD,'blob':'AAAA'}]:
            with self.assertRaises(ValueError): unprotect(credential, 'translation', 'https://service.invalid')
        forged = {'schema':1,'method':METHOD,'blob':'AAAA'}
        with patch('cueflora_host.credentials._crypt', return_value=b'{"key":"synthetic-only"}'):
            with self.assertRaises(ValueError): unprotect(forged, 'translation', 'https://service.invalid')
        with patch('cueflora_host.credentials._crypt', side_effect=OSError('synthetic-only')):
            result = handle_protect({'requestId':'id','stage':'translation','baseUrl':'https://service.invalid','apiKey':'synthetic-only'})
        self.assertIn('no plaintext', result['error']); self.assertNotIn('synthetic-only', json.dumps(result))

    def test_nonwindows_protection_has_no_fallback(self):
        with patch('cueflora_host.credentials.os.name', 'posix'):
            with self.assertRaises(RuntimeError): protect('synthetic-only', 'translation', 'https://service.invalid')

    def test_ambiguous_credentials_are_rejected(self):
        with self.assertRaises(ValueError): resolve_key({'apiKey':'synthetic','credential':{}}, 'translation')

    def test_transport_profiles_and_exact_loopback(self):
        for address in ['http://localhost:8000/v1','http://127.0.0.1:8000','http://[::1]:8000']:
            self.assertTrue(validate_transport({'baseUrl':address}, 'https-remote'))
        for address in ['http://example.invalid','http://localhost.example','http://127.1','http://2130706433','http://0x7f000001','http://127.0.0.1.example']:
            with self.assertRaises(ValueError): validate_transport({'baseUrl':address,'allowRemoteHttp':True}, 'https-remote')
        self.assertEqual(validate_transport({'baseUrl':'http://example.invalid','allowRemoteHttp':True}), 'http://example.invalid')
        with self.assertRaises(ValueError): validate_transport({'baseUrl':'https://example.invalid'}, 'unknown')

    def test_invalid_transport_fails_before_download_or_inference(self):
        from . import handle_transcribe, handle_translate
        config = {'baseUrl':'http://remote.invalid','model':'synthetic','allowRemoteHttp':True}
        with patch('cueflora_host.download_audio') as download, patch('cueflora_host.translate') as translate:
            response = handle_transcribe({'jobId':'job','videoId':'U_V6Jqg7PV4','whisperConfig':config,'transportPolicy':'https-remote'})
            self.assertIn('error', response); download.assert_not_called()
            response = handle_translate({'jobId':'job','cues':[{'text':'synthetic'}],'systemPrompt':'synthetic','translateConfig':config,'transportPolicy':'https-remote'})
            self.assertEqual(response['requestCount'],0); translate.assert_not_called()

    @unittest.skipUnless(os.name == 'nt', 'Real DPAPI needs Windows')
    def test_protected_metadata_only_and_no_redirect(self):
        import httpx
        from .provider_check import check_provider
        key = 'synthetic-metadata-only'
        credential = protect(key, 'translation', 'https://service.invalid/v1')
        calls = []
        def handler(request):
            calls.append(request)
            self.assertEqual(request.headers['Authorization'], 'Bearer ' + key)
            return httpx.Response(302, headers={'Location':'https://else.invalid/'})
        client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)
        with patch('cueflora_host.provider_check.httpx.Client', return_value=client):
            result = check_provider({'requestId':'metadata','stage':'translation','transportPolicy':'https-remote',
                'provider':{'baseUrl':'https://service.invalid/v1','credential':credential}})
        self.assertEqual(len(calls), 1); self.assertEqual(calls[0].method, 'GET')
        self.assertEqual(result['reason'], 'http'); self.assertNotIn(key, json.dumps(result))
        self.assertNotIn(credential['blob'], json.dumps(result))

    def test_capture_excludes_credential_fields_and_secret_echoes(self):
        from .evidence import RunCapture
        from unittest.mock import Mock
        capture = Mock(capture_id='test'); wrapper = RunCapture(capture)
        wrapper.exclude_secrets('synthetic-key', 'synthetic-blob')
        wrapper.record('translation-response', {'apiKey':'synthetic-key','credential':{'blob':'synthetic-blob'},
            'nested':{'ciphertext':'synthetic-blob','text':'synthetic-key synthetic-blob', 'requestCount':1}})
        serialized = json.dumps(capture.record.call_args.args)
        self.assertNotIn('synthetic-key', serialized); self.assertNotIn('synthetic-blob', serialized)
        self.assertNotIn('ciphertext', serialized); self.assertIn('requestCount', serialized)
