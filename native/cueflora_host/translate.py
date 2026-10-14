"""Single-attempt LLM subtitle translation via a chat completions API.

Batching, positional salvage, retry, splitting, and call budgets intentionally
live in the TypeScript content-script layer. One call to ``translate`` performs
exactly one physical HTTP request so the browser-side budget is meaningful.
"""

import json
import re
import sys
import time
from urllib.parse import urlparse

import httpx


class TranslationError(RuntimeError):
    """Structured native error returned to the TypeScript recovery owner."""

    def __init__(
        self, message, kind="protocol", finish_reason=None, diagnostics=None
    ):
        super().__init__(message)
        self.kind = kind
        self.finish_reason = finish_reason
        self.diagnostics = diagnostics or {}


def _log(msg):
    print(f"[cueflora translate] {msg}", file=sys.stderr, flush=True)


def _is_ollama_openai_endpoint(base_url):
    """Identify the conventional local Ollama OpenAI-compatible endpoint."""
    try:
        parsed = urlparse(base_url)
        return parsed.hostname in {"127.0.0.1", "localhost", "::1"} and parsed.port == 11434
    except ValueError:
        return False


def _response_diagnostics(data, max_tokens, duration_ms, reasoning_effort):
    usage = data.get("usage") if isinstance(data, dict) else None
    usage = usage if isinstance(usage, dict) else {}
    completion_details = usage.get("completion_tokens_details")
    completion_details = completion_details if isinstance(completion_details, dict) else {}
    values = {
        "requestedOutputTokens": max_tokens,
        "durationMs": duration_ms,
        "reasoningEffort": reasoning_effort,
        "promptTokens": usage.get("prompt_tokens"),
        "completionTokens": usage.get("completion_tokens"),
        "totalTokens": usage.get("total_tokens"),
        "reasoningTokens": completion_details.get("reasoning_tokens"),
    }
    return {key: value for key, value in values.items() if value is not None}


def _ordered_translation_texts(parsed, cue_count, finish_reason, diagnostics):
    """Validate model cue IDs and return only positional display strings."""
    if not isinstance(parsed, dict) or not isinstance(parsed.get("translations"), list):
        raise TranslationError(
            'LLM returned JSON without the required "translations" array.',
            kind="output",
            finish_reason=finish_reason,
            diagnostics=diagnostics,
        )

    items = parsed["translations"]
    if len(items) != cue_count:
        raise TranslationError(
            f"LLM returned {len(items)}/{cue_count} structured translations.",
            kind="output",
            finish_reason=finish_reason,
            diagnostics=diagnostics,
        )

    by_id = {}
    for position, item in enumerate(items):
        if not isinstance(item, dict) or set(item) != {"id", "text"}:
            raise TranslationError(
                f"Translation item {position} must contain exactly integer id and string text.",
                kind="output",
                finish_reason=finish_reason,
                diagnostics=diagnostics,
            )
        cue_id = item["id"]
        text = item["text"]
        if isinstance(cue_id, bool) or not isinstance(cue_id, int):
            raise TranslationError(
                f"Translation item {position} has a non-integer id.",
                kind="output",
                finish_reason=finish_reason,
                diagnostics=diagnostics,
            )
        if cue_id < 0 or cue_id >= cue_count:
            raise TranslationError(
                f"Translation item {position} has out-of-range id {cue_id}.",
                kind="output",
                finish_reason=finish_reason,
                diagnostics=diagnostics,
            )
        if cue_id in by_id:
            raise TranslationError(
                f"LLM returned duplicate translation id {cue_id}.",
                kind="output",
                finish_reason=finish_reason,
                diagnostics=diagnostics,
            )
        if not isinstance(text, str):
            raise TranslationError(
                f"Translation item {position} has non-string text.",
                kind="output",
                finish_reason=finish_reason,
                diagnostics=diagnostics,
            )
        by_id[cue_id] = text

    missing = [cue_id for cue_id in range(cue_count) if cue_id not in by_id]
    if missing:
        raise TranslationError(
            f"LLM omitted translation ids: {missing}.",
            kind="output",
            finish_reason=finish_reason,
            diagnostics=diagnostics,
        )
    return [by_id[cue_id] for cue_id in range(cue_count)]


