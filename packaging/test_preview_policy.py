import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / 'native'))
sys.path.insert(0,str(ROOT / 'packaging'))
from cueflora_setup.bundle import digest
from cueflora_setup.package_policy import validate_package
from assemble_preview import extension_identity
from cueflora_setup.distribution import distribution_root
from unittest.mock import patch


class PreviewPolicyTests(unittest.TestCase):
    def test_development_identity_matches_public_key_and_has_no_private_key(self):
        identity = json.loads((ROOT / 'preview-identity.json').read_text())
        self.assertEqual(extension_identity(identity['publicKey']),identity['chromeId'])
        self.assertEqual(set(identity),{'developmentOnly','chromeId','publicKey'})
        self.assertTrue(identity['developmentOnly'])

    def test_private_product_binding_and_foreign_runtime_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            metadata={'product':'cueflora','prototype':True}
            (root / 'runtime-manifest.json').write_text(json.dumps(metadata))
            config={'owner':'Private test','mode':'private','product':'cueflora','extensionIds':{'chrome':'a'*32},
                    'runtimeInventorySha256':digest(root / 'runtime-manifest.json'),
                    'publicReleaseAuthorized':False,'redistributionApproved':False}
            validate_package(root,config,metadata,['chrome'])
            for invalid in [{**config,'product':'foreign'}, {**config,'runtimeInventorySha256':'b'*64}, {**config,'redistributionApproved':True}]:
                with self.assertRaises(ValueError): validate_package(root,invalid,metadata,['chrome'])
            with self.assertRaises(ValueError): validate_package(root,config,{'product':'foreign'},['chrome'])
            with self.assertRaises(ValueError): validate_package(root,config,metadata,['firefox'])
            with self.assertRaises(ValueError): validate_package(root,{'owner':'test','extensionIds':{'chrome':'a'*32}},metadata,['chrome'])

    def test_embedded_resources_are_independent_of_launcher_location(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve()
            (root / 'bundle').mkdir()
            (root / 'bundle/release.json').write_text('{}')
            with patch.object(sys,'frozen',True,create=True), patch.object(sys,'_MEIPASS',str(root),create=True), patch.object(sys,'executable','unrelated-launcher.exe'):
                self.assertEqual(distribution_root(),root / 'bundle')
