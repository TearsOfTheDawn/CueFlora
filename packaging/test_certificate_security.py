"""Prevent an affected certificate bundle from returning through any build lock."""
import copy
import json
from pathlib import Path
import re
import tomllib
import unittest

from downloader_security import validate_origin, security_manifest
from release_inputs import ROOT

FIXED='2026.10.19'
WHEEL='42d35340cc5b9ba78e818ddbff0c5b1c2b779de448a340fd1b989f5fa8670e1b'


class CertificateSecurityTests(unittest.TestCase):
    def test_host_setup_downloader_and_development_pins_agree(self):
        main=json.loads((ROOT/'packaging/inputs-windows.lock.json').read_text())
        wheel=next(item for item in main['pythonWheels'] if item['name']=='certifi')
        self.assertEqual((wheel['version'],wheel['sha256']),(FIXED,WHEEL))
        entry=next(item for item in main['files'] if item['file']==wheel['file'])
        self.assertEqual(entry['sha256'],WHEEL)
        line=next(line for line in (ROOT/'packaging/requirements-windows-hashed.lock').read_text().splitlines() if line.startswith('certifi=='))
        self.assertEqual(line,'certifi=='+FIXED+' --hash=sha256:'+WHEEL)
        downloader=json.loads((ROOT/'packaging/downloader-inputs.lock.json').read_text())
        item=next(item for item in downloader['dependencies'] if item['name']=='certifi')
        self.assertEqual((item['version'],item['wheel']['sha256']),(FIXED,WHEEL))
        native=tomllib.loads((ROOT/'native/uv.lock').read_text())
        self.assertEqual(next(item['version'] for item in native['package'] if item['name']=='certifi'),FIXED)
        project=tomllib.loads((ROOT/'native/pyproject.toml').read_text())
        self.assertIn('certifi=='+FIXED,project['project']['dependencies'])

    def test_changed_certificate_pin_keeps_original_upstream_baseline_and_primary_evidence(self):
        lock=json.loads((ROOT/'packaging/downloader-inputs.lock.json').read_text())
        item=next(item for item in lock['dependencies'] if item['name']=='certifi')
        self.assertFalse(item['upstreamWheelHashVerified'])
        self.assertEqual(item['securityOverride']['baselineVersion'],'2026.7.22')
        self.assertEqual(item['declaredLicence'],'MPL-2.0')
        validate_origin(item,2)
        self.assertEqual({item['name'] for item in security_manifest(lock)},{'certifi','urllib3'})
        for key in ('source','wheel'):
            changed=copy.deepcopy(item);changed[key]['sha256']='0'*64
            with self.subTest(key=key),self.assertRaises(ValueError):validate_origin(changed,2)
