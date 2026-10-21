"""Whisper-compatible transcription API client."""

import concurrent.futures
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata

import httpx
from .failures import OperationFailure, http_failure

WHISPER_FORMATS = {"flac", "mp3", "mp4", "mpeg", "mpga", "m4a", "ogg", "wav", "webm"}

MIME_TYPES = {
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
}

TARGET_BITRATE_BPS = 24_000
TARGET_SAMPLE_RATE_HZ = 48_000
TARGET_CHANNELS = 1
MAX_SINGLE_UPLOAD_MEGABYTES = 25
MAX_SINGLE_UPLOAD_BYTES = MAX_SINGLE_UPLOAD_MEGABYTES * 1024 * 1024
CHUNK_OVERLAP_SECONDS = 10
CHUNK_UPLOAD_HEADROOM_RATIO = 0.90
MIN_CHUNK_LENGTH_SECONDS = 15
CHUNK_MAX_PARALLEL_UPLOADS = 4
DEFAULT_MAX_API_ATTEMPTS = 3

TARGET_OUTPUT_EXT = ".ogg"
TARGET_OUTPUT_CODEC = "libopus"

MAX_CUE_DURATION_MS = 5_000
NORMALIZATION_VERSION = "asr-v2-punctuation-ownership"
MIN_CUE_DURATION_MS = 833  # 5/6 second (Netflix spec)
MAX_CUE_TEXT_CHARS = 84  # 42 chars/line × 2 lines
DUPLICATE_WORD_OVERLAP_THRESHOLD = 0.6
MIN_GAP_MS = 1

# Readability post-processing. Real ASR word timestamps can legitimately create
# very short fragments; these settings keep those fragments readable without
# moving their start times away from the spoken audio.
MIN_READABLE_CUE_MS = 1_500
READABILITY_MERGE_MAX_MS = 6_000

MIN_HALLUCINATION_RUN = 5
HALLUCINATION_TS_EPSILON = 0.01  # seconds

# Coarse-segment repetition guard. Fun-ASR-Nano can occasionally emit hundreds
# of repeated CJK characters for a few seconds of difficult/noisy audio, often
# with words=[] so timestamp-based word filtering cannot see the failure. These
# thresholds are deliberately conservative: sanitization only happens when a
# long segment is both implausibly dense and dominated by a short periodic run.
MIN_REPETITIVE_SEGMENT_CHARS = 120
MIN_REPETITION_RUN_CHARS = 80
MIN_REPETITION_RUN_REPEATS = 10
MAX_REPETITION_UNIT_CHARS = 16
MIN_REPETITION_COVERAGE = 0.55
MIN_REPETITIVE_CHAR_RATE = 18.0  # visible characters / second
REPETITION_KEEP_COPIES = 2

# Temporary timing diagnostic. The files contain transcription text, but remain local.
DEBUG_DUMP_DIR = os.environ.get(
    "CUEFLORA_FUNASR_DEBUG_DIR",
    "",
)


def _dump_debug_json(filename, payload):
    """Best-effort local JSON dump for FunASR timing diagnosis."""
    if not DEBUG_DUMP_DIR:
        return
    # Legacy opt-in captures must also be append-only.
    import uuid
    filename = uuid.uuid4().hex + "-" + filename
    try:
        os.makedirs(DEBUG_DUMP_DIR, exist_ok=True)
        path = os.path.join(DEBUG_DUMP_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"[cueflora whisper] Debug dump: {path}", file=sys.stderr)
    except Exception as exc:
        # Diagnostics must never break transcription.
        print(
            f"[cueflora whisper] Debug dump failed for {filename}: {exc}",
            file=sys.stderr,
        )


def _noop_progress(stage, message, percent=None, raw=None):
    pass


def _strip_hallucinated_words(words):
    """Remove runs of words with collapsed timestamps (hallucination artifacts).

    Whisper's decoder can get stuck at segment boundaries, emitting dozens of
    fabricated words all sharing the exact same timestamp.  Real speech never
    produces MIN_HALLUCINATION_RUN+ consecutive words at the same millisecond,
    so this signal is virtually false-positive-free.

    Returns (filtered_words, stripped_count).
    """
    if not words:
        return words, 0

    filtered = []
    run_start = 0
    total_stripped = 0

    i = 0
    while i < len(words):
        run_start = i
        anchor = float(words[i].get("start", -1))
        # Extend run while consecutive words share the same start timestamp.
        j = i + 1
        while j < len(words):
            s = float(words[j].get("start", -2))
            if abs(s - anchor) <= HALLUCINATION_TS_EPSILON:
                j += 1
            else:
                break

        run_len = j - run_start
        if run_len >= MIN_HALLUCINATION_RUN:
            total_stripped += run_len
            ts = round(anchor, 3)
            print(
                f"[cueflora whisper] Stripped {run_len} hallucinated words "
                f"(collapsed at {ts}s)",
                file=sys.stderr,
            )
        else:
            filtered.extend(words[run_start:j])
        i = j

    return filtered, total_stripped


