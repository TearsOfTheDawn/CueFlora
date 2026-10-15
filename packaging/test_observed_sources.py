import copy
import json
import hashlib
import io
import tempfile
import tarfile
import zipfile
from pathlib import Path
import unittest
from unittest.mock import patch
from release_inputs import ROOT
from observed_sources import validate,obtain,collect
from collect_tool_sources import selected_sources


class ObservedSourceTests(unittest.TestCase):
    def test_collect_retains_british_and_unlicense_originals_from_zip_and_tar(self):
        for suffix in ('.zip','.tar.gz'):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as directory:
                root=Path(directory); cache=root/'cache'; cache.mkdir()
                source=cache/('example-1.2.3'+suffix)
                entries={'example/LICENCE.md':b'Original British terms\r\n',
                    'example/UNLICENSE':b'Original dedication\n','example/README.md':b'Not licence terms'}
                if suffix=='.zip':
                    with zipfile.ZipFile(source,'w') as archive:
                        for name,data in entries.items(): archive.writestr(name,data)
                else:
                    with tarfile.open(source,'w:gz') as archive:
                        for name,data in entries.items():
                            member=tarfile.TarInfo(name); member.size=len(data)
                            archive.addfile(member,io.BytesIO(data))
                lock={'observedYtDlpSha256':'a'*64,'sources':[{'package':'example','version':'1.2.3','file':source.name}]}
                with patch('observed_sources.obtain',return_value=lock):
                    report=collect(cache,root/'output',{'ytDlpSha256':'a'*64})
                self.assertEqual(len(report['notices']),2)
                for filename,record in report['notices'].items():
                    original=entries[record['entry']]
                    self.assertEqual((root/'output/notices'/filename).read_bytes(),original)
                    self.assertEqual(record['sha256'],hashlib.sha256(original).hexdigest())
                self.assertFalse(report['redistributionApproved'])
                self.assertFalse(report['completeBinaryDependencyClosure'])

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
