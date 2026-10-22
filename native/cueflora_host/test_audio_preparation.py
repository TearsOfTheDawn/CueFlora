import json
import subprocess
import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from .whisper import _validate_prepared_audio, compress_audio, _split_into_chunks, _probe_duration_seconds, transcribe
from .download import _validated_download_path


class AudioPreparationTests(unittest.TestCase):
    @patch('cueflora_host.whisper._resolve_binary', return_value='tool')
    def test_failed_chunk_command_rejects_nonempty_partial_output(self, resolve):
        with tempfile.TemporaryDirectory() as directory:
            def fail(command,**kwargs):
                Path(command[-1]).write_bytes(b'partial-invalid-audio')
                return SimpleNamespace(returncode=1)
            with patch('cueflora_host.whisper._probe_duration_seconds',return_value=30), \
                    patch('cueflora_host.whisper.subprocess.run',side_effect=fail):
                self.assertEqual(_split_into_chunks('source.ogg',20,10,directory),[])

    @patch('cueflora_host.whisper._resolve_binary', return_value='tool')
    def test_duration_probe_rejects_nonfinite_and_nonpositive_values(self, resolve):
        for value in ('nan','inf','-inf','0','-1'):
            with self.subTest(value=value),patch('cueflora_host.whisper.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout=value)):
                self.assertIsNone(_probe_duration_seconds('source.ogg'))

    def test_optional_audio_tool_evidence_failure_does_not_repeat_or_block_upload(self):
        from .evidence import RunCapture
        capture=RunCapture()
        with tempfile.TemporaryDirectory() as directory:
            audio=Path(directory)/'prepared.ogg';audio.write_bytes(b'synthetic-prepared-audio')
            with patch('cueflora_host.whisper.compress_audio',return_value=str(audio)), \
                    patch('cueflora_host.whisper._resolve_binary',return_value='tool'), \
                    patch('cueflora_host.whisper._probe_duration_seconds',return_value=1), \
                    patch('cueflora_host.whisper.subprocess.check_output',side_effect=subprocess.TimeoutExpired('tool',10)) as version, \
                    patch('cueflora_host.whisper._post_transcription',return_value={'text':'synthetic'}) as upload:
                self.assertEqual(transcribe(str(audio),'','https://fixture.invalid/v1','fixture',capture=capture),{'text':'synthetic'})
            upload.assert_called_once()
            self.assertEqual(version.call_args.kwargs['timeout'],10)
            self.assertEqual(version.call_args.kwargs['stdin'],subprocess.DEVNULL)
            self.assertEqual(capture.diagnostics()['stages']['audio-preparation'],'incomplete')

    def test_download_output_must_be_nonempty_and_inside_request_root(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); root = base/'processing'; root.mkdir()
            audio = root/'audio.ogg'; audio.write_bytes(b'synthetic-audio')
            self.assertEqual(_validated_download_path(str(audio),root),str(audio.resolve()))
            outside = base/'unrelated.ogg'; outside.write_bytes(b'private-data')
            with self.assertRaisesRegex(RuntimeError,'temporary processing'): _validated_download_path(str(outside),root)

    def test_missing_and_empty_download_outputs_fail_without_path_disclosure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); empty = root/'empty.ogg'; empty.touch()
            for path in (empty,root/'missing'):
                with self.assertRaises(RuntimeError) as caught: _validated_download_path(str(path),root)
                self.assertNotIn(str(root),str(caught.exception))

    def probe(self, info):
        return SimpleNamespace(returncode=0, stdout=json.dumps(info).encode())

    @patch('cueflora_host.whisper._resolve_binary', return_value='tool')
    @patch('cueflora_host.whisper.subprocess.run')
    def test_accepts_only_valid_production_audio(self, run, resolve):
        valid = {'streams': [{'codec_name': 'opus', 'sample_rate': '48000', 'channels': 1}], 'format': {'duration': '1.25'}}
        run.return_value = self.probe(valid)
        _validate_prepared_audio('prepared.ogg')
        for info in [{}, {**valid, 'streams': []}, {**valid, 'format': {'duration': 'nan'}},
                     {**valid, 'streams': [{'codec_name': 'aac', 'sample_rate': '48000', 'channels': 1}]}]:
            run.return_value = self.probe(info)
            with self.assertRaisesRegex(RuntimeError, 'validation failed'):
                _validate_prepared_audio('prepared.ogg')

    @patch('cueflora_host.whisper._resolve_binary', return_value=None)
    def test_missing_tools_fail_closed(self, resolve):
        with self.assertRaisesRegex(RuntimeError, 'ffmpeg'):
            compress_audio('original.wav')
        with self.assertRaisesRegex(RuntimeError, 'ffprobe'):
            _validate_prepared_audio('prepared.ogg')

    @patch('cueflora_host.whisper._resolve_binary', return_value='tool')
    @patch('cueflora_host.whisper.os.path.getsize', return_value=100)
    @patch('cueflora_host.whisper.subprocess.run')
    def test_encoding_failure_and_timeout_never_return_original(self, run, size, resolve):
        run.return_value = SimpleNamespace(returncode=1)
        with self.assertRaisesRegex(RuntimeError, 'exited'):
            compress_audio('private-source.wav')
        run.side_effect = subprocess.TimeoutExpired(['tool', 'private-source.wav'], 120)
        with self.assertRaises(RuntimeError) as caught:
            compress_audio('private-source.wav')
        self.assertNotIn('private-source', str(caught.exception))

    @patch('cueflora_host.whisper._resolve_binary', return_value='tool')
    @patch('cueflora_host.whisper.os.path.getsize', return_value=100)
    @patch('cueflora_host.whisper.os.path.exists', return_value=False)
    @patch('cueflora_host.whisper.subprocess.run', return_value=SimpleNamespace(returncode=0))
    def test_success_exit_without_output_is_rejected(self, run, exists, size, resolve):
        with self.assertRaisesRegex(RuntimeError, 'no usable'):
            compress_audio('original.wav')
