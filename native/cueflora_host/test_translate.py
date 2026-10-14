import json
import unittest
from unittest.mock import Mock, patch

from cueflora_host.translate import TranslationError, translate


class TranslateSingleRequestTests(unittest.TestCase):
    @patch("cueflora_host.translate.httpx.Client")
    def test_failed_evidence_write_preserves_translation_and_request_count(self, client_factory):
        from .evidence import RunCapture
        client = self._client(self._translation_content([{"id": 0, "text": "Hello"}]))
        client_factory.return_value = client
        broken = Mock()
        broken.record.side_effect = OSError("disk full")
        capture = RunCapture(broken)
        result = translate([{"text": "你好"}], "translate", "key",
                           "http://localhost:11434/v1", "test", capture=capture)
        self.assertEqual(result["translations"], ["Hello"])
        self.assertEqual(result["requestCount"], 1)
        self.assertEqual(client.post.call_count, 1)
        self.assertFalse(capture.diagnostics()["complete"])
        self.assertEqual(capture.diagnostics()["stages"]["translation-response"], "incomplete")

    @patch("cueflora_host.translate.httpx.Client")
    def test_capture_does_not_mask_invalid_json_protocol_error(self, client_factory):
        client = self._client("")
        client.post.return_value.json.side_effect = ValueError("invalid JSON")
        client.post.return_value.text = "not JSON"
        client_factory.return_value = client
        capture = Mock()
        with self.assertRaises(TranslationError) as caught:
            translate([{"text": "你好"}], "translate", "local",
                      "http://localhost:11434/v1", "test", capture=capture)
        self.assertEqual(caught.exception.kind, "protocol")
        self.assertEqual(client.post.call_count, 1)
        self.assertEqual(capture.record.call_args.args[0], "translation-response")

    def _translation_content(self, items):
        return json.dumps({"translations": items})

    def _client(self, content, finish_reason="stop", usage=None):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "choices": [{
                "finish_reason": finish_reason,
                "message": {"content": content},
            }],
            "usage": usage or {},
        }
        client = Mock()
        client.__enter__ = Mock(return_value=client)
        client.__exit__ = Mock(return_value=False)
        client.post.return_value = response
        return client

    @patch("cueflora_host.translate.httpx.Client")
    def test_one_translate_call_makes_one_http_request(self, client_factory):
        client = self._client(self._translation_content([
            {"id": 1, "text": "World"},
            {"id": 0, "text": "Hello"},
        ]))
        client_factory.return_value = client
        result = translate(
            [
                {"startMs": 0, "endMs": 1000, "text": "你好"},
                {"startMs": 1000, "endMs": 2000, "text": "世界"},
            ],
            "translate",
            "key",
            "http://127.0.0.1:11434/v1",
            "qwen3.5:4b",
        )
        self.assertEqual(result["translations"], ["Hello", "World"])
        self.assertEqual(result["requestCount"], 1)
        self.assertEqual(client.post.call_count, 1)
        request_body = client.post.call_args.kwargs["json"]
        self.assertEqual(request_body["reasoning_effort"], "none")
        self.assertEqual(request_body["max_tokens"], 4096)
        source_payload = json.loads(request_body["messages"][1]["content"])
        self.assertEqual(source_payload, {"cues": [
            {"id": 0, "text": "你好"},
            {"id": 1, "text": "世界"},
        ]})
        output_schema = request_body["response_format"]["json_schema"]["schema"]
        self.assertEqual(output_schema["properties"]["translations"]["minItems"], 2)
        self.assertEqual(output_schema["properties"]["translations"]["maxItems"], 2)

    @patch("cueflora_host.translate.httpx.Client")
    def test_non_ollama_endpoint_keeps_provider_reasoning_default(self, client_factory):
        client = self._client(self._translation_content([
            {"id": 0, "text": "Hello"},
        ]))
        client_factory.return_value = client
        translate(
            [{"startMs": 0, "endMs": 1000, "text": "你好"}],
            "translate",
            "key",
            "https://generativelanguage.googleapis.com/v1beta/openai",
            "gemini-3.1-flash-lite-preview",
        )
        request_body = client.post.call_args.kwargs["json"]
        self.assertNotIn("reasoning_effort", request_body)

    @patch("cueflora_host.translate.httpx.Client")
    def test_invalid_structured_ids_are_recoverable_output_errors(self, client_factory):
        invalid_outputs = {
            "duplicate": [
                {"id": 0, "text": "Hello"},
                {"id": 0, "text": "World"},
            ],
            "non-integer": [
                {"id": "0", "text": "Hello"},
                {"id": 1, "text": "World"},
            ],
            "out-of-range": [
                {"id": 0, "text": "Hello"},
                {"id": 2, "text": "World"},
            ],
            "missing": [{"id": 0, "text": "Hello"}],
        }
        for name, items in invalid_outputs.items():
            with self.subTest(name=name):
                client = self._client(self._translation_content(items))
                client_factory.return_value = client
                with self.assertRaises(TranslationError) as raised:
                    translate(
                        [
                            {"startMs": 0, "endMs": 1000, "text": "你好"},
                            {"startMs": 1000, "endMs": 2000, "text": "世界"},
                        ],
                        "translate",
                        "key",
                        "http://127.0.0.1:11434/v1",
                        "qwen3.5:4b",
                    )
                self.assertEqual(raised.exception.kind, "output")
                self.assertEqual(client.post.call_count, 1)

    @patch("cueflora_host.translate.httpx.Client")
    def test_invalid_json_is_returned_to_browser_without_native_retry(self, client_factory):
        client = self._client(
            '{"translations": ["unfinished"',
            finish_reason="length",
            usage={
                "prompt_tokens": 100,
                "completion_tokens": 4096,
                "total_tokens": 4196,
                "completion_tokens_details": {"reasoning_tokens": 4096},
            },
        )
        client_factory.return_value = client
        with self.assertRaises(TranslationError) as raised:
            translate(
                [{"startMs": 0, "endMs": 1000, "text": "你好"}],
                "translate",
                "key",
                "http://127.0.0.1:11434/v1",
                "qwen3.5:4b",
            )
        self.assertEqual(raised.exception.kind, "output")
        self.assertEqual(raised.exception.finish_reason, "length")
        self.assertEqual(raised.exception.diagnostics["requestedOutputTokens"], 4096)
        self.assertEqual(raised.exception.diagnostics["completionTokens"], 4096)
        self.assertEqual(raised.exception.diagnostics["reasoningTokens"], 4096)
        self.assertEqual(client.post.call_count, 1)


if __name__ == "__main__":
    unittest.main()
