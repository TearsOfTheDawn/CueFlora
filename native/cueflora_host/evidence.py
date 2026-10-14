"""Explicitly enabled, append-only local diagnostic captures (never credentials).

Set CUEFLORA_EVIDENCE_DIR on the native host to enable. Browser messages cannot
select a filesystem directory or enable capture themselves.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import time
from urllib.parse import urlsplit, urlunsplit
import uuid


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sanitized(value):
    if isinstance(value, dict):
        return {k: sanitized(v) for k, v in value.items()
                if not re.search(r"api.?key|authorization|cookie|access.?token|password|headers|url$|credential|ciphertext|^blob$", k, re.I)
                or k in {"max_tokens", "completion_tokens", "prompt_tokens", "total_tokens",
                         "reasoning_tokens", "requestedOutputTokens"}}
    if isinstance(value, (list, tuple)):
        return [sanitized(v) for v in value]
    if isinstance(value, str):
        def clean_url(match):
            try:
                p = urlsplit(match.group())
                host = p.hostname or ""
                if ":" in host:
                    host = f"[{host}]"
                if p.port:
                    host += f":{p.port}"
                return urlunsplit((p.scheme, host, p.path, "", ""))
            except ValueError:
                return "[redacted-url]"
        return re.sub(r"https?://[^\s\"<>]+", clean_url, value)
    return value


class RunCapture:
    """Best-effort production capture; failures never repeat inference.

    Controlled callers inspect diagnostics and reject incomplete evidence after
    the operation, preserving the physical request count even on disk failure.
    """
    def __init__(self, capture=None):
        self.capture = capture
        self.capture_id = capture.capture_id if capture else None
        self.stages = {}
        self._secrets = ()

    def exclude_secrets(self, *values):
        self._secrets = tuple(value for value in values if isinstance(value, str) and value)

    def _redact(self, value):
        if isinstance(value, dict):
            return {key: self._redact(item) for key, item in sanitized(value).items()}
        if isinstance(value, (list, tuple)):
            return [self._redact(item) for item in value]
        if isinstance(value, str):
            for secret in self._secrets:
                value = value.replace(secret, '[redacted]')
        return value

    @classmethod
    def open(cls, method, *args):
        if not os.environ.get("CUEFLORA_EVIDENCE_DIR"):
            return None
        result = cls()
        try:
            result.capture = getattr(Capture, method)(*args)
            result.capture_id = result.capture.capture_id if result.capture else None
            if result.capture is None:
                result.stages["capture-open"] = "incomplete"
        except Exception:
            result.stages["capture-open"] = "incomplete"
        return result

    def _call(self, operation, kind, *args):
        try:
            if self.capture is None:
                raise RuntimeError("Capture unavailable")
            value = getattr(self.capture, operation)(kind, *args)
            self.stages.setdefault(kind, "complete")
            return value
        except Exception:
            self.stages[kind] = "incomplete"
            return None

    def record(self, kind, payload):
        return self._call("record", kind, self._redact(payload))

    def record_lazy(self, kind, payload_factory):
        try:
            return self.record(kind, payload_factory())
        except Exception:
            self.stages[kind] = "incomplete"
            return None

    def preserve(self, kind, source):
        return self._call("preserve", kind, source)

    def diagnostics(self):
        return {"complete": all(v == "complete" for v in self.stages.values()),
                "stages": dict(self.stages)}


class Capture:
    def __init__(self, path, capture_id):
        self.path = path
        self.capture_id = capture_id

    @classmethod
    def create(cls, video_id, job_id):
        root = os.environ.get("CUEFLORA_EVIDENCE_DIR")
        if not root:
            return None
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id or ""):
            raise ValueError("Invalid capture video ID")
        run = uuid.uuid4().hex
        capture_id = f"{video_id}/{run}"
        path = Path(root).resolve() / video_id / run
        path.mkdir(parents=True, exist_ok=False)
        capture = cls(path, capture_id)
        capture.record("run", {"schemaVersion": 1, "videoId": video_id,
                               "jobId": job_id, "createdAt": time.time(),
                               "captureId": capture_id})
        return capture

    @classmethod
    def resume(cls, capture_id, job_id):
        root = os.environ.get("CUEFLORA_EVIDENCE_DIR")
        if not root or not capture_id:
            return None
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}/[a-f0-9]{32}", capture_id):
            raise ValueError("Invalid capture ID")
        base = Path(root).resolve()
        path = (base / capture_id).resolve()
        if not path.is_relative_to(base):
            raise ValueError("Capture escaped root")
        manifests = list(path.glob("run-*.json"))
        if len(manifests) != 1 or json.loads(manifests[0].read_text(encoding="utf-8"))["jobId"] != job_id:
            raise ValueError("Capture does not belong to this job")
        return cls(path, capture_id)

    def record(self, kind, payload):
        if not re.fullmatch(r"[a-z0-9-]+", kind):
            raise ValueError("Invalid record kind")
        name = f"{kind}-{uuid.uuid4().hex}.json"
        with (self.path / name).open("x", encoding="utf-8") as stream:
            json.dump(sanitized(payload), stream, ensure_ascii=False, indent=2)
        return name

    def record_lazy(self, kind, payload_factory):
        return self.record(kind, payload_factory())

    def preserve(self, kind, source):
        source = Path(source)
        name = f"{kind}-{uuid.uuid4().hex}{source.suffix}"
        target = self.path / name
        with source.open("rb") as src, target.open("xb") as dst:
            shutil.copyfileobj(src, dst)
        return {"file": name, "sha256": sha256(target), "bytes": target.stat().st_size,
                "originalFilename": source.name}


def normalization_mapping(raw, cues):
    """Explicit temporal associations, not claims of exact lexical ownership.

    Native ASR has no persistent token IDs. Retain raw and normalized words so
    consumers can inspect ambiguous associations rather than inventing matches.
    """
    raw_words = {}
    segments = raw.get("segments") or []
    groups = [(f"segment:{j}", seg.get("words") or []) for j, seg in enumerate(segments)]
    groups.append(("top", raw.get("words") or []))
    for prefix, words in groups:
        for index, word in enumerate(words):
            try:
                key = (word.get("word") or word.get("token") or "",
                       round(float(word["start"]) * 1000, 3), round(float(word["end"]) * 1000, 3))
                raw_words.setdefault(key, []).append(f"{prefix}:word:{index}")
            except (KeyError, TypeError, ValueError):
                continue
    return [{"cueId": i, "rawSegmentIds": [j for j, seg in enumerate(segments)
             if seg.get("start", 0) * 1000 < cue["endMs"]
             and seg.get("end", 0) * 1000 > cue["startMs"]],
             "segmentAssociation": "temporal-overlap",
             "wordAssociations": [{"wordIndex": j, "rawWordIds": raw_words.get(
                 (word["text"], round(word["startMs"], 3), round(word["endMs"], 3)), [])}
                 for j, word in enumerate(cue.get("words") or [])]}
            for i, cue in enumerate(cues)]
