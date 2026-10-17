import json
from pathlib import Path
import tempfile
import unittest
from html.parser import HTMLParser
from release_inputs import digest
from public_materials import build,markdown,privacy_revision


class PublicMaterialsTests(unittest.TestCase):
    def test_privacy_revision_rejects_missing_duplicate_and_invalid_dates(self):
        self.assertEqual(privacy_revision('Policy revision: 2026-10-17.'),'2026-10-17')
        for text in ('','Policy revision: 2026-02-30.',
                'Policy revision: 2026-10-17. Policy revision: 2026-10-17.'):
            with self.subTest(text=text),self.assertRaises(ValueError):
                privacy_revision(text)

    def test_privacy_commitment_and_footer_agree_without_claiming_store_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'pages'
            build(output,self.configuration(),prelaunch=True)
            privacy=(output/'privacy.html').read_text()
            self.assertIn('Limited Use requirements',privacy)
            self.assertIn('not a claim that Google has approved',privacy)
            self.assertIn('does not sell user data',privacy)
            revision=privacy_revision((Path(__file__).resolve().parents[1]/'docs/public/privacy.md').read_text())
            for name in ('index','download','privacy','support'):
                self.assertIn('Privacy policy revision '+revision,(output/(name+'.html')).read_text())

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

    def test_prelaunch_pages_offer_source_and_help_without_binary_or_store_downloads(self):
        class Links(HTMLParser):
            def __init__(self):
                super().__init__(); self.targets=[]
            def handle_starttag(self, tag, attrs):
                if tag in ('a','link'):
                    self.targets.extend(value for name,value in attrs if name=='href')
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'pages'
            result=build(output,self.configuration(),prelaunch=True)
            self.assertFalse(result['published']); self.assertFalse(result['visualAcceptance'])
            self.assertIsNone(result['installerSha256'])
            self.assertEqual(result['releaseStatus'],'prelaunch-source-and-help-only')
            self.assertTrue((output/'.nojekyll').is_file())
            for name in ('index','download','privacy','support'):
                content=(output/(name+'.html')).read_text()
                self.assertIn('Installer and Store item are not released',content)
                self.assertNotIn('Installer SHA-256:',content)
                self.assertNotIn('<script',content)
                parser=Links(); parser.feed(content)
                for link in parser.targets:
                    self.assertNotIn('chromewebstore.google.com',link)
                    self.assertNotIn('/releases/download/',link)
                    self.assertFalse(link.endswith(('.exe','.zip','.msi')))
                    if not link.startswith('https://'):
                        self.assertTrue((output/link).is_file(),link)
            for name,checksum in result['files'].items():
                self.assertEqual(digest(output/name),checksum)

    def test_prelaunch_refuses_artifact_reports_missing_identity_and_implicit_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for index,args in enumerate([
                    {'configuration':self.configuration(),'artifact_report':{'setupSha256':'b'*64},'prelaunch':True},
                    {'prelaunch':True},
                    {'configuration':self.configuration(),'prelaunch':'yes'}]):
                with self.subTest(index=index),self.assertRaises(ValueError):
                    build(root/str(index),**args)
