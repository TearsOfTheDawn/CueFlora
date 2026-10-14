#!/bin/bash
# Install the cueflora native messaging host for Firefox and/or Chrome.
# Requires: uv (https://docs.astral.sh/uv/)
#
# Usage:
#   ./install.sh firefox FIREFOX_EXTENSION_ID # Developer-only Firefox registration
#   ./install.sh chrome CHROME_EXTENSION_ID   # Install for Chrome
#   ./install.sh all CHROME_ID FIREFOX_ID     # Install for both with explicit identities
#
# The Chrome extension ID is required when installing for Chrome. Find it at
# chrome://extensions with Developer mode enabled.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="cueflora_host"
FIREFOX_EXTENSION_ID="${3:-}"

BROWSER="${1:-chrome}"
CHROME_EXT_ID="${2:-}"
if [[ "$BROWSER" == "firefox" ]]; then FIREFOX_EXTENSION_ID="${2:-}"; fi

case "$BROWSER" in
    firefox|chrome|all) ;;
    *)
        echo "Usage: $0 [firefox|chrome|all] [CHROME_EXTENSION_ID]"
        echo ""
        echo "  firefox  Developer registration; requires explicit Firefox ID"
        echo "  chrome   Install for Chrome only (requires extension ID)"
        echo "  all      Install for both Firefox and Chrome"
        echo ""
        echo "Chrome extension ID can be found at chrome://extensions with Developer mode on."
        exit 1
        ;;
esac

if [[ "$BROWSER" == "firefox" || "$BROWSER" == "all" ]] && [[ -z "$FIREFOX_EXTENSION_ID" ]]; then
    echo "Error: no default Firefox identity. Supply an explicit development identity."
    exit 1
fi

if [[ "$BROWSER" == "chrome" || "$BROWSER" == "all" ]] && [[ -z "$CHROME_EXT_ID" ]]; then
    echo "Error: Chrome extension ID is required when installing for Chrome."
    echo ""
    echo "Find your extension ID at chrome://extensions (enable Developer mode)."
    echo "Usage: $0 $BROWSER YOUR_CHROME_EXTENSION_ID"
    exit 1
fi

# Check for uv
if ! command -v uv &>/dev/null; then
    echo "Error: uv is required but not found in PATH."
    echo "Install it: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Install project and dependencies (creates .venv)
echo "Installing cueflora-host and dependencies with uv..."
cd "$SCRIPT_DIR"
uv sync

VENV_BIN="$SCRIPT_DIR/.venv/bin"

resolve_bin() {
    local name="$1"
    local detected=""

    # Remove any existing venv symlink first to avoid circular resolution
    # when the venv is activated and command -v returns the venv's own link.
    rm -f "$VENV_BIN/$name"

    if command -v "$name" &>/dev/null; then
        detected="$(command -v "$name")"
        # Resolve through symlink chains to get the real binary path
        detected="$(python3 -c "import os; print(os.path.realpath('$detected'))")"
    fi

    if [[ -z "$detected" || ! -x "$detected" ]]; then
        detected=""
        for candidate in \
            "/opt/homebrew/bin/$name" \
            "/usr/local/bin/$name" \
            "/usr/bin/$name"; do
            if [[ -x "$candidate" ]]; then
                detected="$(python3 -c "import os; print(os.path.realpath('$candidate'))")"
                break
            fi
        done
    fi

    if [[ -z "$detected" || ! -x "$detected" ]]; then
        echo "Error: $name not found. Install it and re-run ./install.sh"
        exit 1
    fi

    echo "$detected"
}

echo "Linking external binaries into venv for native host runtime..."
YT_DLP_PATH="$(resolve_bin yt-dlp)"
FFMPEG_PATH="$(resolve_bin ffmpeg)"
FFPROBE_PATH="$(resolve_bin ffprobe)"

ln -sf "$YT_DLP_PATH" "$VENV_BIN/yt-dlp"
ln -sf "$FFMPEG_PATH" "$VENV_BIN/ffmpeg"
ln -sf "$FFPROBE_PATH" "$VENV_BIN/ffprobe"

echo "  yt-dlp  -> $YT_DLP_PATH"
echo "  ffmpeg  -> $FFMPEG_PATH"
echo "  ffprobe -> $FFPROBE_PATH"

HOST_BIN="$SCRIPT_DIR/.venv/bin/cueflora-host"
if [[ ! -f "$HOST_BIN" ]]; then
    echo "Error: entry point not found at $HOST_BIN"
    exit 1
fi

# --- Browser-specific manifest installation ---

get_firefox_manifest_dir() {
    if [[ "$OSTYPE" == darwin* ]]; then
        echo "$HOME/Library/Application Support/Mozilla/NativeMessagingHosts"
    elif [[ "$OSTYPE" == linux* ]]; then
        echo "$HOME/.mozilla/native-messaging-hosts"
    else
        echo ""
    fi
}

get_chrome_manifest_dir() {
    if [[ "$OSTYPE" == darwin* ]]; then
        echo "$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts"
    elif [[ "$OSTYPE" == linux* ]]; then
        echo "$HOME/.config/google-chrome/NativeMessagingHosts"
    else
        echo ""
    fi
}

install_firefox() {
    local manifest_dir
    manifest_dir="$(get_firefox_manifest_dir)"
    if [[ -z "$manifest_dir" ]]; then
        echo "Warning: Unsupported OS ($OSTYPE) for Firefox native messaging."
        return 1
    fi

    mkdir -p "$manifest_dir"
    cat > "$manifest_dir/$APP_NAME.json" <<EOF
{
  "name": "$APP_NAME",
  "description": "cueflora native messaging host — downloads YouTube audio via yt-dlp and transcribes via Whisper API",
  "path": "$HOST_BIN",
  "type": "stdio",
  "allowed_extensions": ["$FIREFOX_EXTENSION_ID"]
}
EOF
    echo "  Firefox: $manifest_dir/$APP_NAME.json"
}

install_chrome() {
    local manifest_dir
    manifest_dir="$(get_chrome_manifest_dir)"
    if [[ -z "$manifest_dir" ]]; then
        echo "Warning: Unsupported OS ($OSTYPE) for Chrome native messaging."
        return 1
    fi

    mkdir -p "$manifest_dir"
    cat > "$manifest_dir/$APP_NAME.json" <<EOF
{
  "name": "$APP_NAME",
  "description": "cueflora native messaging host — downloads YouTube audio via yt-dlp and transcribes via Whisper API",
  "path": "$HOST_BIN",
  "type": "stdio",
  "allowed_origins": ["chrome-extension://$CHROME_EXT_ID/"]
}
EOF
    echo "  Chrome:  $manifest_dir/$APP_NAME.json"
}

echo ""
echo "Installed native messaging host:"
echo "  Entry point: $HOST_BIN"

if [[ "$BROWSER" == "firefox" || "$BROWSER" == "all" ]]; then
    install_firefox
fi
if [[ "$BROWSER" == "chrome" || "$BROWSER" == "all" ]]; then
    install_chrome
fi

RESTART_MSG=""
if [[ "$BROWSER" == "firefox" ]]; then
    RESTART_MSG="Restart Firefox for changes to take effect."
elif [[ "$BROWSER" == "chrome" ]]; then
    RESTART_MSG="Restart Chrome for changes to take effect."
else
    RESTART_MSG="Restart Firefox and Chrome for changes to take effect."
fi

echo ""
echo "Done. $RESTART_MSG"
