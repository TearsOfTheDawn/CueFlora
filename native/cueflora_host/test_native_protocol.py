import io
import json
import struct
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from . import read_message, send_message, _read_exact, _tool_health, MAX_RESPONSE_BYTES


class NativeProtocolTests(unittest.TestCase):
    def test_health_uses_existing_tool_resolvers(self):
        with patch('cueflora_host.download._resolve_yt_dlp_executable', return_value='yt-dlp'), patch('cueflora_host.whisper._resolve_binary', return_value='tool'):
            self.assertTrue(all(item['available'] for item in _tool_health().values()))

    def test_reads_short_chunks(self):
        class ShortStream(io.BytesIO):
            def read(self, size=-1):
                return super().read(min(size, 2))
        self.assertEqual(_read_exact(ShortStream(b'123456'), 6), b'123456')

    def test_rejects_partial_header(self):
        with patch('sys.stdin', SimpleNamespace(buffer=io.BytesIO(b'12'))):
            with self.assertRaisesRegex(RuntimeError, 'header'):
                read_message()

    def test_oversized_response_becomes_small_correlated_error(self):
        output = io.BytesIO()
        with patch('sys.stdout', SimpleNamespace(buffer=output)):
            send_message({'jobId': 'job', 'requestCount': 1, 'text': 'x' * MAX_RESPONSE_BYTES})
        value = output.getvalue()
        self.assertEqual(struct.unpack('<I', value[:4])[0], len(value) - 4)
        result = json.loads(value[4:])
        self.assertEqual(result['jobId'], 'job')
        self.assertEqual(result['requestCount'], 1)
        self.assertIn('error', result)
