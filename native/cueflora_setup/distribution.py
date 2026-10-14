"""Resolve immutable embedded payloads, not the executable's installation path."""
import sys
from pathlib import Path


def distribution_root():
    if getattr(sys, 'frozen', False):
        # Windows bootloader temporary paths can use an 8.3 spelling. Normalize
        # this bootloader-owned root before strict linked-payload checks.
        embedded = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent)).resolve() / 'bundle'
        return embedded if (embedded / 'release.json').is_file() else Path(sys.executable).parent
    return Path(__file__).resolve().parents[2]
