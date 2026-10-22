"""One discoverable native suite for local, clean-source and CI gates."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]

def suite(root=ROOT):
    native=root/'native'
    result=unittest.TestSuite()
    for package in ('cueflora_host','cueflora_setup'):
        result.addTests(unittest.defaultTestLoader.discover(str(native/package),
                        pattern='test_*.py',top_level_dir=str(native)))
    return result

if __name__=='__main__':
    raise SystemExit(0 if unittest.TextTestRunner(verbosity=1).run(suite()).wasSuccessful() else 1)
