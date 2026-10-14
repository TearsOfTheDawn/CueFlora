import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'native'))
from cueflora_setup.public_release import validate_public, validate_identity, GATES, DEVELOPMENT_ID
from cueflora_setup.package_policy import validate_package
from cueflora_setup.bundle import digest
from cueflora_host.provider_security import validate_transport


class PublicPolicyTests(unittest.TestCase):
    def test_schema_two_candidate_can_install_without_claiming_approval(self):
        config=self.configuration()
        config.update(schema=2,publicReleaseAuthorized=False,redistributionApproved=False)
        config.pop('evidence')
        validate_identity(config)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            metadata={'product':'cueflora','platform':'Windows','architecture':'AMD64','transportPolicy':'https-remote',
                'sourceInventorySha256':config['sourceInventorySha256'],'publicEvidence':None}
            (root/'runtime-manifest.json').write_text(json.dumps(metadata)); config['runtimeInventorySha256']=digest(root/'runtime-manifest.json')
            validate_package(root,config,metadata,['chrome'])
            for changed in [{**config,'publicReleaseAuthorized':True},{**config,'redistributionApproved':True},{**config,'evidence':{}},
                {**config,'runtimeInventorySha256':'e'*64},{**config,'extensionIds':{'chrome':DEVELOPMENT_ID}}]:
                with self.assertRaises(ValueError): validate_package(root,changed,metadata,['chrome'])
            with self.assertRaises(ValueError): validate_package(root,config,{**metadata,'transportPolicy':'preview'},['chrome'])

    def test_schema_two_optional_key_and_missing_bindings_are_not_fake_identities(self):
        config=self.configuration(); config.update(schema=2,publicReleaseAuthorized=False,redistributionApproved=False)
        config.pop('evidence'); config['runtimeInventorySha256']=None; config['sourceInventorySha256']=None
        validate_identity(config,require_binding=False)
        with self.assertRaises(ValueError): validate_identity(config)
        for key in ('not-base64','c2VjcmV0'):
            with self.assertRaises(ValueError): validate_identity({**config,'chromePublicKey':key},require_binding=False)

    def configuration(self):
        # Synthetic values are confined to tests; never emitted as a release.
        return {'schema':1,'owner':'Synthetic unit-test publisher','mode':'public','product':'cueflora',
            'extensionIds':{'chrome':'a'*32},'privacyUrl':'https://fixture.example.com/privacy',
            'downloadUrl':'https://fixture.example.com/download','supportUrl':'https://fixture.example.com/support',
            'runtimeInventorySha256':'b'*64,'sourceInventorySha256':'c'*64,'signing':'unsigned',
            'publicReleaseAuthorized':True,'redistributionApproved':True,
            'evidence':{name:{'status':'passed','reviewedBy':'Synthetic unit test','reportSha256':'d'*64} for name in GATES}}

    def test_public_requires_every_evidence_and_real_identity_field(self):
        config = self.configuration()
        validate_public(config)
        for field in ('owner','privacyUrl','downloadUrl','supportUrl','runtimeInventorySha256','sourceInventorySha256','evidence'):
            broken = copy.deepcopy(config); broken[field] = None
            with self.subTest(field=field), self.assertRaises(ValueError): validate_public(broken)
        for broken in [{**config,'extensionIds':{'chrome':DEVELOPMENT_ID}}, {**config,'publicReleaseAuthorized':False}, {**config,'privacyUrl':'http://fixture.example.com'}, {**config,'downloadUrl':'https://localhost/download'}, {**config,'supportUrl':'https://127.0.0.2'}, {**config,'apiKey':'must never be packaged'}]:
            with self.assertRaises(ValueError): validate_public(broken)
        broken = copy.deepcopy(config); broken['evidence']['chromeRun']['status'] = 'pending'
        with self.assertRaises(ValueError): validate_public(broken)

    def test_public_inventory_and_source_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = self.configuration()
            metadata = {'product':'cueflora','platform':'Windows','architecture':'AMD64','prototype':True,
                'transportPolicy':'https-remote','sourceInventorySha256':config['sourceInventorySha256'],'publicEvidence':config['evidence']}
            (root/'runtime-manifest.json').write_text(json.dumps(metadata))
            config['runtimeInventorySha256'] = digest(root/'runtime-manifest.json')
            validate_package(root,config,metadata,['chrome'])
            with self.assertRaises(ValueError): validate_package(root,{**config,'runtimeInventorySha256':'e'*64},metadata,['chrome'])
            with self.assertRaises(ValueError): validate_package(root,config,{**metadata,'sourceInventorySha256':'f'*64},['chrome'])
            with self.assertRaises(ValueError): validate_package(root,config,metadata,['firefox'])
            with self.assertRaises(ValueError): validate_package(root,{**config,'mode':'prototype'},metadata,['chrome'])

    def test_frozen_public_transport_cannot_be_downgraded_by_message(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'runtime-manifest.json').write_text(json.dumps({'transportPolicy':'https-remote'}))
            with patch.object(sys,'frozen',True,create=True), patch.object(sys,'executable',str(root/'host.exe')):
                with self.assertRaises(ValueError): validate_transport({'baseUrl':'http://remote.invalid','allowRemoteHttp':True},'preview')
                self.assertEqual(validate_transport({'baseUrl':'http://127.0.0.1:8000'}),'http://127.0.0.1:8000')
                (root/'runtime-manifest.json').write_text('invalid')
                with self.assertRaises(ValueError): validate_transport({'baseUrl':'https://remote.invalid'})
