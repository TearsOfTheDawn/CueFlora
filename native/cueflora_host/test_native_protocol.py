import io
import json
import struct
import unittest
from unittest.mock import call, patch
from types import SimpleNamespace
from . import read_message, send_message, _read_exact, _tool_health, MAX_RESPONSE_BYTES


class NativeProtocolTests(unittest.TestCase):
    def test_health_uses_existing_tool_resolvers(self):
        with patch('cueflora_host.download._resolve_yt_dlp_executable', return_value='yt-dlp') as downloader, \
                patch('cueflora_host.whisper._resolve_binary', return_value='tool') as audio, \
                patch('cueflora_host.runtime_tools.resolve_deno', return_value='deno') as deno:
            self.assertEqual(_tool_health(), {
                name: {'available': True} for name in ('yt-dlp', 'ffmpeg', 'ffprobe', 'deno')
            })
            downloader.assert_called_once_with()
            self.assertEqual(audio.call_args_list, [call('ffmpeg'), call('ffprobe')])
            deno.assert_called_once_with()

    def test_health_reports_each_missing_tool_without_hiding_healthy_tools(self):
        for missing in ('yt-dlp', 'ffmpeg', 'ffprobe', 'deno'):
            for raises in (False, True):
                with self.subTest(missing=missing, raises=raises):
                    def resolve(name):
                        if name != missing:
                            return name
                        if raises:
                            raise RuntimeError('synthetic resolver failure ' + 'x' * 300)
                        return None

                    with patch('cueflora_host.download._resolve_yt_dlp_executable', side_effect=lambda: resolve('yt-dlp')), \
                            patch('cueflora_host.whisper._resolve_binary', side_effect=resolve), \
                            patch('cueflora_host.runtime_tools.resolve_deno', side_effect=lambda: resolve('deno')):
                        health = _tool_health()
                    self.assertEqual(set(health), {'yt-dlp', 'ffmpeg', 'ffprobe', 'deno'})
                    for name, result in health.items():
                        self.assertEqual(result['available'], name != missing)
                        if name == missing and raises:
                            self.assertEqual(len(result['error']), 240)
                        else:
                            self.assertNotIn('error', result)

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
