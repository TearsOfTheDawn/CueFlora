import json
from pathlib import Path
import tempfile
import unittest
from cueflora_setup.bundle import digest
from verify_installer import verify_embedded


class InstallerVerificationTests(unittest.TestCase):
    def test_public_identity_checked_without_preview_id_assumption(self):
        # Synthetic configuration is confined to this non-installing unit test.
        with tempfile.TemporaryDirectory() as folder:
            runtime=Path(folder)
            metadata={'product':'cueflora','platform':'Windows','architecture':'AMD64','transportPolicy':'https-remote',
                'sourceInventorySha256':'c'*64,'publicEvidence':None}
            (runtime/'runtime-manifest.json').write_text(json.dumps(metadata))
            release={'schema':2,'mode':'public','product':'cueflora','owner':'Synthetic test publisher','extensionIds':{'chrome':'a'*32},
                'privacyUrl':'https://fixture.example.com/privacy','downloadUrl':'https://fixture.example.com/download',
                'supportUrl':'https://fixture.example.com/support','runtimeInventorySha256':digest(runtime/'runtime-manifest.json'),
                'sourceInventorySha256':'c'*64,'signing':'unsigned','publicReleaseAuthorized':False,'redistributionApproved':False}
            value={'release':release,'inventory':metadata}
            verify_embedded(value,runtime,release)
            with self.assertRaises(ValueError): verify_embedded({**value,'release':{**release,'owner':'Different'}},runtime,release)
            with self.assertRaises(ValueError): verify_embedded({**value,'inventory':{**metadata,'transportPolicy':'preview'}},runtime,release)

    def test_private_configuration_and_every_embedded_field_are_checked(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime=Path(folder); metadata={'product':'cueflora'}
            (runtime/'runtime-manifest.json').write_text(json.dumps(metadata))
            release={'mode':'private','owner':'Synthetic test','extensionIds':{'chrome':'b'*32},'product':'cueflora',
                'runtimeInventorySha256':digest(runtime/'runtime-manifest.json'),'publicReleaseAuthorized':False,'redistributionApproved':False}
            value={'release':release,'inventory':metadata}
            verify_embedded(value,runtime,release)
            with self.assertRaises(ValueError): verify_embedded({**value,'release':{**release,'extensionIds':{'chrome':'a'*32}}},runtime,release)
