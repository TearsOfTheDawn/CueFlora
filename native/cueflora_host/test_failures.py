import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import httpx
from .failures import OperationFailure, http_failure
from .whisper import _post_transcription
from . import handle_transcribe


class FailureTests(unittest.TestCase):
    def test_http_statuses_are_classified_without_error_body_or_key(self):
        for status,code in [(400,'provider-request'),(401,'provider-auth'),(402,'provider-payment'),(403,'provider-permission'),
                            (413,'provider-request'),(415,'provider-request'),(422,'provider-request'),(429,'provider-rate-limit'),(503,'provider-unavailable')]:
            with self.subTest(status=status),tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'synthetic.ogg';path.write_bytes(b'synthetic audio')
                client=httpx.Client(transport=httpx.MockTransport(lambda _:httpx.Response(status,text='synthetic-private-key https://private.invalid')))
                with patch('cueflora_host.whisper.httpx.Client',return_value=client),self.assertRaises(OperationFailure) as caught:
                    _post_transcription(str(path),'https://provider.invalid/audio/transcriptions',{}, {},'audio/ogg',1)
                self.assertEqual(caught.exception.detail,{'stage':'transcription','code':code,'httpStatus':status})
                self.assertNotIn('private',str(caught.exception))
        self.assertEqual(http_failure('upload',302).detail['code'],'invalid-response')
    def test_transcription_records_stage_without_leaking_exception_text(self):
        message={'jobId':'test','videoId':'3gwqsqh2ATk','whisperConfig':{'baseUrl':'https://provider.invalid/v1','model':'synthetic','apiKey':'synthetic-key'}}
        with patch('cueflora_host.RunCapture.open',return_value=None),patch('cueflora_host.send_message'):
            with patch('cueflora_host.download_audio',side_effect=RuntimeError('synthetic-key https://private.invalid')):
                result=handle_transcribe(message)
            self.assertEqual(result['failure'],{'stage':'download','code':'download-failed'})
            self.assertNotIn('synthetic-key',json.dumps(result));self.assertNotIn('private.invalid',json.dumps(result))
            with patch('cueflora_host.download_audio',return_value='synthetic.ogg'),patch('cueflora_host.transcribe',side_effect=OperationFailure('transcription','provider-auth',401)):
                self.assertEqual(handle_transcribe(message)['failure']['httpStatus'],401)
            with patch('cueflora_host.resolve_key',side_effect=ValueError('synthetic-key')):
                self.assertEqual(handle_transcribe(message)['failure']['code'],'credential-unavailable')


if __name__=='__main__':unittest.main()
