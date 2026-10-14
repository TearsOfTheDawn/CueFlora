"""Headless production-path capture and byte-identical upload replay.

No browser settings are changed. The optional JSON message bridge is consumed by
scripts/quality-run.mjs, which executes the real TypeScript API/recovery code.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import re
import copy
import importlib.util
from collections import Counter

from . import handle_transcribe, handle_translate
from .evidence import Capture, sha256
from .whisper import _post_transcription


def handle_controlled_message(msg):
    """One production invocation, followed by strict evidence acceptance."""
    if msg["type"] == "TRANSCRIBE_NATIVE":
        result = handle_transcribe(msg)
    elif msg["type"] == "TRANSLATE_NATIVE":
        result = handle_translate(msg)
    elif msg["type"] == "CAPTURE_PRESENTATION":
        capture = Capture.resume(msg["captureId"], msg["jobId"])
        if not capture:
            raise ValueError("Capture disabled")
        capture.record("presentation", {k: v for k, v in msg.items()
            if k not in {"type", "captureId", "jobId"}})
        return {"jobId": msg["jobId"], "captured": True}
    else:
        raise ValueError("Unknown message")
    evidence = result.get("evidence", result.get("diagnostics", {}).get("evidence"))
    if not evidence or not evidence.get("complete"):
        result = {**result, "error": "Controlled evaluation requires complete evidence", "errorKind": "evidence"}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["message", "replay", "normalize"])
    parser.add_argument("--capture")
    parser.add_argument("--endpoint", help="Explicit service base URL for replay")
    args = parser.parse_args()
    if args.command == 'replay' and not args.endpoint:
        parser.error('replay requires an explicit --endpoint')
    # Prevent native binary framing in this developer-only CLI.
    import cueflora_host
    from . import download
    download._send_on_real_stdout = lambda msg: None
    sys.stdout.reconfigure(encoding="utf-8")
    cueflora_host.send_message = lambda msg: None
    if args.command == "message":
        msg = json.load(sys.stdin)
        original_stdout = sys.stdout
        sys.stdout = sys.stderr
        try:
            result = handle_controlled_message(msg)
        finally:
            sys.stdout = original_stdout
        print(json.dumps(result, ensure_ascii=False))
    else:
        path = Path(args.capture).resolve()
        manifest = json.loads(next(path.glob("run-*.json")).read_text(encoding="utf-8"))
        capture = Capture(path, manifest["captureId"])
        if args.command == "normalize":
            source_record = json.loads(next(path.glob("normalizer-source-*.json")).read_text(encoding="utf-8"))
            snapshot = (path / source_record["file"]).resolve()
            if not snapshot.is_relative_to(path) or sha256(snapshot) != source_record["sha256"]:
                raise ValueError("Normalizer snapshot hash/path mismatch")
            spec = importlib.util.spec_from_file_location("baseline_normalizer", snapshot)
            old = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(old)
            from .whisper import parse_cues
            for file in path.glob("normalization-*.json"):
                if not re.fullmatch(r"normalization-[a-f0-9]{32}\.json", file.name):
                    continue
                record = json.loads(file.read_text(encoding="utf-8"))
                raw = record["raw"]
                before = old.parse_cues(copy.deepcopy(raw))
                after = parse_cues(copy.deepcopy(raw))
                def lexical(cues):
                    return ''.join(ch for cue in cues for ch in cue["text"] if ch.isalnum())
                def words(cues):
                    return Counter((w["text"], round(w["startMs"], 3), round(w["endMs"], 3))
                        for c in cues for w in c.get("words", []))
                summary = {"originalRecord": file.name, "beforeCount": len(before), "afterCount": len(after),
                    "lexicalContentUnchanged": lexical(before) == lexical(after),
                    "wordTimestampsUnchanged": words(before) == words(after),
                    "baselineReproduced": before == record["cues"],
                    "leadingClosingBefore": sum(c["text"][0] in '，。！？；：、,.!?;:' for c in before),
                    "leadingClosingAfter": sum(c["text"][0] in '，。！？；：、,.!?;:' for c in after)}
                capture.record("normalization-replay", {**summary, "before": before, "after": after})
                print(json.dumps(summary))
                if not all(summary[k] for k in ['lexicalContentUnchanged','wordTimestampsUnchanged','baselineReproduced']):
                    raise ValueError("Normalization preservation check failed")
            return
        seen = set()
        for file in sorted(path.glob("asr-attempt-*.json")):
            item = json.loads(file.read_text(encoding="utf-8"))
            upload = item["upload"]
            if upload["file"] in seen:
                continue
            seen.add(upload["file"])
            audio = (path / upload["file"]).resolve()
            if not audio.is_relative_to(path) or sha256(audio) != upload["sha256"]:
                raise ValueError("Upload hash/path mismatch")
            response = _post_transcription(audio, args.endpoint.rstrip("/") + "/audio/transcriptions",
                {"Authorization": "Bearer " + os.environ.get("CUEFLORA_ASR_KEY", "local")},
                item["params"], item["mime"], 1, upload_filename=upload["originalFilename"])
            capture.record("asr-replay", {"originalRecord": file.name, "upload": upload,
                "response": response, "sameText": response.get("text") == (item.get("response") or {}).get("text")})
            print(json.dumps({"upload": upload["file"], "sha256": upload["sha256"], "replayed": True}))


if __name__ == "__main__":
    main()
