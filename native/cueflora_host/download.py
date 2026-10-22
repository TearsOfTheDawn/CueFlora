"""YouTube audio download via system-installed yt-dlp CLI."""

import json
import os
import re
import shutil
import struct
import subprocess
import sys
import threading
import queue
import time
from pathlib import Path
from .runtime_tools import packaged_tool, download_runtime_options, download_process_environment
from .owned_process import OwnedProcess
from .tool_process import tool_process_options

# We need a lock-free way to send progress while stdout is used for
# native-messaging frames.  _real_stdout is captured before any redirect.
_real_stdout = None


def _send_on_real_stdout(obj):
    """Send a native-messaging frame on the real stdout."""
    if _real_stdout is None:
        return
    encoded = json.dumps(obj).encode("utf-8")
    from . import _write_lock
    with _write_lock:
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
                **tool_process_options(),
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


def _consume_download(owned, job_id, cancel=None, inactivity=300, overall=3600, clock=time.monotonic):
    """Drain both pipes concurrently. Log spam is not download progress."""
    events = queue.Queue(maxsize=128)
    def pump(name, pipe):
        try:
            while True:
                line = pipe.readline(262145)
                if not line: break
                events.put((name, line))
        finally:
            pipe.close(); events.put((name, None))
    workers = [threading.Thread(target=pump, args=(name, pipe), daemon=True)
               for name, pipe in [('stdout', owned.process.stdout), ('stderr', owned.process.stderr)]]
    for worker in workers: worker.start()
    started = last_progress = clock(); previous_bytes = -1; ended = set(); stdout = []; size = 0; tail = []
    try:
        while len(ended) < 2 or owned.process.poll() is None:
            now = clock()
            if cancel is not None and cancel.is_set(): raise RuntimeError('Audio download cancelled')
            if now - started >= overall: raise RuntimeError('Audio download exceeded the 60-minute limit')
            if now - last_progress >= inactivity: raise RuntimeError('Audio download made no progress for five minutes. Retry the Run.')
            try: name, raw = events.get(timeout=0.2)
            except queue.Empty: continue
            if raw is None: ended.add(name); continue
            if len(raw) > 262144: raise RuntimeError('Invalid oversized downloader output')
            line = raw.decode('utf-8', errors='replace').strip()
            if line.startswith('cueflora_progress:'):
                try:
                    received,total,speed=line.split(':',1)[1].split('|');received=int(received)
                    if received>previous_bytes:previous_bytes=received;last_progress=now
                    progress={'type':'progress','jobId':job_id,'stage':'download'}
                    try:
                        total=float(total)
                        if total>0:progress['percent']=round(min(100,max(0,received*100/total)),1)
                    except ValueError:pass
                    try:
                        speed=float(speed)
                        if 0<=speed<10**12:progress['speed']=f'{speed/1024:.0f} KiB/s'
                    except ValueError:pass
                    _send_on_real_stdout(progress)
                except ValueError:pass
            elif name == 'stdout':
                size += len(raw)
                if size > 2 * 1024 * 1024: raise RuntimeError('Downloader output exceeded its limit')
                stdout.append(line)
            else:
                tail.append(re.sub(r'https?://\S+', '[media URL]', line)[-500:]); del tail[:-20]
        if owned.process.returncode:
            raise RuntimeError(f'yt-dlp exited with code {owned.process.returncode}: ' + ' | '.join(tail[-3:]))
        return stdout
    finally:
        owned.close()
        # Drain any queued items so pipe readers can exit after cancellation.
        for _ in range(256):
            try: events.get_nowait()
            except queue.Empty: break
        for worker in workers: worker.join(timeout=1)


def download_audio(video_id, tmp_dir, job_id=None, capture=None, cancel=None):
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
        "--progress",
        "--progress-template", "download:cueflora_progress:%(progress.downloaded_bytes)s|%(progress.total_bytes,progress.total_bytes_estimate)s|%(progress.speed)s",
        "--socket-timeout", "30", "--retries", "3", "--fragment-retries", "3", "--extractor-retries", "2",
        "--abort-on-unavailable-fragments",
        "--print",
        "after_move:cueflora_filepath:%(filepath)j",  # dedicated JSON path marker, never a progress/log line
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
            version = subprocess.check_output([yt_dlp_bin, "--version"], text=True, timeout=10,
                                              **tool_process_options()).strip()
        except (OSError, subprocess.SubprocessError):
            version = None
            if hasattr(capture, "stages"):
                capture.stages["download-tool"] = "incomplete"
        capture.record("download-tool", {"version": version, "selection": "worstaudio"})

    try:
        owned = OwnedProcess(
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

    _send_on_real_stdout({'type':'progress', 'jobId':job_id, 'stage':'download', 'message':'Connecting to YouTube…'})
    lines = _consume_download(owned, job_id, cancel)
    if capture:
        for line in lines:
            if line.startswith("cueflora_metadata:"):
                capture.record_lazy("source-metadata", lambda line=line: json.loads(line.split(":", 1)[1]))
        lines = [line for line in lines if not line.startswith("cueflora_metadata:")]
    paths=[line.split(':',1)[1] for line in lines if line.startswith('cueflora_filepath:')]
    if not paths:
        raise RuntimeError("yt-dlp completed without printing an output file")
    if len(paths)!=1:raise RuntimeError('yt-dlp returned ambiguous output paths')
    try:filepath=json.loads(paths[0])
    except ValueError:raise RuntimeError('yt-dlp returned an invalid output path') from None
    if not isinstance(filepath,str):raise RuntimeError('yt-dlp returned an invalid output path')

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
