import copy
import json
import tempfile
from pathlib import Path
import unittest
from release_inputs import ROOT
from observed_sources import validate,obtain
from collect_tool_sources import selected_sources


class ObservedSourceTests(unittest.TestCase):
    def test_locked_sources_include_the_actual_gpl_dependency_without_granting_approval(self):
        lock=json.loads((ROOT/'packaging/observed-tool-sources.lock.json').read_text()); validate(lock)
        mutagen=next(item for item in lock['sources'] if item['package']=='mutagen')
        self.assertEqual(mutagen['version'],'1.48.1'); self.assertIn('GPL',mutagen['declaredLicence'])
        self.assertFalse(lock['redistributionApproved']); self.assertFalse(lock['completeBinaryDependencyClosure'])
        for change in ({'file':'../escape'},{'url':'http://files.pythonhosted.org/source'},{'sha256':'latest'},{'version':'latest'}):
            bad=copy.deepcopy(lock); bad['sources'][0].update(change)
            with self.assertRaises(ValueError): validate(bad)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError): obtain(Path(directory))

    def test_selection_uses_observed_exact_versions_and_normalizes_certifi(self):
        values=selected_sources({'observedOptionalLibraryVersions':[{'name':'certifi','version':'2026.07.22'},{'name':'sqlite3','version':'3.40.1'},{'name':'Cryptodome','version':'3.23.0'}]})
        self.assertEqual(values,[('certifi','2026.7.22'),('pycryptodomex','3.23.0')])
        with self.assertRaises(ValueError): selected_sources({'observedOptionalLibraryVersions':[{'name':'mutagen','version':'latest'}]})
