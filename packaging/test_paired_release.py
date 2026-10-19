import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'native'))
from cueflora_host.updates import CHROME_ID
from stage_release import paired_update_asset,paired_release_notes


class PairedReleaseTests(unittest.TestCase):
    def fixture(self,root):
        setup=root/'CueFlora-0.2.0-Setup.exe';setup.write_bytes(b'synthetic-not-executable'+b'0'*(1024*1024))
        checksum=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
        bindings={'sourceInventorySha256':'a'*64,'runtimeInventorySha256':'b'*64,'setupSha256':checksum(setup),'extensionSha256':'d'*64}
        configuration={'extensionIds':{'chrome':CHROME_ID},'extensionInventorySha256':'c'*64}
        data={'schema':1,'product':'cueflora','repository':'TearsOfTheDawn/CueFlora','version':'0.2.0','platform':'Windows','architecture':'x64','chromeId':CHROME_ID,'minimumUpdaterVersion':'0.2.0',
            'sourceInventorySha256':'a'*64,'runtimeInventorySha256':'b'*64,'extensionInventorySha256':'c'*64,
            'setup':{'name':setup.name,'size':setup.stat().st_size,'sha256':bindings['setupSha256'],'url':'https://github.com/TearsOfTheDawn/CueFlora/releases/download/v0.2.0/'+setup.name}}
        path=root/'CueFlora-0.2.0-update.json';path.write_text(json.dumps(data))
        return path,configuration,bindings,data,{path.name:checksum(path)}

    def test_bound_update_manifest_is_required_and_actual_embedded_pair_is_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();path,config,bindings,data,inventory=self.fixture(root)
            with patch('cueflora_host.update_payload.verify_update_payload') as verify:
                self.assertEqual(paired_update_asset(root,config,bindings,'0.2.0',inventory),(path.name,inventory[path.name]))
                verify.assert_called_once_with(root/data['setup']['name'],data)
                for edit in ('missing','source','identity','setup'):
                    with self.subTest(edit=edit):
                        changed=json.loads(json.dumps(data));modified=dict(inventory)
                        if edit=='missing':modified={}
                        elif edit=='source':changed['sourceInventorySha256']='e'*64
                        elif edit=='identity':changed['chromeId']='a'*32
                        else:changed['setup']['size']+=1
                        path.write_text(json.dumps(changed));modified[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
                        if edit=='missing':modified={}
                        with self.assertRaises(ValueError):paired_update_asset(root,config,bindings,'0.2.0',modified)

    def test_release_notes_explain_single_setup_bootstrap_and_optional_subscription(self):
        text=paired_release_notes({'version':'0.2.0','repository':'TearsOfTheDawn/CueFlora'})
        for marker in ('only required download','CueFlora-0.2.0-Setup.exe','stable folder','one-time manual upgrade','currently loaded CueFlora extension folder','Do not remove/reinstall','translation only','unverified','Check for updates'):
            self.assertIn(marker,text)
        self.assertNotIn('extract it to a permanent folder',text)
