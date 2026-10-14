import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from .evidence import Capture, RunCapture, normalization_mapping, sanitized, sha256


class EvidenceTests(unittest.TestCase):
    def test_optional_metadata_parsing_failure_is_nonfatal_and_marks_stage(self):
        capture = RunCapture()
        self.assertIsNone(capture.record_lazy("source-metadata", lambda: json.loads("invalid")))
        self.assertEqual(capture.diagnostics(), {"complete": False, "stages": {"source-metadata": "incomplete"}})

    def test_direct_evaluation_capture_keeps_metadata_parsing_strict(self):
        capture = Capture(None, "capture")
        with self.assertRaises(ValueError):
            capture.record_lazy("source-metadata", lambda: json.loads("invalid"))
    def test_capture_creation_failure_is_reported_without_private_error(self):
        with patch.dict(os.environ, {"CUEFLORA_EVIDENCE_DIR": "unused"}), patch.object(
                Capture, "create", side_effect=OSError("private-path")):
            capture = RunCapture.open("create", "U_V6Jqg7PV4", "job")
            capture.preserve("upload", "private-file")
            diagnostics = capture.diagnostics()
            self.assertFalse(diagnostics["complete"])
            self.assertNotIn("private", json.dumps(diagnostics))
            self.assertEqual(diagnostics["stages"]["upload"], "incomplete")

    def test_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(Capture.create("U_V6Jqg7PV4", "job"))

    def test_append_only_bytes_and_job_binding(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {"CUEFLORA_EVIDENCE_DIR": root}):
            capture = Capture.create("U_V6Jqg7PV4", "job")
            source = Path(root) / "input.ogg"
            source.write_bytes(b"exact-upload-bytes")
            saved = capture.preserve("upload", source)
            self.assertEqual(sha256(source), saved["sha256"])
            self.assertEqual((capture.path / saved["file"]).read_bytes(), source.read_bytes())
            a = capture.record("same", {"value": 1})
            b = capture.record("same", {"value": 2})
            self.assertNotEqual(a, b)
            self.assertEqual(json.loads((capture.path / a).read_text())["value"], 1)
            self.assertEqual(Capture.resume(capture.capture_id, "job").path, capture.path)
            with self.assertRaises(ValueError):
                Capture.resume(capture.capture_id, "other-job")
            with self.assertRaises(ValueError):
                Capture.resume("../../anything", "job")

    def test_credentials_and_signed_urls_are_excluded_but_asr_tokens_remain(self):
        cleaned = sanitized({"apiKey": "secret", "Authorization": "Bearer secret",
            "url": "https://media/video?sig=secret", "endpoint": "https://user:pass@host/path?key=secret",
            "words": [{"token": "你", "start": 1}], "max_tokens": 4096})
        self.assertNotIn("secret", json.dumps(cleaned))
        self.assertEqual(cleaned["endpoint"], "https://host/path")
        self.assertEqual(cleaned["words"][0]["token"], "你")

    def test_word_mapping_matches_text_and_original_timing(self):
        raw = {"segments": [{"start": 0, "end": 1, "words": [{"word": "你", "start": .1, "end": .2}]}]}
        cue = {"startMs": 100, "endMs": 1500, "text": "你", "words": [{"text": "你", "startMs": 100, "endMs": 200}]}
        mapping = normalization_mapping(raw, [cue])[0]
        self.assertEqual(mapping["wordAssociations"][0]["rawWordIds"], ["segment:0:word:0"])
