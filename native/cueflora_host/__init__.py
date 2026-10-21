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
import queue
import threading
from importlib.metadata import PackageNotFoundError, version

MAX_MESSAGE_BYTES = 8 * 1024 * 1024
MAX_RESPONSE_BYTES = 1024 * 1024
_write_lock = threading.RLock()

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
    with _write_lock:
        sys.stdout.buffer.write(struct.pack("<I", len(encoded)))
        sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()


def handle_transcribe(msg):
    from .failures import OperationFailure
    job_id = msg.get("jobId")
    video_id = msg.get("videoId")
    whisper_config = msg.get("whisperConfig")

    if not video_id:
        return {"jobId": job_id, "error": "Missing videoId"}
    if not isinstance(whisper_config, dict) or not whisper_config.get('baseUrl') or not whisper_config.get('model'):
        return {"jobId": job_id, "error": "Transcription service address and model must be configured"}

    try:
        base_url = validate_transport(whisper_config, msg.get('transportPolicy', 'preview'))
    except Exception:
        failure = OperationFailure('credentials', 'transport-policy')
        return {'jobId': job_id, 'error': str(failure), 'failure': failure.detail}
    try:
        api_key = resolve_key(whisper_config, 'transcription')
    except Exception:
        failure = OperationFailure('credentials', 'credential-unavailable')
        return {'jobId': job_id, 'error': str(failure), 'failure': failure.detail}
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

    active_stage = 'download'
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
            audio_path = download_audio(video_id, tmp_dir, job_id=job_id, capture=capture, **({'cancel':msg['_cancel']} if '_cancel' in msg else {}))

            def on_progress(stage, message, percent=None, raw=None):
                nonlocal active_stage
                active_stage = {'compress': 'audio-preparation', 'prepare': 'audio-preparation', 'chunk': 'audio-preparation',
                                'upload': 'upload', 'transcribe': 'transcription', 'merge': 'transcription'}.get(stage, active_stage)
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

            active_stage = 'audio-preparation'
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

    except OperationFailure as error:
        return {'jobId': job_id, 'error': str(error), 'failure': error.detail}
    except Exception:
        code = 'download-failed' if active_stage == 'download' else 'audio-preparation-failed' if active_stage == 'audio-preparation' else 'invalid-response'
        if msg.get('_cancel') is not None and msg['_cancel'].is_set(): code = 'cancelled'
        failure = OperationFailure(active_stage, code)
        return {'jobId': job_id, 'error': str(failure), 'failure': failure.detail}