def translate(cues, system_prompt, api_key, base_url, model, on_progress=None, capture=None, source_indexes=None):
    """Perform one chat-completions request and return raw positional outputs."""
    if on_progress is None:
        on_progress = lambda stage, message: None

    cues_text = json.dumps(
        {"cues": [{"id": i, "text": cue["text"]} for i, cue in enumerate(cues)]},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    url = base_url.rstrip("/") + "/chat/completions"
    on_progress("translate", "Waiting for LLM response...")
    _log(f"Requesting translation: {len(cues)} cues, model={model}")

    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "subtitle_translation",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "translations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "integer",
                                    "minimum": 0,
                                    "maximum": len(cues) - 1,
                                },
                                "text": {"type": "string"},
                            },
                            "required": ["id", "text"],
                            "additionalProperties": False,
                        },
                        "minItems": len(cues),
                        "maxItems": len(cues),
                    }
                },
                "required": ["translations"],
                "additionalProperties": False,
            },
        },
    }

    timeout_s = max(180, len(cues) // 5)
    max_tokens = max(4096, len(cues) * 25)
    reasoning_effort = "none" if _is_ollama_openai_endpoint(base_url) else None
    request_body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": cues_text},
        ],
        "temperature": 0.3,
        "max_tokens": max_tokens,
        "response_format": response_format,
    }
    if reasoning_effort:
        request_body["reasoning_effort"] = reasoning_effort
    request_record = capture.record("translation-request", {"body": request_body,
        "sourceCues": cues, "sourceIndexes": source_indexes, "endpoint": base_url}) if capture else None

    _log(
        f"Request settings: max_tokens={max_tokens}, "
        f"reasoning_effort={reasoning_effort or 'provider-default'}"
    )
    started_at = time.monotonic()
    try:
        with httpx.Client(timeout=timeout_s) as client:
            response = client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    **({"Authorization": f"Bearer {api_key}"} if api_key else {}),
                },
                json=request_body,
            )
    except httpx.TimeoutException as exc:
        raise TranslationError(
            f"LLM API request timed out ({timeout_s}s)",
            kind="network",
            diagnostics={
                "requestedOutputTokens": max_tokens,
                "reasoningEffort": reasoning_effort,
            },
        ) from exc
    except httpx.RequestError as exc:
        raise TranslationError(
            f"LLM API request failed: {type(exc).__name__}",
            kind="network",
            diagnostics={
                "requestedOutputTokens": max_tokens,
                "reasoningEffort": reasoning_effort,
            },
        ) from exc

    duration_ms = round((time.monotonic() - started_at) * 1000)
    if capture:
        try:
            captured_body = response.json()
        except ValueError:
            captured_body = {"invalidJson": True, "raw": response.text}
        capture.record("translation-response", {"requestRecord": request_record,
            "status": response.status_code, "durationMs": duration_ms,
            "body": captured_body})
    if response.status_code != 200:
        kind = "auth" if response.status_code in (401, 403) else "http"
        raise TranslationError(
            f"LLM API returned HTTP {response.status_code}",
            kind=kind,
            diagnostics={
                "requestedOutputTokens": max_tokens,
                "durationMs": duration_ms,
                "reasoningEffort": reasoning_effort,
            },
        )

    try:
        data = response.json()
        diagnostics = _response_diagnostics(
            data, max_tokens, duration_ms, reasoning_effort
        )
        choice = data["choices"][0]
        finish_reason = choice.get("finish_reason", "unknown")
        content = choice["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise TranslationError(
            f"LLM returned an invalid chat-completions response: {exc}",
            kind="protocol",
            diagnostics={
                "requestedOutputTokens": max_tokens,
                "durationMs": duration_ms,
                "reasoningEffort": reasoning_effort,
            },
        ) from exc

    on_progress("translate", "Parsing response...")
    _log(
        f"Raw response length: {len(content)} chars, finish_reason={finish_reason}, "
        f"duration_ms={duration_ms}, prompt_tokens={diagnostics.get('promptTokens')}, "
        f"completion_tokens={diagnostics.get('completionTokens')}, "
        f"reasoning_tokens={diagnostics.get('reasoningTokens')}"
    )

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        cleaned = content.replace("```json", "").replace("```", "").strip()
        match = re.search(r"[\[{][\s\S]*[\]}]", cleaned)
        if match:
            cleaned = match.group(0)
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise TranslationError(
                f"LLM returned invalid JSON (finish_reason={finish_reason}).",
                kind="output",
                finish_reason=finish_reason,
                diagnostics=diagnostics,
            ) from exc

    translations = _ordered_translation_texts(
        parsed, len(cues), finish_reason, diagnostics
    )
    _log(
        f"Single translation request complete: {len(translations)} outputs, "
        f"finish_reason={finish_reason}"
    )
    return {
        "translations": translations,
        "finishReason": finish_reason,
        "requestCount": 1,
        **diagnostics,
    }
