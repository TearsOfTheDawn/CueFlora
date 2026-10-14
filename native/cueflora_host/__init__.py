#!/usr/bin/env python3
"""Native messaging host for cueflora browser extension.

Receives JSON messages from the extension via stdin, uses yt-dlp (system CLI) to
download the cheapest YouTube audio, sends it to a Whisper-compatible API for
transcription, and returns timestamped cues via stdout.

Protocol: Native messaging (length-prefixed JSON on stdin/stdout, same for Firefox and Chrome).
"""

import json
import os
import struct
import sys
import tempfile
from importlib.metadata import PackageNotFoundError, version

MAX_MESSAGE_BYTES = 8 * 1024 * 1024
MAX_RESPONSE_BYTES = 1024 * 1024

from .download import download_audio
from .translate import TranslationError, translate
from .whisper import parse_cues, transcribe
from .evidence import Capture, RunCapture, normalization_mapping
from .credentials import resolve_key, redact
from .provider_security import validate_transport


def _tool_health():
    from .download import _resolve_yt_dlp_executable
    from .whisper import _resolve_binary
    from .runtime_tools import resolve_deno
    checks = {}
    for name, resolver in (("yt-dlp", _resolve_yt_dlp_executable), ("ffmpeg", lambda: _resolve_binary("ffmpeg")), ("ffprobe", lambda: _resolve_binary("ffprobe")), ("deno", resolve_deno)):
        try:
            checks[name] = {"available": bool(resolver())}
        except Exception as error:
            checks[name] = {"available": False, "error": str(error)[:240]}
    return checks


def _read_exact(stream, size):
    result = bytearray()
    while len(result) < size:
        chunk = stream.read(size - len(result))
        if not chunk:
            break
        result.extend(chunk)
    return bytes(result)


def read_message():
    raw_length = _read_exact(sys.stdin.buffer, 4)
    if not raw_length:
        return None
    if len(raw_length) != 4:
        raise RuntimeError("Truncated native message header")
    length = struct.unpack("<I", raw_length)[0]
    if length > MAX_MESSAGE_BYTES:
        raise RuntimeError(f"Native message exceeds {MAX_MESSAGE_BYTES} byte limit")
    data = _read_exact(sys.stdin.buffer, length)
    if len(data) != length:
        raise RuntimeError("Truncated native message")
    value = json.loads(data)
    if not isinstance(value, dict):
        raise RuntimeError("Native message must be an object")
    return value


def send_message(obj):
    encoded = json.dumps(obj).encode("utf-8")
    if len(encoded) > MAX_RESPONSE_BYTES:
        encoded = json.dumps({"jobId": obj.get("jobId"),
            "error": "Native result exceeds the browser's 1 MiB response limit",
            "requestCount": obj.get("requestCount", 0)}).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def handle_transcribe(msg):
    job_id = msg.get("jobId")
    video_id = msg.get("videoId")
    whisper_config = msg.get("whisperConfig")

    if not video_id:
        return {"jobId": job_id, "error": "Missing videoId"}
    if not isinstance(whisper_config, dict) or not whisper_config.get('baseUrl') or not whisper_config.get('model'):
        return {"jobId": job_id, "error": "Transcription service address and model must be configured"}

    try:
        base_url = validate_transport(whisper_config, msg.get('transportPolicy', 'preview'))
        api_key = resolve_key(whisper_config, 'transcription')
    except Exception:
        return {'jobId': job_id, 'error': 'Invalid service transport or protected key. Open settings or upgrade/repair CueFlora.'}
    model = whisper_config['model']
    language = whisper_config.get("language")
    prompt = whisper_config.get("prompt")
    max_parallel = whisper_config.get("maxParallel")
    try:
        max_parallel = int(max_parallel) if max_parallel is not None else None
    except (TypeError, ValueError):
        max_parallel = None

    mb_per_req = whisper_config.get("mbPerReq")
    try:
        mb_per_req = int(mb_per_req) if mb_per_req is not None else None
    except (TypeError, ValueError):
        mb_per_req = None

    try:
        capture = RunCapture.open("create", video_id, job_id)
        if capture:
            capture.exclude_secrets(api_key, whisper_config.get('credential', {}).get('blob', ''))
            from . import whisper
            capture.record("normalizer-source", capture.preserve("normalizer", whisper.__file__))
        with tempfile.TemporaryDirectory(prefix="cueflora_") as tmp_dir:
            send_message(
                {
                    "type": "progress",
                    "jobId": job_id,
                    "stage": "download",
                    "message": "Starting download...",
                }
            )
            audio_path = download_audio(video_id, tmp_dir, job_id=job_id, capture=capture)

            def on_progress(stage, message, percent=None, raw=None):
                msg = {
                    "type": "progress",
                    "jobId": job_id,
                    "stage": stage,
                    "message": redact(message, api_key),
                }
                if percent is not None:
                    msg["percent"] = percent
                # Raw provider payloads belong only in redacted opt-in capture,
                # never in progress/diagnostic messages sent to the browser.
                send_message(msg)

            result = transcribe(
                audio_path,
                api_key,
                base_url,
                model,
                language=language,
                prompt=prompt,
                parallel_uploads=max_parallel,
                mb_per_req=mb_per_req,
                on_progress=on_progress,
                capture=capture,
            )

            diagnostics = {}
            cues = parse_cues(result, diagnostics=diagnostics)
            if capture:
                capture.record("normalization", {"raw": result, "cues": cues,
                    "mapping": normalization_mapping(result, cues), "diagnostics": diagnostics})
                diagnostics["captureId"] = capture.capture_id
                diagnostics["evidence"] = capture.diagnostics()

            return {"jobId": job_id, "cues": cues, "diagnostics": diagnostics}

    except Exception as e:
        return {"jobId": job_id, "error": redact(e, api_key)}


