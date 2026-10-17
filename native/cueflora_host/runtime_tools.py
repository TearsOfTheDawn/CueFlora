"""Bundled tools are release-owned; frozen hosts never silently use PATH."""
import os
from pathlib import Path
import sys
import shutil
import subprocess
import re


def packaged_tool(name):
    """Return an explicit override/bundled path, or None for developer discovery.

    Overrides are opt-in developer controls. A broken override or missing tool
    in a frozen distribution fails closed instead of changing the tool version.
    """
    if name not in ('yt-dlp', 'ffmpeg', 'ffprobe', 'deno'):
        raise ValueError('Unsupported runtime tool')
    override = os.environ.get({'yt-dlp': 'YT_DLP_PATH', 'ffmpeg': 'FFMPEG_PATH', 'ffprobe': 'FFPROBE_PATH', 'deno': 'DENO_PATH'}[name])
    if override:
        candidate = Path(override)
        if not candidate.is_absolute() or not candidate.is_file():
            raise RuntimeError(f'Invalid explicit {name} override')
        return str(candidate)
    if getattr(sys, 'frozen', False):
        candidate = Path(sys.executable).parent / 'tools' / (name + ('.exe' if os.name == 'nt' else ''))
        if not candidate.is_file():
            raise RuntimeError(f'Bundled {name} is missing; repair CueFlora runtime')
        return str(candidate)
    return None


def resolve_deno():
    candidate = packaged_tool('deno') or shutil.which('deno')
    if not candidate:
        raise RuntimeError('Deno is missing; upgrade or repair CueFlora runtime')
    try:
        result = subprocess.run([candidate, '--version'], capture_output=True, text=True, timeout=5)
        version = re.match(r'deno (\d+)\.(\d+)\.(\d+)', result.stdout)
        if result.returncode or not version or tuple(map(int, version.groups())) < (2, 3, 0):
            raise RuntimeError('Deno 2.3.0 or newer is required; upgrade CueFlora runtime')
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError('Deno cannot run; repair CueFlora runtime') from error
    return candidate


def download_process_environment():
    """Packaged solvers must not inherit a different permission authority.

    Deno's permission broker replaces command-line permission decisions. A
    browser inheriting a global broker configuration must not silently retune
    the private solver. Developer (unfrozen) executions retain their own policy.
    Tool-path overrides, proxies and certificates are otherwise unchanged.
    """
    environment = dict(os.environ)
    if getattr(sys, 'frozen', False):
        environment = {key: value for key, value in environment.items()
                       if key.upper() != 'DENO_PERMISSION_BROKER_PATH'}
    return environment


def download_runtime_options():
    # Frozen releases ignore unrelated user configuration/plugins and never
    # fetch EJS components. The solver is included inside the pinned yt-dlp EXE.
    if getattr(sys, 'frozen', False) or os.environ.get('DENO_PATH'):
        return ['--ignore-config', '--no-plugin-dirs', '--no-remote-components',
                '--no-js-runtimes', '--js-runtimes', 'deno:' + resolve_deno()]
    return ['--no-remote-components']
