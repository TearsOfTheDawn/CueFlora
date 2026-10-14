import json
from pathlib import Path
import tempfile
import unittest
from public_materials import build,markdown


class PublicMaterialsTests(unittest.TestCase):
    def configuration(self):
        return {'schema':2,'mode':'public','product':'cueflora','owner':'Synthetic <publisher> only','repositoryUrl':'https://github.com/fixture-owner/fixture-project',
            'extensionIds':{'chrome':'a'*32},'privacyUrl':'https://fixture-owner.github.io/fixture-project/privacy.html',
            'downloadUrl':'https://fixture-owner.github.io/fixture-project/download.html','supportUrl':'https://github.com/fixture-owner/fixture-project/issues',
            'runtimeInventorySha256':None,'sourceInventorySha256':None,'signing':'unsigned','publicReleaseAuthorized':False,'redistributionApproved':False}

    def test_missing_identity_prepares_sources_not_fabricated_public_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'pages'; result=build(output)
            self.assertFalse(result['rendered']); self.assertFalse(result['published'])
            self.assertFalse((output/'index.html').exists())

    def test_real_shaped_values_render_safe_buildless_review_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'pages'; result=build(output,self.configuration(),{'setupSha256':'b'*64})
            self.assertTrue(result['rendered']); self.assertFalse(result['published']); self.assertFalse(result['visualAcceptance'])
            for page in ('index','download','privacy','support'):
                content=(output/(page+'.html')).read_text()
                self.assertIn('lang="en"',content); self.assertNotIn('<script',content)
                self.assertIn('&lt;publisher&gt;',content); self.assertNotIn('<publisher>',content)
            content=(output/'download.html').read_text(); self.assertIn('b'*64,content)
            self.assertIn('review candidate',content); self.assertIn('unsigned',content)
            self.assertIn('href="download.html"',(output/'index.html').read_text())

    def test_unknown_or_missing_repository_hash_and_unsafe_links_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for index,configuration in enumerate([{**self.configuration(),'repositoryUrl':None},{**self.configuration(),'repositoryUrl':'https://github.com/owner/repo/../outside'},{**self.configuration(),'privacyUrl':'http://remote.invalid'},{**self.configuration(),'owner':''}]):
                with self.subTest(index=index),self.assertRaises(ValueError): build(root/str(index),configuration,{'setupSha256':'b'*64})
            with self.assertRaises(ValueError): build(root/'bad-hash',self.configuration(),{'setupSha256':'not-a-hash'})
            self.assertNotIn('<script',markdown('<script>alert(1)</script>'))
            self.assertNotIn('href="javascript:',markdown('[x](javascript:alert(1))'))