def handle_translate(msg):
    job_id = msg.get("jobId")
    cues = msg.get("cues")
    system_prompt = msg.get("systemPrompt")
    translate_config = msg.get("translateConfig")

    if not cues:
        return {"jobId": job_id, "error": "Missing cues", "errorKind": "protocol", "requestCount": 0}
    if not system_prompt:
        return {"jobId": job_id, "error": "Missing systemPrompt", "errorKind": "protocol", "requestCount": 0}
    if not isinstance(translate_config, dict) or not translate_config.get('baseUrl') or not translate_config.get('model'):
        return {"jobId": job_id, "error": "Translation service address and model must be configured", "errorKind": "protocol", "requestCount": 0}

    try:
        base_url = validate_transport(translate_config, msg.get('transportPolicy', 'preview'))
        api_key = resolve_key(translate_config, 'translation')
    except Exception:
        return {'jobId': job_id, 'error': 'Invalid service transport or protected key. Open settings or upgrade/repair CueFlora.', 'errorKind': 'protocol', 'requestCount': 0}
    model = translate_config['model']

    try:
        capture = RunCapture.open("resume", msg.get("captureId"), job_id)
        if capture:
            capture.exclude_secrets(api_key, translate_config.get('credential', {}).get('blob', ''))
            capture.record("translation-mapping", {"sourceIndexes": msg.get("sourceIndexes"),
                "cues": cues})
        def on_progress(stage, message):
            send_message(
                {
                    "type": "progress",
                    "jobId": job_id,
                    "stage": stage,
                    "message": redact(message, api_key),
                }
            )

        result = translate(
            cues,
            system_prompt,
            api_key,
            base_url,
            model,
            on_progress=on_progress,
            capture=capture,
            source_indexes=msg.get("sourceIndexes"),
        )
        if capture:
            result["evidence"] = capture.diagnostics()
        return {"jobId": job_id, **result}

    except TranslationError as e:
        result = {
            "jobId": job_id,
            "error": redact(e, api_key),
            "errorKind": e.kind,
            "requestCount": 1,
        }
        if e.finish_reason:
            result["finishReason"] = e.finish_reason
        result.update(e.diagnostics)
        return result
    except Exception as e:
        return {
            "jobId": job_id,
            "error": redact(e, api_key),
            "errorKind": "protocol",
            "requestCount": 0,
        }


def main():
    while True:
        msg = read_message()
        if msg is None:
            break

        msg_type = msg.get("type")

        if msg_type == "PING":
            try:
                host_version = version("cueflora-host")
            except PackageNotFoundError:
                host_version = "development (uninstalled)"
                if getattr(sys, 'frozen', False):
                    try:
                        from pathlib import Path
                        metadata = json.loads((Path(sys.executable).parent / 'runtime-manifest.json').read_text(encoding='utf-8'))
                        candidate = metadata.get('hostVersion')
                        if isinstance(candidate, str) and len(candidate) <= 64:
                            host_version = candidate
                    except (OSError, ValueError):
                        host_version = 'unknown-bundle-version'
            send_message({"status": "PONG", "version": host_version, "tools": _tool_health(),
                          "capabilities": {"credentialProtection": 'windows-dpapi-v1' if os.name == 'nt' else None}})

        elif msg_type == 'CREDENTIAL_PROTECT':
            from .credentials import handle_protect
            send_message(handle_protect(msg))

        elif msg_type == 'PROVIDERS_CHECK':
            from .provider_check import check_provider
            send_message(check_provider(msg))

        elif msg_type == "TRANSCRIBE_NATIVE":
            result = handle_transcribe(msg)
            send_message(result)

        elif msg_type == "TRANSLATE_NATIVE":
            result = handle_translate(msg)
            send_message(result)

        elif msg_type == "CAPTURE_PRESENTATION":
            try:
                capture = Capture.resume(msg.get("captureId"), msg.get("jobId"))
                if not capture:
                    raise ValueError("Capture is not enabled")
                capture.record("presentation", {"sourceCues": msg.get("sourceCues"),
                    "translations": msg.get("translations"), "displayCues": msg.get("displayCues"),
                    "sourceIndexes": msg.get("sourceIndexes"), "diagnostics": msg.get("diagnostics")})
                send_message({"jobId": msg.get("jobId"), "captured": True})
            except (ValueError, OSError) as exc:
                send_message({"jobId": msg.get("jobId"), "error": str(exc)})

        else:
            send_message({"error": f"Unknown message type: {msg_type}"})


if __name__ == "__main__":
    main()