def handle_translate(msg):
    job_id = msg.get("jobId")
    cues = msg.get("cues")
    system_prompt = msg.get("systemPrompt")
    translate_config = msg.get("translateConfig")
    if isinstance(translate_config,dict) and translate_config.get('backend') == 'chatgpt':
        if not cues or not system_prompt or not translate_config.get('model') or not translate_config.get('accountRef'):
            return {'jobId':job_id,'error':'Choose a ChatGPT account and model in settings.','errorKind':'protocol','requestCount':0}
        try:
            from .chatgpt_translate import translate as subscription_translate
            capture = RunCapture.open('resume',msg.get('captureId'),job_id)
            result = subscription_translate(cues,system_prompt,translate_config['accountRef'],translate_config['model'],
                on_progress=lambda stage,message:send_message({'type':'progress','jobId':job_id,'stage':stage,'message':message}),
                capture=capture,source_indexes=msg.get('sourceIndexes'))
            if capture: result['evidence']=capture.diagnostics()
            return {'jobId':job_id,**result}
        except TranslationError as error:
            return {'jobId':job_id,'error':str(error),'errorKind':error.kind,'requestCount':1,'failure':error.failure}
        except Exception:
            return {'jobId':job_id,'error':'ChatGPT account is unavailable. Sign in again; no paid API fallback was used.','errorKind':'auth','requestCount':0}

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
            "failure": e.failure,
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
    run_lease = None
    incoming = queue.Queue(maxsize=4)
    closed = threading.Event()
    tasks = {}
    def read_input():
        try:
            while True:
                item = read_message()
                if item is None: break
                if item.get('type') == 'TASK_CANCEL':
                    event=tasks.get(item.get('taskId'))
                    if event: event.set()
                    continue
                if item.get('type') == 'TASK_START':
                    event=threading.Event(); tasks[item.get('taskId')]=event; item['_cancel']=event
                elif item.get('type') == 'TRANSCRIBE_NATIVE': item['_cancel']=closed
                incoming.put(item)
        except Exception:
            pass  # Framing failure closes this connection; never expose raw payloads.
        finally:
            closed.set()
            for event in tuple(tasks.values()): event.set()
            incoming.put(None)
    threading.Thread(target=read_input,daemon=True).start()
    while True:
        msg = incoming.get()
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
                          "capabilities": {"credentialProtection": 'windows-dpapi-v1' if os.name == 'nt' else None,
                            'chatgpt':'chatgpt-translation-v1' if os.name == 'nt' else None,
                            'runLeases':'run-leases-v1' if os.name == 'nt' else None,
                            'updates':'paired-updates-v1' if os.name == 'nt' else None}})

        elif msg_type == 'RUN_LEASE':
            try:
                from .activity import RunLease
                if run_lease is not None:raise RuntimeError('Lease already acquired')
                run_lease=RunLease();run_lease.__enter__()
                send_message({'requestId':msg.get('requestId'),'leased':True})
            except Exception:
                send_message({'requestId':msg.get('requestId'),'error':'CueFlora is installing or activity tracking is unavailable. Retry after Setup finishes.'})

        elif msg_type == 'TASK_START':
            task_id=msg.get('taskId'); operation=msg.get('operation')
            if not isinstance(task_id,str) or not __import__('re').fullmatch(r'[a-f0-9-]{36}',task_id):
                send_message({'taskId':task_id,'type':'task','status':'error','reason':'invalid-request'}); continue
            send_message({'type':'task','taskId':task_id,'status':'started'})
            try:
                if operation == 'chatgpt-login':
                    from .chatgpt_auth import login
                    result=login(msg['_cancel'],lambda stage:send_message({'type':'task','taskId':task_id,'status':'progress','stage':stage}),msg.get('accountRef'))
                elif operation in ('chatgpt-models','chatgpt-disconnect'):
                    from .chatgpt_auth import models,disconnect
                    result=models(msg.get('accountRef')) if operation=='chatgpt-models' else disconnect(msg.get('accountRef'))
                elif operation in ('update-check','update-download'):
                    from .updates import Updates
                    updater=Updates()
                    if operation=='update-check':result=updater.check()
                    else:result=updater.download(msg.get('selectionRef'),msg['_cancel'],lambda percent:send_message({'type':'task','taskId':task_id,'status':'progress','stage':'downloading','percent':percent}))
                else:raise ValueError('Unsupported task')
                send_message({'type':'task','taskId':task_id,'status':'complete','result':result})
            except Exception as error:
                from .failures import OperationFailure
                failure = None
                if str(operation).startswith('update-'):
                    import httpx
                    stage = 'update-check' if operation == 'update-check' else 'update-download'
                    code = 'cancelled' if msg['_cancel'].is_set() else 'timeout' if isinstance(error, httpx.TimeoutException) else 'network' if isinstance(error, httpx.HTTPError) else 'invalid-response' if operation == 'update-check' else 'verification-failed'
                    failure = error if isinstance(error, OperationFailure) else OperationFailure(stage, code)
                send_message({'type':'task','taskId':task_id,'status':'error','reason':'cancelled' if msg['_cancel'].is_set() else 'authentication-failed' if str(operation).startswith('chatgpt-') else 'download-failed',
                              **({'failure': failure.detail} if failure else {})})
            finally: tasks.pop(task_id,None)

        elif msg_type in ('CHATGPT_STATUS','CHATGPT_MODELS','CHATGPT_MODELS_CACHED','CHATGPT_DISCONNECT','CHATGPT_ACK_USAGE'):
            try:
                from .account_store import AccountStore
                from .chatgpt_auth import models, disconnect,acknowledge_usage,cached_models
                if msg_type == 'CHATGPT_STATUS': result={'accounts':AccountStore().public_status()}
                elif msg_type == 'CHATGPT_MODELS': result=models(msg.get('accountRef'))
                elif msg_type=='CHATGPT_MODELS_CACHED':result=cached_models(msg.get('accountRef'))
                elif msg_type=='CHATGPT_ACK_USAGE':result=acknowledge_usage(msg.get('accountRef'))
                else: result=disconnect(msg.get('accountRef'))
                send_message({'requestId':msg.get('requestId'),**result})
            except Exception:
                send_message({'requestId':msg.get('requestId'),'error':'ChatGPT account operation failed. Upgrade/Repair or reconnect. No paid API fallback was used.'})

        elif msg_type in ('UPDATES_INSTALL','UPDATES_STATUS'):
            try:
                from .updates import Updates
                if msg_type=='UPDATES_INSTALL':
                    from .activity import activity_gate,root_directory
                    with activity_gate(root_directory(),install=True):result=Updates().launch(msg.get('selectionRef'))
                else:
                    from cueflora_setup.engine import Setup
                    state=Setup().state()
                    result={'installedVersion':(state or {}).get('hostVersion'),
                        'extensionVersion':((state or {}).get('extension') or {}).get('version'),
                        'managed':bool((state or {}).get('extension'))}
                send_message({'requestId':msg.get('requestId'),**result})
            except Exception:
                send_message({'requestId':msg.get('requestId'),'error':'Update installation is unavailable. Finish all Runs, download again if verification failed, or use the matching complete package and Setup.'})

        elif msg_type == 'CREDENTIAL_PROTECT':
            from .credentials import handle_protect
            send_message(handle_protect(msg))

        elif msg_type == 'PROVIDERS_CHECK':
            from .provider_check import check_provider
            send_message(check_provider(msg))

        elif msg_type == "TRANSCRIBE_NATIVE":
            if getattr(sys,'frozen',False) and os.name=='nt':
                from .activity import RunLease
                try:
                    with RunLease():result=handle_transcribe(msg)
                except Exception:result={'jobId':msg.get('jobId'),'error':'CueFlora installation is in progress. Retry afterward.'}
            else:result = handle_transcribe(msg)
            send_message(result)

        elif msg_type == "TRANSLATE_NATIVE":
            if getattr(sys,'frozen',False) and os.name=='nt':
                from .activity import RunLease
                try:
                    with RunLease():result=handle_translate(msg)
                except Exception:result={'jobId':msg.get('jobId'),'error':'CueFlora installation is in progress. Retry afterward.','requestCount':0,'errorKind':'protocol'}
            else:result = handle_translate(msg)
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

    if run_lease is not None:run_lease.__exit__(None,None,None)


if __name__ == "__main__":
    main()