def _find_pathological_repetition_run(text):
    """Return the strongest exact short-period repetition run, or None.

    The scan is intentionally small (periods <= MAX_REPETITION_UNIT_CHARS) and
    only used on already-long coarse segments, so it remains cheap. A candidate
    is represented as (start, end, unit, repeats, run_chars).
    """
    n = len(text)
    if n < MIN_REPETITION_RUN_CHARS:
        return None

    best = None
    max_unit = min(MAX_REPETITION_UNIT_CHARS, n // MIN_REPETITION_RUN_REPEATS)
    for unit_len in range(1, max_unit + 1):
        max_start = n - unit_len * MIN_REPETITION_RUN_REPEATS
        for start in range(max_start + 1):
            unit = text[start : start + unit_len]
            if not unit or unit.isspace():
                continue
            # Ignore pure punctuation/spacing cycles.
            if not any(ch.isalnum() for ch in unit):
                continue

            pos = start + unit_len
            repeats = 1
            while pos + unit_len <= n and text[pos : pos + unit_len] == unit:
                repeats += 1
                pos += unit_len

            run_chars = repeats * unit_len
            if (
                repeats < MIN_REPETITION_RUN_REPEATS
                or run_chars < MIN_REPETITION_RUN_CHARS
            ):
                continue

            candidate = (run_chars, repeats, -unit_len, -start, start, pos, unit)
            if best is None or candidate > best:
                best = candidate

    if best is None:
        return None
    run_chars, repeats, _neg_unit_len, _neg_start, start, end, unit = best
    return start, end, unit, repeats, run_chars


def _sanitize_repetitive_segment_text(text, start_s, end_s):
    """Trim only extreme periodic decoder loops from coarse ASR segments.

    Legitimate repetition is preserved unless ALL of the following are true:
      * the segment is long;
      * visible text density is implausibly high for its audio duration;
      * a short exact periodic run occupies most of the segment; and
      * that run repeats at least MIN_REPETITION_RUN_REPEATS times.

    Returns (sanitized_text, changed).
    """
    original = (text or "").strip()
    if not original:
        return original, False

    visible_chars = sum(1 for ch in original if not ch.isspace())
    try:
        duration_s = max(0.0, float(end_s) - float(start_s))
    except (TypeError, ValueError):
        duration_s = 0.0

    if visible_chars < MIN_REPETITIVE_SEGMENT_CHARS or duration_s <= 0:
        return original, False

    char_rate = visible_chars / duration_s
    if char_rate < MIN_REPETITIVE_CHAR_RATE:
        return original, False

    run = _find_pathological_repetition_run(original)
    if run is None:
        return original, False

    run_start, run_end, unit, repeats, run_chars = run
    coverage = run_chars / max(1, len(original))
    if coverage < MIN_REPETITION_COVERAGE:
        return original, False

    keep_end = min(run_end, run_start + len(unit) * REPETITION_KEEP_COPIES)
    prefix = original[:keep_end]
    suffix = original[run_end:]

    # A decoder loop often stops mid-period (for example a trailing "，你").
    # Drop tiny fragments that are likely just a partial repeat, but preserve a
    # substantial suffix so real speech after a loop is not lost.
    suffix_visible = "".join(ch for ch in suffix if not ch.isspace())
    if len(suffix_visible) >= max(6, len(unit)):
        sanitized = prefix + suffix
    else:
        sanitized = prefix

    sanitized = sanitized.strip()
    removed = max(0, len(original) - len(sanitized))
    print(
        f"[cueflora whisper] Sanitized pathological repetition: "
        f"removed {removed} chars, repeats={repeats}, "
        f"coverage={coverage:.2f}, char_rate={char_rate:.1f}/s, "
        f"segment={float(start_s):.2f}-{float(end_s):.2f}s",
        file=sys.stderr,
    )
    return sanitized, True


def _annotate_words_with_segment_text(seg_text, seg_words):
    """Attach punctuation context from *seg_text* to each word entry.

    Walks through *seg_text* matching each word in *seg_words* in order.
    Each word gets a ``prefix`` key containing any characters (commas,
    spaces, etc.) that appeared between the previous match and this one.
    The annotation travels with the word through splitting and
    normalisation, so punctuation is never lost.
    """
    if not seg_text or not seg_words:
        return

    pos = 0
    for word in seg_words:
        wt = word.get("text", "").strip()
        if not wt:
            word["prefix"] = ""
            continue
        idx = seg_text.find(wt, pos)
        if idx >= 0:
            word["prefix"] = seg_text[pos:idx]
            pos = idx + len(wt)
        else:
            # Word diverges from segment text — use space as fallback.
            word["prefix"] = " " if pos > 0 else ""


def _text_from_annotated_words(words):
    """Build display text from words carrying ``prefix`` annotations.

    The first word's prefix is always skipped (a standalone cue should
    not begin with a comma or other inter-sentence punctuation).
    Missing prefixes default to ``" "`` which keeps the existing
    space-joined behaviour for the words-only code path.
    """
    if not words:
        return ""
    parts = []
    for w in words:
        wt = w.get("text", "").strip()
        if not wt:
            continue
        if not parts:
            # First visible word — skip prefix.
            parts.append(wt)
        else:
            prefix = w.get("prefix", " ")
            parts.append(prefix + wt)
    return "".join(parts).strip()


def _resolve_binary(name):
    """Resolve external tool paths robustly for native-host runtime."""
    from .runtime_tools import packaged_tool

    def is_runnable(path, version_args=None):
        if not path or not os.path.isfile(path) or not os.access(path, os.X_OK):
            return False
        try:
            args = [path] + (version_args or ["-version"])
            probe = subprocess.run(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=8,
            )
            return probe.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False

    bundled = packaged_tool(name)
    if bundled:
        if not is_runnable(bundled):
            raise RuntimeError(f'Configured {name} cannot run; repair runtime or developer override')
        return bundled

    # Prefer venv-local links created by install.sh.
    venv_bin = os.path.dirname(sys.executable)

    venv_candidates = [
        os.path.join(venv_bin, name + ".exe"),
        os.path.join(venv_bin, name),
    ]

    for venv_tool in venv_candidates:
        if is_runnable(venv_tool):
            return venv_tool

    # Prefer common Homebrew paths on macOS.
    preferred_candidates = [
        f"/opt/homebrew/bin/{name}",
        f"/usr/local/bin/{name}",
    ]
    for path in preferred_candidates:
        if is_runnable(path):
            return path

    found = shutil.which(name)
    if is_runnable(found):
        return found

    fallback = f"/usr/bin/{name}"
    if is_runnable(fallback):
        return fallback

    return None


def build_transcription_params(model, language=None, prompt=None):
    """Build request data params appropriate for the model.

    - whisper-1, Groq whisper-large-v3*: support verbose_json + word timestamps
    - gpt-4o-transcribe / gpt-4o-mini-transcribe: only support json (no timestamps)

    Returns a dict of form-data fields for the multipart upload.
    Array params use the ``[]`` suffix with a Python list so httpx sends
    repeated multipart fields (the convention the OpenAI API expects).
    """
    if "gpt-4o" in model:
        params = {"model": model, "response_format": "json"}
    else:
        params = {
            "model": model,
            "response_format": "verbose_json",
            "timestamp_granularities[]": ["word", "segment"],
        }

    if language:
        params["language"] = language

    if prompt:
        # OpenAI docs mention a 224-token prompt limit; trim very long input.
        params["prompt"] = prompt[:1200]

    return params


def parse_cues(result, diagnostics=None):
    """Parse any Whisper-compatible transcription response into cues.

    Handles:
      - FunASR verbose_json with word timestamps nested in each segment:
        {segments: [{start, end, text, words: [{word, start, end}, ...]}]}
      - OpenAI-style top-level words:
        {words: [{word, start, end}], segments: [...]}
      - segment-only verbose_json:
        {segments: [{start, end, text, ...}]}
      - plain json:
        {text: "..."}

    When real word-level timestamps are available, they are always preserved and
    used for cue boundaries.  Proportional timing is only a fallback for models
    that return segment/text timing without word timestamps.
    """
    diagnostics = diagnostics if diagnostics is not None else {}
    diagnostics.setdefault("rawSegmentCount", 0)
    diagnostics.setdefault("collapsedWordsRemoved", 0)
    diagnostics.setdefault("repetitionSanitizations", 0)

    cues = []
    segments = result.get("segments") or []
    top_level_words = result.get("words") or []
    diagnostics["rawSegmentCount"] = len(segments)
    diagnostics["normalizationVersion"] = NORMALIZATION_VERSION
    diagnostics["emptySegmentCount"] = sum(not (s.get("text") or "").strip() for s in segments)
    diagnostics["audioDurationMs"] = round(float(result.get("duration") or 0) * 1000)

    # FunASR's OpenAI-compatible verbose_json normally places word timestamps
    # inside each segment rather than in a top-level "words" array.  Prefer
    # those segment-local timestamps when present.
    has_nested_words = any(
        isinstance(seg.get("words"), list) and seg.get("words")
        for seg in segments
    )

    if segments and has_nested_words:
        for seg in segments:
            seg_text = (seg.get("text") or "").strip()
            if not seg_text:
                continue

            raw_seg_words = seg.get("words") or []
            raw_seg_words, stripped_count = _strip_hallucinated_words(raw_seg_words)
            diagnostics["collapsedWordsRemoved"] += stripped_count

            seg_words = []
            for word in raw_seg_words:
                w_text = (word.get("word") or word.get("token") or "").strip()
                if not w_text:
                    continue
                try:
                    w_start = float(word.get("start"))
                    w_end = float(word.get("end"))
                except (TypeError, ValueError):
                    continue
                if w_end <= w_start:
                    continue
                seg_words.append(
                    {
                        "text": w_text,
                        "startMs": w_start * 1000,
                        "endMs": w_end * 1000,
                    }
                )

            speaker = seg.get("speaker")

            if seg_words:
                _annotate_words_with_segment_text(seg_text, seg_words)
                text_from_words = _text_from_annotated_words(seg_words)
                if not text_from_words:
                    continue

                # Use the actual first/last word timestamps for the cue itself,
                # not the coarser VAD/segment boundaries.  _split_cue() will
                # then split further on these same word timestamps.
                cue_start = seg_words[0]["startMs"]
                cue_end = seg_words[-1]["endMs"]
                display_text = text_from_words
                if speaker:
                    display_text = f"[{speaker}] {display_text}"

                cues.append(
                    {
                        "start": cue_start,
                        "end": cue_end,
                        "text": display_text,
                        "words": seg_words,
                    }
                )
            else:
                # Some segments may legitimately have no word timing even when
                # neighboring segments do. Keep their real segment boundaries,
                # but guard against extreme decoder repetition loops that cannot
                # be detected by _strip_hallucinated_words() when words=[].
                display_text, changed = _sanitize_repetitive_segment_text(
                    seg_text, seg.get("start", 0), seg.get("end", 0)
                )
                diagnostics["repetitionSanitizations"] += int(changed)
                if not display_text:
                    continue
                if speaker:
                    display_text = f"[{speaker}] {display_text}"
                cues.append(
                    {
                        "start": float(seg.get("start", 0)) * 1000,
                        "end": float(seg.get("end", 0)) * 1000,
                        "text": display_text,
                        "coarse_timing": True,
                    }
                )

    elif top_level_words:
        # Strip hallucinated word runs (collapsed timestamps at segment
        # boundaries) before any further processing.
        raw_words, stripped_count = _strip_hallucinated_words(top_level_words)
        diagnostics["collapsedWordsRemoved"] += stripped_count

        if segments:
            # Assign each word to exactly one segment (the tightest fit) so
            # chunk overlap never duplicates a word across cues.
            word_seg = [None] * len(raw_words)
            for w_i, w in enumerate(raw_words):
                best_idx = None
                best_span = float("inf")
                best_seg_start = -1.0
                for s_i, seg in enumerate(segments):
                    if (
                        w["start"] >= seg["start"] - 0.01
                        and w["start"] < seg["end"] + 0.01
                    ):
                        span = seg["end"] - seg["start"]
                        if span < best_span or (
                            span == best_span
                            and seg["start"] > best_seg_start
                        ):
                            best_idx = s_i
                            best_span = span
                            best_seg_start = seg["start"]
                word_seg[w_i] = best_idx

            seg_word_map = {}
            for w_i, s_i in enumerate(word_seg):
                if s_i is not None:
                    seg_word_map.setdefault(s_i, []).append(w_i)

            for s_i, seg in enumerate(segments):
                seg_text = (seg.get("text") or "").strip()
                if not seg_text:
                    continue

                w_indices = seg_word_map.get(s_i, [])
                seg_words = [
                    {
                        "text": (raw_words[i].get("word") or raw_words[i].get("token") or "").strip(),
                        "startMs": float(raw_words[i]["start"]) * 1000,
                        "endMs": float(raw_words[i]["end"]) * 1000,
                    }
                    for i in w_indices
                    if (raw_words[i].get("word") or raw_words[i].get("token") or "").strip()
                ]

                speaker = seg.get("speaker")
                if seg_words:
                    _annotate_words_with_segment_text(seg_text, seg_words)
                    display_text = _text_from_annotated_words(seg_words)
                    if not display_text:
                        continue
                    if speaker:
                        display_text = f"[{speaker}] {display_text}"
                    cues.append(
                        {
                            "start": seg_words[0]["startMs"],
                            "end": seg_words[-1]["endMs"],
                            "text": display_text,
                            "words": seg_words,
                        }
                    )
                else:
                    display_text, changed = _sanitize_repetitive_segment_text(
                        seg_text, seg.get("start", 0), seg.get("end", 0)
                    )
                    diagnostics["repetitionSanitizations"] += int(changed)
                    if not display_text:
                        continue
                    if speaker:
                        display_text = f"[{speaker}] {display_text}"
                    cues.append(
                        {
                            "start": float(seg.get("start", 0)) * 1000,
                            "end": float(seg.get("end", 0)) * 1000,
                            "text": display_text,
                            "coarse_timing": True,
                        }
                    )
        else:
            # No segments — group top-level words into natural phrase cues
            # based on real word timing gaps, text length, and duration.
            phrase_words = []
            phrase_start = None

            for word in raw_words:
                w_text = (word.get("word") or word.get("token") or "").strip()
                if not w_text:
                    continue
                w_start = float(word["start"]) * 1000
                w_end = float(word["end"]) * 1000

                if phrase_start is None:
                    phrase_start = w_start

                should_split = False
                if phrase_words:
                    gap_ms = w_start - phrase_words[-1]["endMs"]
                    duration = w_end - phrase_start
                    new_len = sum(len(w["text"]) for w in phrase_words) + len(w_text)
                    should_split = (
                        gap_ms > 400
                        or new_len > MAX_CUE_TEXT_CHARS
                        or duration > MAX_CUE_DURATION_MS
                    )

                if should_split and phrase_words:
                    cues.append(
                        {
                            "start": phrase_words[0]["startMs"],
                            "end": phrase_words[-1]["endMs"],
                            "text": _text_from_annotated_words(phrase_words),
                            "words": list(phrase_words),
                        }
                    )
                    phrase_words = []
                    phrase_start = w_start

                phrase_words.append(
                    {"text": w_text, "startMs": w_start, "endMs": w_end, "prefix": ""}
                )

            if phrase_words:
                cues.append(
                    {
                        "start": phrase_words[0]["startMs"],
                        "end": phrase_words[-1]["endMs"],
                        "text": _text_from_annotated_words(phrase_words),
                        "words": list(phrase_words),
                    }
                )

    elif segments:
        # Segment-only models (for example SenseVoice fallback) do not provide
        # enough information for truly accurate timing inside a long segment.
        # Keep the real segment boundaries here; _split_cue() may proportionally
        # subdivide them for readability, but that remains an approximation.
        for seg in segments:
            text = (seg.get("text") or "").strip()
            if not text:
                continue
            text, changed = _sanitize_repetitive_segment_text(
                text, seg.get("start", 0), seg.get("end", 0)
            )
            diagnostics["repetitionSanitizations"] += int(changed)
            if not text:
                continue
            speaker = seg.get("speaker")
            if speaker:
                text = f"[{speaker}] {text}"
            cues.append(
                {
                    "start": float(seg.get("start", 0)) * 1000,
                    "end": float(seg.get("end", 0)) * 1000,
                    "text": text,
                    "coarse_timing": True,
                }
            )

    elif "text" in result:
        duration = result.get("duration", 0)
        text, changed = _sanitize_repetitive_segment_text(result["text"], 0, duration)
        diagnostics["repetitionSanitizations"] += int(changed)
        if text:
            cues.append(
                {
                    "start": 0,
                    "end": duration * 1000,
                    "text": text,
                    "coarse_timing": True,
                }
            )

    normalized = _normalize_cues(cues)
    output = []
    for cue in normalized:
        entry = {
            "startMs": cue["start"],
            "endMs": cue["end"],
            "text": cue["text"],
        }
        if "words" in cue and cue["words"]:
            entry["words"] = cue["words"]
        output.append(entry)
    diagnostics["finalCueCount"] = len(output)
    return output

def _split_text_for_cues(text):
    """Split long text at natural punctuation/word boundaries.

    Returns a list of strings, each at most MAX_CUE_TEXT_CHARS characters.
    Prefers splitting at sentence-ending punctuation, then clause
    boundaries, then word boundaries.
    """
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return []
    if len(cleaned) <= MAX_CUE_TEXT_CHARS:
        return [cleaned]

    min_pos = MAX_CUE_TEXT_CHARS // 3  # avoid very short leading fragments
    parts = []
    remaining = cleaned
    while remaining:
        if len(remaining) <= MAX_CUE_TEXT_CHARS:
            parts.append(remaining.strip())
            break

        window = remaining[:MAX_CUE_TEXT_CHARS]

        # 1. Sentence-ending punctuation
        punct = max(window.rfind(". "), window.rfind("? "), window.rfind("! "))
        if punct >= min_pos:
            split_at = punct + 1
        else:
            # 2. Clause-level punctuation
            clause = max(window.rfind(", "), window.rfind("; "), window.rfind(": "))
            if clause >= min_pos:
                split_at = clause + 1
            else:
                # 3. Last word boundary
                space = window.rfind(" ")
                split_at = space if space > 0 else MAX_CUE_TEXT_CHARS

        left = remaining[:split_at].strip()
        if left:
            parts.append(left)
        remaining = remaining[split_at:].strip()

    return parts


def _split_cue(cue):
    """Split a cue that exceeds text length or duration limits.

    All resulting sub-cues stay within the original cue's time range.
    Time is allocated proportionally by character count and scaled down
    if the minimum-duration floor would push sub-cues past the end.
    """
    text = " ".join((cue["text"] or "").split())
    if not text:
        return []

    start = int(round(float(cue["start"])))
    end = int(round(float(cue["end"])))
    if end <= start:
        end = start + MIN_CUE_DURATION_MS

    duration = end - start
    text_fits = len(text) <= MAX_CUE_TEXT_CHARS
    time_fits = duration <= MAX_CUE_DURATION_MS

    # If real word-level timing is available, always use it — even when the
    # parent segment is already short enough.  Segment/VAD boundaries can be
    # noticeably earlier or later than the spoken words themselves.
    cue_words = cue.get("words") or []
    if cue_words:
        return _split_cue_with_words(cue_words, start, end)

    # Never invent intra-segment timing when the ASR model supplied only a
    # coarse segment boundary.  A long but honestly timed cue is preferable to
    # several short captions whose start/end times are guessed from text length.
    if cue.get("coarse_timing"):
        return [{"start": start, "end": end, "text": text}]

    if text_fits and time_fits:
        return [{"start": start, "end": end, "text": text}]

    # Split text into display-sized parts.
    parts = _split_text_for_cues(text)

    # If text already fits but duration is too long, split by time.
    if len(parts) <= 1 and not time_fits:
        n_chunks = max(2, -(-duration // MAX_CUE_DURATION_MS))
        words = text.split()

        if len(words) >= n_chunks:
            # Languages with spaces
            chunk_size = -(-len(words) // n_chunks)
            parts = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
        elif len(text) >= n_chunks:
            # CJK / languages without spaces
            chunk_size = -(-len(text) // n_chunks)
            parts = [text[i:i + chunk_size].strip() for i in range(0, len(text), chunk_size)]

    if len(parts) <= 1:
        return [{"start": start, "end": end, "text": parts[0] if parts else text}]

    # Proportional time allocation, scaled to stay within the original range.
    total_chars = sum(max(1, len(p)) for p in parts)
    raw_allocs = [
        max(MIN_CUE_DURATION_MS, int(round(duration * max(1, len(p)) / total_chars)))
        for p in parts
    ]
    total_alloc = sum(raw_allocs)
    if total_alloc > duration > 0:
        scale = duration / total_alloc
        raw_allocs = [max(1, int(round(a * scale))) for a in raw_allocs]

    result = []
    pos = start
    for i, (part_text, alloc) in enumerate(zip(parts, raw_allocs)):
        seg_start = pos
        seg_end = end if i == len(parts) - 1 else pos + alloc
        if seg_start >= end and result:
            # All time consumed — merge remaining text into last cue.
            result[-1]["text"] += " " + part_text
        else:
            result.append({"start": seg_start, "end": seg_end, "text": part_text})
        pos = seg_end

    return result if result else [{"start": start, "end": end, "text": text}]


def _punctuation_atoms(words):
    """Keep closing punctuation with preceding text and opening marks with following text.

    Atoms hold the original tokens unchanged, including their timestamps. This
    changes split ownership only, not recognized lexical content or alignment.
    Ambiguous straight quotes are left untouched.
    """
    atoms = []
    opening = []
    for word in words:
        text = word.get("text", "").strip()
        if not text:
            continue
        is_open = all(unicodedata.category(ch) in {"Ps", "Pi"} or ch in "¿¡" for ch in text)
        is_close = all(unicodedata.category(ch) in {"Pe", "Pf"} or ch in ",.!?;:，。！？；：、…" for ch in text)
        if is_open:
            opening.append(word)
        elif is_close and atoms and not opening:
            atoms[-1].append(word)
        else:
            atoms.append(opening + [word])
            opening = []
    if opening:
        # Incomplete source: preserve the marks rather than dropping them.
        atoms.append(opening)
    return atoms


def _split_cue_with_words(words, cue_start, cue_end):
    """Split a cue that has word-level timing into properly sized sub-cues.

    Uses actual word timestamps for splitting, so every resulting sub-cue
    retains accurate per-word timing data.  Display text for each sub-cue
    is built from the words' ``prefix`` annotations (set by
    ``_annotate_words_with_segment_text``), preserving punctuation even
    when a cue is split at an arbitrary word boundary.
    """
    result = []
    group_words = []
    group_text_len = 0
    group_start = None

    for atom in _punctuation_atoms(words):
        w = atom[0]
        w_start = w.get("startMs", cue_start)
        w_end = atom[-1].get("endMs", cue_end)
        w_text = _text_from_annotated_words(atom)
        if not w_text:
            continue

        if group_start is None:
            group_start = w_start

        should_split = False
        if group_words:
            prefix_len = len(w.get("prefix", " "))
            new_len = group_text_len + prefix_len + len(w_text)
            duration = w_end - group_start
            gap = w_start - group_words[-1].get("endMs", w_start)
            should_split = (
                new_len > MAX_CUE_TEXT_CHARS
                or duration > MAX_CUE_DURATION_MS
                or gap > 400
            )

        if should_split and group_words:
            last_end = group_words[-1].get("endMs", cue_end)
            result.append(
                {
                    "start": int(round(group_start)),
                    "end": int(round(last_end)),
                    "text": _text_from_annotated_words(group_words),
                    "words": list(group_words),
                }
            )
            group_words = []
            group_text_len = 0
            group_start = w_start

        group_words.extend(atom)
        if group_text_len == 0:
            group_text_len = len(w_text)
        else:
            group_text_len += len(w.get("prefix", " ")) + len(w_text)

    if group_words:
        last_end = group_words[-1].get("endMs", cue_end)
        result.append(
            {
                "start": int(round(group_start)),
                "end": int(round(last_end)),
                "text": _text_from_annotated_words(group_words),
                "words": list(group_words),
            }
        )

    return result if result else [{"start": cue_start, "end": cue_end, "text": ""}]


def _word_set(text):
    """Extract a set of comparable tokens for overlap detection.

    For text with whitespace separators (Latin, etc.) this returns
    whitespace-split words.  For CJK text (no internal whitespace) it
    returns individual characters so that overlap detection works for
    Chinese, Japanese, and Korean.
    """
    cleaned = re.sub(r"[^\w\s]", "", text.lower())
    tokens = cleaned.split()
    if len(tokens) <= 1 and len(cleaned) > 1:
        return set(cleaned)
    return set(tokens)


def _word_overlap_ratio(text_a, text_b):
    """Fraction of the smaller word-set shared with the other.

    Used to detect near-duplicate cues produced when overlapping audio
    chunks transcribe the same speech.  Returns 0.0–1.0.
    """
    words_a = _word_set(text_a)
    words_b = _word_set(text_b)
    if not words_a or not words_b:
        return 0.0
    smaller = min(len(words_a), len(words_b))
    return len(words_a & words_b) / smaller



def _join_caption_text(left, right):
    """Join adjacent cue text without inserting spaces into CJK text."""
    left = (left or "").strip()
    right = (right or "").strip()
    if not left:
        return right
    if not right:
        return left

    # Add a space only between ordinary ASCII words. Chinese/Japanese/Korean
    # text and punctuation should concatenate directly.
    if (
        left[-1].isascii()
        and right[0].isascii()
        and left[-1].isalnum()
        and right[0].isalnum()
    ):
        return left + " " + right
    return left + right


def _merge_caption_cues(left, right):
    """Merge two neighboring cues while preserving any word timing metadata."""
    merged = {
        "start": min(int(left["start"]), int(right["start"])),
        "end": max(int(left["end"]), int(right["end"])),
        "text": _join_caption_text(left.get("text"), right.get("text")),
    }
    words = list(left.get("words") or []) + list(right.get("words") or [])
    if words:
        merged["words"] = words
    return merged


def _can_merge_for_readability(left, right):
    """Whether two adjacent cues can be combined without becoming excessive."""
    merged = _merge_caption_cues(left, right)
    return (
        merged["end"] - merged["start"] <= READABILITY_MERGE_MAX_MS
        and len(merged["text"]) <= MAX_CUE_TEXT_CHARS
    )


def _finalize_readable_cues(cues):
    """Give very short real-timestamp cues enough display time.

    Strategy:
      1. Attach punctuation-only timestamp tokens to a neighboring cue.
      2. For cues shorter than MIN_READABLE_CUE_MS, first use otherwise-empty
         time before the next cue.
      3. If there is not enough free time, merge with the nearest neighboring
         cue when the combined cue remains reasonably sized.

    Start times are never moved later, and cues are never allowed to overlap.
    """
    if not cues:
        return []

    work = []
    for cue in cues:
        entry = {
            "start": int(cue["start"]),
            "end": int(cue["end"]),
            "text": (cue.get("text") or "").strip(),
        }
        if cue.get("words"):
            entry["words"] = list(cue["words"])
        work.append(entry)

    # Fun-ASR-Nano emits punctuation as timestamped tokens. A long pause before
    # punctuation can otherwise create a 60 ms cue containing only "。" etc.
    i = 0
    while i < len(work):
        text = work[i]["text"]
        punctuation_only = bool(text) and not any(ch.isalnum() for ch in text)
        if punctuation_only:
            if i > 0 and _can_merge_for_readability(work[i - 1], work[i]):
                work[i - 1] = _merge_caption_cues(work[i - 1], work[i])
                work.pop(i)
                continue
            if i + 1 < len(work) and _can_merge_for_readability(work[i], work[i + 1]):
                work[i] = _merge_caption_cues(work[i], work[i + 1])
                work.pop(i + 1)
                continue
        i += 1

    # Make remaining short cues readable.
    i = 0
    while i < len(work):
        cue = work[i]
        duration = cue["end"] - cue["start"]
        if duration >= MIN_READABLE_CUE_MS:
            i += 1
            continue

        next_start = work[i + 1]["start"] if i + 1 < len(work) else None
        ceiling = (
            next_start - MIN_GAP_MS
            if next_start is not None
            else cue["start"] + MAX_CUE_DURATION_MS
        )
        desired_end = min(
            cue["start"] + MIN_READABLE_CUE_MS,
            cue["start"] + MAX_CUE_DURATION_MS,
        )

        # Best case: simply hold the caption through an existing pause.
        if desired_end <= ceiling:
            cue["end"] = max(cue["end"], desired_end)
            i += 1
            continue

        # Dense speech: combine the short fragment with a neighbor rather than
        # delaying later speech or displaying unreadably fast text.
        candidates = []
        if i + 1 < len(work) and _can_merge_for_readability(cue, work[i + 1]):
            merged = _merge_caption_cues(cue, work[i + 1])
            candidates.append(("next", merged["end"] - merged["start"]))
        if i > 0 and _can_merge_for_readability(work[i - 1], cue):
            merged = _merge_caption_cues(work[i - 1], cue)
            candidates.append(("prev", merged["end"] - merged["start"]))

        if candidates:
            direction = min(candidates, key=lambda item: item[1])[0]
            if direction == "next":
                work[i] = _merge_caption_cues(cue, work[i + 1])
                work.pop(i + 1)
                # Re-evaluate the merged cue.
                continue

            work[i - 1] = _merge_caption_cues(work[i - 1], cue)
            work.pop(i)
            i = max(0, i - 1)
            continue

        # If merging is impossible, at least use every available millisecond
        # before the next caption.
        if ceiling > cue["end"]:
            cue["end"] = min(ceiling, cue["start"] + MAX_CUE_DURATION_MS)
        i += 1

    return work

def _normalize_cues(cues):
    """Post-process cues for readability and non-overlapping display.

    Pipeline:
      1. Split oversized cues (text > 84 chars or duration > 5 s).
      2. Sort by start time.
      3. Deduplicate near-identical overlapping cues that arise from
         transcribing overlapping audio chunks (word-overlap similarity).
      4. Resolve remaining timing overlaps — prefer trimming the previous
         cue's end so the current cue keeps its audio-sync start time.
    """
    if not cues:
        return []

    # 1. Expand cues that exceed limits.
    expanded = []
    for cue in cues:
        expanded.extend(_split_cue(cue))

    if not expanded:
        return []

    # 2. Sort by timeline.
    expanded.sort(key=lambda c: (c["start"], c["end"]))

    # 3 & 4. Deduplicate and resolve overlaps in one pass.
    normalized = []
    for cue in expanded:
        text = " ".join((cue.get("text") or "").split())
        if not text:
            continue

        start = int(cue["start"])
        end = int(cue["end"])
        if end <= start:
            end = start + MIN_CUE_DURATION_MS

        if normalized:
            prev = normalized[-1]

            if start < prev["end"]:
                # Overlapping cues — check if near-duplicate.
                ratio = _word_overlap_ratio(text, prev["text"])
                if ratio >= DUPLICATE_WORD_OVERLAP_THRESHOLD:
                    # Chunk-overlap artifact: keep the more complete version.
                    if len(text) > len(prev["text"]):
                        prev["text"] = text
                        prev["end"] = max(prev["end"], end)
                        if "words" in cue and cue["words"]:
                            prev["words"] = cue["words"]
                    elif not prev.get("words") and cue.get("words"):
                        prev["words"] = cue["words"]
                    continue

                # Different content overlapping: trim prev's end so curr
                # keeps its original start (better audio synchronisation).
                desired = start - MIN_GAP_MS
                if desired > prev["start"]:
                    prev["end"] = desired
                else:
                    # prev would shrink to nothing — shift curr instead.
                    start = prev["end"] + MIN_GAP_MS
                    if end <= start:
                        end = start + MIN_CUE_DURATION_MS

        entry = {"start": start, "end": end, "text": text}
        if "words" in cue and cue["words"]:
            entry["words"] = cue["words"]
        normalized.append(entry)

    return _finalize_readable_cues(normalized)


def _probe_bitrate_bps(audio_path):
    """Return source bitrate in bps from ffprobe, or None if unavailable."""
    ffprobe_bin = _resolve_binary("ffprobe")
    if not ffprobe_bin:
        return None

    try:
        res = subprocess.run(
            [
                ffprobe_bin,
                "-v",
                "error",
                "-show_entries",
                "stream=bit_rate:format=bit_rate",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None

    if res.returncode != 0:
        return None

    for line in res.stdout.splitlines():
        line = line.strip()
        if line.isdigit() and int(line) > 0:
            return int(line)
    return None


def _probe_duration_seconds(audio_path):
    """Return audio duration in seconds from ffprobe, or None if unavailable."""
    ffprobe_bin = _resolve_binary("ffprobe")
    if not ffprobe_bin:
        return None

    try:
        res = subprocess.run(
            [
                ffprobe_bin,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None

    if res.returncode != 0:
        return None

    try:
        return float(res.stdout.strip())
    except (TypeError, ValueError):
        return None


def _derive_chunk_length_seconds(audio_path, file_size_bytes, max_upload_bytes=None):
    """Compute chunk length with a data-driven estimate.

    Primary path: use actual file size and duration to estimate average bytes/s,
    then target the largest chunk duration that stays under upload headroom.
    Fallback: use target bitrate if duration probing fails.
    """
    if max_upload_bytes is None:
        max_upload_bytes = MAX_SINGLE_UPLOAD_BYTES
    target_bytes = max_upload_bytes * CHUNK_UPLOAD_HEADROOM_RATIO
    duration_s = _probe_duration_seconds(audio_path)

    if duration_s and duration_s > 0 and file_size_bytes > 0:
        avg_bytes_per_second = file_size_bytes / duration_s
        if avg_bytes_per_second > 0:
            seconds = int(target_bytes / avg_bytes_per_second)
            return max(MIN_CHUNK_LENGTH_SECONDS, seconds)

    if TARGET_BITRATE_BPS <= 0:
        return MIN_CHUNK_LENGTH_SECONDS

    seconds = int((target_bytes * 8) / TARGET_BITRATE_BPS)
    return max(MIN_CHUNK_LENGTH_SECONDS, seconds)


def _split_into_chunks(audio_path, chunk_length_s, overlap_s, output_dir):
    """Split audio into overlapping chunks and return chunk metadata.

    Returns list of dicts:
      {path, start_s, end_s, keep_from_s, keep_to_s}
    """
    duration = _probe_duration_seconds(audio_path)
    if not duration or duration <= 0:
        return []

    base, ext = os.path.splitext(os.path.basename(audio_path))
    step = max(1.0, float(chunk_length_s) - float(overlap_s))
    chunks = []
    start = 0.0
    idx = 0

    ffmpeg_bin = _resolve_binary("ffmpeg")
    if not ffmpeg_bin:
        return []

    while start < duration:
        end = min(start + float(chunk_length_s), duration)
        chunk_path = os.path.join(output_dir, f"{base}.chunk{idx:04d}{ext}")

        try:
            subprocess.run(
                [
                    ffmpeg_bin,
                    "-y",
                    "-ss",
                    str(start),
                    "-i",
                    audio_path,
                    "-t",
                    str(max(0.01, end - start)),
                    "-map",
                    "0:a",
                    "-c:a",
                    "copy",
                    chunk_path,
                ],
                capture_output=True,
                timeout=120,
            )
        except (subprocess.TimeoutExpired, OSError):
            return []

        if not os.path.exists(chunk_path) or os.path.getsize(chunk_path) == 0:
            return []

        keep_from = start if idx == 0 else start + (float(overlap_s) / 2.0)
        keep_to = end
        chunks.append(
            {
                "path": chunk_path,
                "start_s": start,
                "end_s": end,
                "keep_from_s": keep_from,
                "keep_to_s": keep_to,
            }
        )
        start += step
        idx += 1

    # Trim trailing overlap for all but final chunk to reduce duplicated text.
    for i in range(len(chunks) - 1):
        chunks[i]["keep_to_s"] = max(
            chunks[i]["keep_from_s"], chunks[i]["end_s"] - (float(overlap_s) / 2.0)
        )

    return chunks


class _ProgressUpload:
    """Report multipart body consumption without changing its bytes or retry policy."""
    def __init__(self,stream,complete):self.stream=stream;self.complete=complete;self.notified=False
    def __getattr__(self,name):return getattr(self.stream,name)
    def read(self,size=-1):
        data=self.stream.read(size)
        if not self.notified and self.stream.tell()>=os.fstat(self.stream.fileno()).st_size:
            self.notified=True;self.complete()
        return data


def _post_transcription(upload_path, url, headers, params, mime, max_attempts, capture=None, upload_filename=None,on_progress=None):
    """Upload one file to the transcription endpoint with retry logic."""
    last_error = None
    upload = capture.preserve("upload", upload_path) if capture else None
    for attempt in range(1, max_attempts + 1):
        started = time.monotonic()
        try:
            with open(upload_path, "rb") as f:
                if on_progress:on_progress('upload','Uploading audio…')
                upload_stream=_ProgressUpload(f,lambda:on_progress('transcribe','Waiting for transcription…')) if on_progress else f
                files = {"file": (upload_filename or os.path.basename(upload_path), upload_stream, mime)}
                with httpx.Client(timeout=300.0) as client:
                    resp = client.post(
                        url,
                        headers=headers,
                        files=files,
                        data=params,
                    )
        except (httpx.TransportError, httpx.TimeoutException) as e:
            if capture:
                capture.record("asr-attempt", {"upload": upload, "params": params,
                    "mime": mime, "attempt": attempt, "status": "transport-error"})
            last_error = f"attempt {attempt}: {type(e).__name__}"
            last_failure = OperationFailure('upload', 'timeout' if isinstance(e, httpx.TimeoutException) else 'network')
            print(f"  {last_error}", file=sys.stderr)
            if attempt < max_attempts:
                time.sleep(2)
            continue

        if capture:
            capture.record("asr-attempt", {"upload": upload, "params": params,
                "mime": mime, "attempt": attempt, "status": resp.status_code,
                "durationMs": round((time.monotonic() - started) * 1000),
                "response": resp.json() if resp.status_code == 200 else None})
        if resp.status_code >= 500:
            last_failure = http_failure('transcription', resp.status_code)
            last_error = (
                f"attempt {attempt}: HTTP {resp.status_code}"
            )
            print(f"  {last_error}", file=sys.stderr)
            if attempt < max_attempts:
                time.sleep(2)
            continue

        if resp.status_code != 200:
            raise http_failure('transcription', resp.status_code)

        result = resp.json()
        print("  ASR response received", file=sys.stderr)
        return result

    raise last_failure if last_error is not None else OperationFailure('upload', 'unknown')


def _merge_chunk_results(chunk_results):
    """Merge chunk transcription results while trimming overlap windows.

    FunASR verbose_json stores word timestamps inside each segment.  Preserve
    those nested words and convert their chunk-local times to the video's
    absolute timeline so parse_cues() can build accurately timed captions.
    """
    merged_segments = []
    merged_words = []
    merged_text_parts = []

    has_segments = any(
        isinstance(r["result"].get("segments"), list) and r["result"].get("segments")
        for r in chunk_results
    )
    has_top_level_words = any(
        isinstance(r["result"].get("words"), list) and r["result"].get("words")
        for r in chunk_results
    )

    for item in chunk_results:
        result = item["result"]
        start_s = item["start_s"]
        keep_from_s = item["keep_from_s"]
        keep_to_s = item["keep_to_s"]

        if has_segments:
            for seg in result.get("segments") or []:
                seg_start = float(seg.get("start", 0)) + start_s
                seg_end = float(seg.get("end", 0)) + start_s
                if seg_end <= keep_from_s or seg_start >= keep_to_s:
                    continue

                merged_seg = {
                    "start": seg_start,
                    "end": seg_end,
                    "text": (seg.get("text") or "").strip(),
                }
                if seg.get("speaker") is not None:
                    merged_seg["speaker"] = seg.get("speaker")

                # FunASR puts real word timestamps here.  Convert them to the
                # absolute video timeline and discard words that belong to the
                # neighboring chunk's half of the overlap.
                nested_words = seg.get("words") or []
                if isinstance(nested_words, list) and nested_words:
                    absolute_words = []
                    for word in nested_words:
                        try:
                            w_start = float(word.get("start", 0)) + start_s
                            w_end = float(word.get("end", 0)) + start_s
                        except (TypeError, ValueError):
                            continue
                        if w_end <= keep_from_s or w_start >= keep_to_s:
                            continue
                        w_text = word.get("word") or word.get("token") or ""
                        if not str(w_text).strip() or w_end <= w_start:
                            continue
                        absolute_words.append(
                            {
                                "word": str(w_text),
                                "start": w_start,
                                "end": w_end,
                            }
                        )

                    if absolute_words:
                        merged_seg["words"] = absolute_words
                        # Tighten the coarse segment boundary to the actual
                        # words retained from this overlap window.
                        merged_seg["start"] = absolute_words[0]["start"]
                        merged_seg["end"] = absolute_words[-1]["end"]
                    else:
                        # This segment overlaps the keep window only through
                        # audio outside its retained words, so do not duplicate
                        # its text in the merged result.
                        continue

                merged_segments.append(merged_seg)

        if has_top_level_words:
            for word in result.get("words") or []:
                try:
                    w_start = float(word.get("start", 0)) + start_s
                    w_end = float(word.get("end", 0)) + start_s
                except (TypeError, ValueError):
                    continue
                if w_end <= keep_from_s or w_start >= keep_to_s:
                    continue
                merged_words.append(
                    {
                        "word": word.get("word") or word.get("token") or "",
                        "start": w_start,
                        "end": w_end,
                    }
                )

        if not has_segments and not has_top_level_words:
            txt = (result.get("text") or "").strip()
            if txt:
                merged_text_parts.append(txt)

    merged = {"text": "", "segments": []}
    if has_segments:
        merged_segments.sort(key=lambda x: x["start"])
        merged["segments"] = merged_segments
        merged["text"] = " ".join(
            s["text"] for s in merged_segments if s["text"]
        ).strip()
    else:
        merged["segments"] = []

    if has_top_level_words:
        merged_words.sort(key=lambda x: x["start"])
        merged_words, _ = _strip_hallucinated_words(merged_words)
        merged["words"] = merged_words

    if not merged["text"]:
        merged["text"] = " ".join(merged_text_parts).strip()

    return merged

def _transcribe_one_chunk(
    chunk_index,
    total,
    chunk,
    url,
    headers,
    params,
    mime,
    max_attempts,
    on_progress=None,
    capture=None,
):
    """Transcribe a single chunk and return merge-ready metadata."""
    print(f"  Transcribing chunk {chunk_index}/{total}", file=sys.stderr)
    result = _post_transcription(
        chunk["path"],
        url,
        headers,
        params,
        mime,
        max_attempts,
        capture=capture,
        on_progress=on_progress,
    )
    _dump_debug_json(
        f"chunk_{chunk_index:04d}_raw.json",
        {
            "chunk_index": chunk_index,
            "total_chunks": total,
            "requested_start_s": chunk["start_s"],
            "requested_end_s": chunk["end_s"],
            "keep_from_s": chunk["keep_from_s"],
            "keep_to_s": chunk["keep_to_s"],
            "actual_chunk_duration_s": _probe_duration_seconds(chunk["path"]),
            "chunk_filename": os.path.basename(chunk["path"]),
            "request_params": params,
            "response": result,
        },
    )
    if on_progress and capture:
        on_progress(
            "transcribe_raw",
            f"Raw API response chunk {chunk_index}/{total}",
            raw=result,
        )
    return {
        "chunk_index": chunk_index,
        "result": result,
        "start_s": chunk["start_s"],
        "keep_from_s": chunk["keep_from_s"],
        "keep_to_s": chunk["keep_to_s"],
    }


def _validate_prepared_audio(path):
    """Reject unusable preparation before any upload; never change encoding."""
    ffprobe_bin = _resolve_binary("ffprobe")
    if not ffprobe_bin:
        raise RuntimeError("ffprobe executable not found; prepared audio validation is required")
    try:
        result = subprocess.run([ffprobe_bin, "-v", "error", "-select_streams", "a",
            "-show_entries", "stream=codec_name,sample_rate,channels:format=duration",
            "-of", "json", path], capture_output=True, timeout=30)
        if result.returncode != 0:
            raise ValueError("Probe failed")
        info = json.loads(result.stdout)
        streams = info.get("streams", [])
        duration = float(info.get("format", {}).get("duration", 0))
        if (len(streams) != 1 or streams[0].get("codec_name") != "opus"
                or int(streams[0].get("sample_rate", 0)) != TARGET_SAMPLE_RATE_HZ
                or streams[0].get("channels") != TARGET_CHANNELS
                or not math.isfinite(duration) or duration <= 0):
            raise ValueError("Unexpected prepared audio")
    except (subprocess.SubprocessError, OSError, ValueError, TypeError, AttributeError, KeyError) as error:
        raise RuntimeError("Prepared audio validation failed; no audio was uploaded") from error


def compress_audio(audio_path, on_progress=None):
    """Re-encode to normalized sample-rate/channels in Ogg/Opus.

    Uses a fixed target bitrate for consistent upload sizing and chunking math.
    Fails closed when conversion is not possible; uploading a different
    unprepared source would invalidate the production ASR contract.
    """
    if on_progress is None:
        on_progress = _noop_progress
    ffmpeg_bin = _resolve_binary("ffmpeg")
    if not ffmpeg_bin:
        raise RuntimeError("ffmpeg executable not found; audio preparation is required")

    file_size = os.path.getsize(audio_path)
    orig_mb = file_size / 1024 / 1024
    base, ext = os.path.splitext(audio_path)
    compressed = base + ".compressed" + TARGET_OUTPUT_EXT

    on_progress(
        "compress",
        f"Compressing {orig_mb:.1f} MB {ext} → Opus...",
    )

    try:
        cmd = [
            ffmpeg_bin,
            "-y",
            "-i",
            audio_path,
            "-ar",
            str(TARGET_SAMPLE_RATE_HZ),
            "-ac",
            str(TARGET_CHANNELS),
            "-map",
            "0:a",
            "-c:a",
            TARGET_OUTPUT_CODEC,
            "-b:a",
            str(TARGET_BITRATE_BPS),
        ]
        cmd.append(compressed)

        completed = subprocess.run(
            cmd,
            capture_output=True,
            timeout=120,
        )

        if completed.returncode != 0:
            raise RuntimeError(f"ffmpeg exited with code {completed.returncode}")
        if os.path.exists(compressed) and os.path.getsize(compressed) > 0:
            _validate_prepared_audio(compressed)
            new_size = os.path.getsize(compressed)
            new_mb = new_size / 1024 / 1024
            on_progress(
                "compress",
                f"Compressed {orig_mb:.1f} MB → {new_mb:.1f} MB Opus",
            )
            return compressed
    except (subprocess.TimeoutExpired, OSError) as error:
        raise RuntimeError(f"ffmpeg audio preparation failed ({type(error).__name__}); no audio was uploaded") from error

    raise RuntimeError("ffmpeg produced no usable prepared audio")


def transcribe(
    audio_path,
    api_key,
    base_url,
    model,
    max_attempts=DEFAULT_MAX_API_ATTEMPTS,
    language=None,
    prompt=None,
    parallel_uploads=None,
    mb_per_req=None,
    on_progress=None,
    capture=None,
):
    """Send audio file to a Whisper-compatible API (OpenAI, Groq, etc.).

    Returns the raw JSON response dict from the API.
    """
    if on_progress is None:
        on_progress = _noop_progress

    url = f"{base_url.rstrip('/')}/audio/transcriptions"

    # Resolve configurable upload size limit.
    if mb_per_req is not None:
        try:
            mb_per_req = max(1, min(25, int(mb_per_req)))
        except (TypeError, ValueError):
            mb_per_req = MAX_SINGLE_UPLOAD_MEGABYTES
    else:
        mb_per_req = MAX_SINGLE_UPLOAD_MEGABYTES

    max_upload_bytes = mb_per_req * 1024 * 1024

    # Normalize the full file first, then chunk only if still over size limit.
    upload_path = compress_audio(audio_path, on_progress=on_progress)
    if capture:
        capture.record("audio-preparation", {
            "source": capture.preserve("source", audio_path),
            "prepared": capture.preserve("prepared", upload_path),
            "sampleRate": TARGET_SAMPLE_RATE_HZ, "channels": TARGET_CHANNELS,
            "codec": TARGET_OUTPUT_CODEC, "bitrate": TARGET_BITRATE_BPS,
            "conversionSucceeded": upload_path != audio_path,
            "duration": _probe_duration_seconds(upload_path),
            "ffmpegVersion": subprocess.check_output([_resolve_binary("ffmpeg"), "-version"],
                text=True).splitlines()[0],
        })

    file_size = os.path.getsize(upload_path)
    ext = os.path.splitext(upload_path)[1].lower()
    file_mb = file_size / 1024 / 1024
    mime = MIME_TYPES.get(ext, "application/octet-stream")
    params = build_transcription_params(model, language, prompt)
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    if parallel_uploads is None:
        parallel_uploads = CHUNK_MAX_PARALLEL_UPLOADS
    try:
        parallel_uploads = int(parallel_uploads)
    except (TypeError, ValueError):
        parallel_uploads = CHUNK_MAX_PARALLEL_UPLOADS
    parallel_uploads = max(1, min(16, parallel_uploads))
    if capture:
        capture.record("asr-config", {"model": model, "endpoint": base_url,
            "params": params, "maxUploadBytes": max_upload_bytes,
            "parallelUploads": parallel_uploads, "maxAttempts": max_attempts})

    if file_size <= max_upload_bytes:
        on_progress(
            "transcribe",
            f"Uploading {file_mb:.1f} MB {ext} to {model}...",
        )
        result = _post_transcription(
            upload_path, url, headers, params, mime, max_attempts, capture=capture,on_progress=on_progress
        )
        _dump_debug_json(
            "single_raw.json",
            {
                "upload_filename": os.path.basename(upload_path),
                "actual_upload_duration_s": _probe_duration_seconds(upload_path),
                "request_params": params,
                "response": result,
            },
        )
        if capture:
            on_progress("transcribe_raw", "Raw API response", raw=result)
        on_progress("transcribe", "Transcription complete")
        return result

    chunk_length_s = _derive_chunk_length_seconds(
        upload_path, file_size, max_upload_bytes
    )
    on_progress(
        "transcribe",
        f"Splitting {file_mb:.1f} MB into ~{chunk_length_s}s chunks...",
    )

    with tempfile.TemporaryDirectory(prefix="cueflora_chunks_") as chunk_dir:
        chunks = _split_into_chunks(
            upload_path,
            chunk_length_s,
            CHUNK_OVERLAP_SECONDS,
            chunk_dir,
        )
        if not chunks:
            raise RuntimeError("Failed to split audio into chunks")

        total = len(chunks)
        if capture:
            capture.record("chunk-layout", [{k: (os.path.basename(v) if k == "path" else v)
                for k, v in chunk.items()} for chunk in chunks])
        for idx, chunk in enumerate(chunks, start=1):
            chunk_size = os.path.getsize(chunk["path"])
            if chunk_size > max_upload_bytes:
                raise RuntimeError(
                    f"Chunk {idx}/{total} is too large ({chunk_size / 1024 / 1024:.1f} MB)"
                )

        workers = max(1, min(parallel_uploads, total))
        on_progress(
            "transcribe",
            f"Uploading {total} chunks to {model} (parallel={workers})...",
        )

        chunk_results = []
        completed = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(
                    _transcribe_one_chunk,
                    idx,
                    total,
                    chunk,
                    url,
                    headers,
                    params,
                    mime,
                    max_attempts,
                    on_progress,
                    capture,
                )
                for idx, chunk in enumerate(chunks, start=1)
            ]

            for future in concurrent.futures.as_completed(futures):
                chunk_results.append(future.result())
                completed += 1
                pct = round(100 * completed / total)
                on_progress(
                    "transcribe",
                    f"Transcribing... {completed}/{total} chunks ({pct}%)",
                    percent=pct,
                )

        # Preserve timeline order for overlap trimming/merge logic.
        chunk_results.sort(key=lambda x: x["chunk_index"])
        on_progress("transcribe", "Transcription complete")

        merged_result = _merge_chunk_results(chunk_results)
        _dump_debug_json(
            "merged_raw.json",
            {
                "chunks": [
                    {
                        "chunk_index": item["chunk_index"],
                        "start_s": item["start_s"],
                        "keep_from_s": item["keep_from_s"],
                        "keep_to_s": item["keep_to_s"],
                    }
                    for item in chunk_results
                ],
                "response": merged_result,
            },
        )
        return merged_result
