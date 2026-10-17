"""YouTube audio download via system-installed yt-dlp CLI."""

import json
import os
import re
import shutil
import struct
import subprocess
import sys
import threading
from pathlib import Path
from .runtime_tools import packaged_tool, download_runtime_options, download_process_environment

# We need a lock-free way to send progress while stdout is used for
# native-messaging frames.  _real_stdout is captured before any redirect.
_real_stdout = None


def _send_on_real_stdout(obj):
    """Send a native-messaging frame on the real stdout."""
    if _real_stdout is None:
        return
    encoded = json.dumps(obj).encode("utf-8")
    _real_stdout.buffer.write(struct.pack("<I", len(encoded)))
    _real_stdout.buffer.write(encoded)
    _real_stdout.buffer.flush()


_PROGRESS_RE = re.compile(
    r"\[download\]\s+([\d.]+)%\s+of\s+\S+" r"(?:\s+at\s+(\S+))?",
)


def _validated_download_path(filepath, tmp_dir):
    """Only nonempty ordinary files in this request's temporary root may upload."""
    try:
        root = Path(tmp_dir).resolve(strict=True)
        candidate = Path(filepath)
        resolved = candidate.resolve(strict=True)
        if candidate.is_symlink() or not resolved.is_relative_to(root) or not resolved.is_file() or resolved.stat().st_size == 0:
            raise ValueError('Unsafe download output')
        return str(resolved)
    except (OSError, ValueError) as error:
        raise RuntimeError('yt-dlp output is missing, empty or outside its temporary processing directory') from error


def _resolve_yt_dlp_executable():
    """Resolve yt-dlp executable path in constrained native-host environments.

    Firefox/Chrome-launched native hosts can run with a minimal PATH, especially
    on macOS. We try PATH first, then common install locations.
    """

    def is_runnable(path):
        if not path or not os.path.isfile(path) or not os.access(path, os.X_OK):
            return False
        try:
            probe = subprocess.run(
                [path, "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=8,
            )
            return probe.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False

    bundled = packaged_tool('yt-dlp')
    if bundled:
        if not is_runnable(bundled):
            raise RuntimeError('Configured yt-dlp cannot run; repair runtime or developer override')
        return bundled

    # Prefer venv-local link created by install.sh.
    venv_bin = os.path.dirname(sys.executable)

    venv_candidates = [
        os.path.join(venv_bin, "yt-dlp.exe"),
        os.path.join(venv_bin, "yt-dlp"),
    ]

    for venv_yt_dlp in venv_candidates:
        if is_runnable(venv_yt_dlp):
            return venv_yt_dlp

    # Prefer common macOS install paths before generic PATH lookups to avoid
    # shell-specific shims that can break in native-host environments.
    preferred_candidates = [
        "/opt/homebrew/bin/yt-dlp",  # Apple Silicon Homebrew
        "/usr/local/bin/yt-dlp",  # Intel Homebrew / manual install
    ]
    for path in preferred_candidates:
        if is_runnable(path):
            return path

    found = shutil.which("yt-dlp")
    if is_runnable(found):
        return found

    candidates = [
        "/usr/bin/yt-dlp",
    ]
    for path in candidates:
        if is_runnable(path):
            return path

    raise RuntimeError(
        "yt-dlp executable not found. Install yt-dlp and ensure it is in PATH, "
        "or set YT_DLP_PATH to its absolute path (e.g. /opt/homebrew/bin/yt-dlp)."
    )


def _stream_progress(pipe, job_id=None, stderr_tail=None):
    """Read yt-dlp stderr line-by-line and relay download progress."""
    for raw in pipe:
        line = raw.decode("utf-8", errors="replace").strip()
        if stderr_tail is not None:
            stderr_tail.append(re.sub(r"https?://\S+", "[media URL]", line)[-500:])
            del stderr_tail[:-20]
        m = _PROGRESS_RE.search(line)
        if m:
            pct = float(m.group(1))
            speed = m.group(2) or "..."
            _send_on_real_stdout(
                {
                    "type": "progress",
                    "jobId": job_id,
                    "stage": "download",
                    "percent": round(pct, 1),
                    "speed": speed,
                }
            )


def download_audio(video_id, tmp_dir, job_id=None, capture=None):
    """Download cheapest audio-only stream via yt-dlp CLI."""
    global _real_stdout
    _real_stdout = sys.stdout
    yt_dlp_bin = _resolve_yt_dlp_executable()

    outtmpl = os.path.join(tmp_dir, "%(id)s.%(ext)s")
    url = f"https://www.youtube.com/watch?v={video_id}"

    cmd = [
        yt_dlp_bin,
        "--format",
        "worstaudio",
        "--output",
        outtmpl,
        "--no-playlist",
        "--no-warnings",
        "--newline",  # one progress line per update (no \r)
        "--print",
        "after_move:filepath",  # print final path to stdout
        url,
    ]
    cmd[1:1] = download_runtime_options()

    if capture:
        # Additional print output only; selection and downloaded audio are unchanged.
        fields = ("id", "title", "description", "format_id", "format_note", "language",
                  "audio_channels", "acodec", "asr", "abr", "duration")
        template = "cueflora_metadata:%(.{" + ",".join(fields) + "})j"
        cmd[1:1] = ["--print", "after_move:" + template]
        try:
            version = subprocess.check_output([yt_dlp_bin, "--version"], text=True, timeout=10).strip()
        except (OSError, subprocess.SubprocessError):
            version = None
            if hasattr(capture, "stages"):
                capture.stages["download-tool"] = "incomplete"
        capture.record("download-tool", {"version": version, "selection": "worstaudio"})

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=download_process_environment(),
        )
    except FileNotFoundError as e:
        raise RuntimeError(
            f"Failed to launch yt-dlp at '{yt_dlp_bin}'. Verify install path, "
            "its shebang interpreter, or set YT_DLP_PATH to a working binary."
        ) from e

    # Stream progress from stderr in a background thread
    stderr_tail = []
    progress_thread = threading.Thread(
        target=_stream_progress, args=(proc.stderr, job_id, stderr_tail), daemon=True
    )
    progress_thread.start()

    stdout_data = proc.stdout.read()
    proc.wait()
    progress_thread.join(timeout=5)

    if proc.returncode != 0:
        detail = " | ".join(stderr_tail[-3:]) if stderr_tail else "no stderr output"
        raise RuntimeError(f"yt-dlp exited with code {proc.returncode}: {detail}")

    lines = stdout_data.decode("utf-8").strip().splitlines()
    if capture:
        for line in lines:
            if line.startswith("cueflora_metadata:"):
                capture.record_lazy("source-metadata", lambda line=line: json.loads(line.split(":", 1)[1]))
        lines = [line for line in lines if not line.startswith("cueflora_metadata:")]
    if not lines:
        raise RuntimeError("yt-dlp completed without printing an output file")
    filepath = lines[-1]

    filepath = _validated_download_path(filepath, tmp_dir)

    _send_on_real_stdout(
        {
            "type": "progress",
            "jobId": job_id,
            "stage": "download",
            "percent": 100,
            "message": "Download complete",
        }
    )

    return filepath
