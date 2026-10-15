"""Check the actual project metadata, not third-party dependency versions."""
import json
from pathlib import Path
import re
import tomllib
import unittest


class ProductVersionTests(unittest.TestCase):
    def test_extension_and_native_project_lock_versions_match(self):
        root = Path(__file__).resolve().parent.parent
        package = json.loads((root / 'package.json').read_text(encoding='utf-8'))
        version = package['version']
        self.assertRegex(version, re.compile(r'^\d+\.\d+\.\d+$'))
        npm_lock = json.loads((root / 'package-lock.json').read_text(encoding='utf-8'))
        self.assertEqual(npm_lock['version'], version)
        self.assertEqual(npm_lock['packages']['']['name'], package['name'])
        self.assertEqual(npm_lock['packages']['']['version'], version)
        project = tomllib.loads((root / 'native/pyproject.toml').read_text(encoding='utf-8'))['project']
        self.assertEqual(project['version'], version)
        uv_lock = tomllib.loads((root / 'native/uv.lock').read_text(encoding='utf-8'))
        own_records = [record for record in uv_lock['package'] if record['name'] == project['name']]
        self.assertEqual(len(own_records), 1)
        self.assertEqual(own_records[0]['source'], {'editable': '.'})
        self.assertEqual(own_records[0]['version'], version)
