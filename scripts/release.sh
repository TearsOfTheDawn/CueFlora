#!/usr/bin/env bash
set -euo pipefail
# Compatibility entry point; never read credentials or submit to any service.
case "${1:-}" in
  sign|submit)
    if [ "${2:-}" != "--dry-run" ]; then
      echo "Signing/submission disabled. Use release:prepare for local preparation." >&2
      exit 1
    fi
    cd "$(dirname "$0")/.."
    npm run typecheck
    npm test
    CUEFLORA_BUILD_PROFILE=store-candidate npm run zip:chrome
    ;;
  *) echo "Usage: release.sh {sign|submit} --dry-run (build only)" >&2; exit 1 ;;
esac
