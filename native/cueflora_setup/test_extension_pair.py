import json
from pathlib import Path
import platform
import tempfile
import unittest
from unittest.mock import patch
from .bundle import digest
from .engine import Setup
from .extension_pair import identity,tree,INVENTORY,verify_extension
from .test_setup import FakeRegistration
from cueflora_host.activity import RunLease


class PairedSetupTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='CueFlora pair Ω ');self.addCleanup(self.temporary.cleanup)
        self.base=Path(self.temporary.name).resolve();self.root=self.base/'CueFlora'
        self.registration=FakeRegistration();self.setup=Setup(self.root,self.base,'Windows',self.registration)
        identity_file=Path(__file__).resolve().parents[2]/'preview-identity.json'
        values=json.loads(identity_file.read_text());self.key=values.get('publicKey') or values.get('key')
        if not self.key:
            self.key=values['chromePublicKey']
    def extension(self,name,version,inventoried=True):
        folder=self.base/name;folder.mkdir()
        (folder/'manifest.json').write_text(json.dumps({'manifest_version':3,'name':'CueFlora','version':version,'key':self.key}))
        (folder/'background.js').write_text('/* synthetic '+version+' */')
        chrome_id,_=identity(folder)
        if inventoried:(folder/INVENTORY).write_text(json.dumps({'schema':1,'product':'cueflora','version':version,'chromeId':chrome_id,'files':tree(folder)}))
        return folder,chrome_id
    def payload(self,name,version,extension=None):
        folder=self.base/name;folder.mkdir();(folder/'cueflora-host.exe').write_bytes(b'synthetic '+version.encode())
        (folder/'runtime-manifest.json').write_text(json.dumps({'schema':1,'product':'cueflora','prototype':True,'platform':'Windows','architecture':platform.machine(),'hostVersion':version,'files':{'cueflora-host.exe':digest(folder/'cueflora-host.exe')}}))
        release={'owner':'Synthetic private test','mode':'private','product':'cueflora','extensionIds':{'chrome':identity(extension)[0] if extension else 'a'*32},'runtimeInventorySha256':digest(folder/'runtime-manifest.json'),'publicReleaseAuthorized':False,'redistributionApproved':False}
        if extension:release['extensionInventorySha256']=digest(extension/INVENTORY)
        return folder,release
    def test_install_upgrade_paired_rollback_repair_uninstall_and_settings_preservation(self):
        extension,chrome_id=self.extension('ext-one','0.2.0');payload,release=self.payload('native-one','0.2.0',extension)
        first=self.setup.install(payload,release,['chrome'],extension=extension)
        stable=Path(first['extension']['directory']);self.assertEqual(stable,self.root/'Chrome-extension')
        (self.root/'synthetic-user-settings').write_text('do not change')
        second_ext,_=self.extension('ext-two','0.2.1');second_payload,second_release=self.payload('native-two','0.2.1',second_ext)
        second=self.setup.install(second_payload,second_release,['chrome'],extension=second_ext)
        self.assertEqual(identity(stable)[1],'0.2.1')
        self.setup.rollback();self.assertEqual(identity(stable)[1],'0.2.0')
        self.setup.rollback();self.assertEqual(identity(stable)[1],'0.2.1')
        self.setup.repair(second_payload,extension=second_ext)
        with RunLease(self.root):
            with self.assertRaisesRegex(RuntimeError,'active'):self.setup.uninstall()
        removed=self.setup.uninstall();self.assertTrue(removed.exists());self.assertFalse(stable.exists())
        self.assertEqual((self.root/'synthetic-user-settings').read_text(),'do not change')
        self.assertTrue(Path(self.setup.state()['removedExtensionTo']).exists())
    def test_explicit_legacy_adoption_registration_failure_and_interruption_recovery(self):
        old,chrome_id=self.extension('loaded-extension','0.1.13',False)
        legacy=[{'version':'0.1.13','chromeId':chrome_id,'files':tree(old)}]
        old_payload,old_release=self.payload('old-host','0.1.13');old_release['extensionIds']['chrome']=chrome_id
        previous=self.setup.install(old_payload,old_release,['chrome'])
        new,unused=self.extension('new-extension','0.2.0');payload,release=self.payload('new-host','0.2.0',new)
        with patch('cueflora_setup.extension_pair.legacy_releases',return_value=legacy):
            with self.assertRaisesRegex(ValueError,'confirmation'):self.setup.install(payload,release,['chrome'],extension=new,adopt_extension=old)
            self.registration.fail_once=True
            with self.assertRaises(OSError):self.setup.install(payload,release,['chrome'],extension=new,adopt_extension=old,confirm_adoption=True)
            self.assertEqual(tree(old),legacy[0]['files']);self.assertEqual(self.setup.state()['current'],previous['current'])
            original=self.registration.write_pointer
            with patch.object(self.registration,'write_pointer',side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):self.setup.install(payload,release,['chrome'],extension=new,adopt_extension=old,confirm_adoption=True)
            self.assertTrue((self.root/'pending-activation.json').exists())
            self.setup.recover();self.assertEqual(tree(old),legacy[0]['files'])
            self.setup.install(payload,release,['chrome'],extension=new,adopt_extension=old,confirm_adoption=True)
            self.assertEqual(identity(old)[1],'0.2.0')
            with self.assertRaisesRegex(ValueError,'0.1.x'):self.setup.rollback()
    def test_modified_foreign_missing_and_mismatched_payloads(self):
        ext,unused=self.extension('ext','0.2.0');payload,release=self.payload('host','0.2.0',ext)
        with self.assertRaises(ValueError):self.setup.install(payload,{**release,'extensionInventorySha256':'0'*64},['chrome'],extension=ext)
        installed=self.setup.install(payload,release,['chrome'],extension=ext);stable=Path(installed['extension']['directory'])
        (stable/'foreign.txt').write_text('leave me')
        with self.assertRaisesRegex(ValueError,'foreign'):self.setup.repair(payload,extension=ext)
        self.assertEqual((stable/'foreign.txt').read_text(),'leave me')
        (stable/'foreign.txt').unlink();stable.rename(self.base/'saved-missing-folder')
        self.setup.repair(payload,extension=ext);verify_extension(stable,release['extensionInventorySha256'])


if __name__=='__main__':unittest.main()
