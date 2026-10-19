import base64
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib
from .update_payload import COOKIE,ENTRY,MAGIC,inventories,verify_update_payload
from .test_updates import manifest


class UpdatePayloadTests(unittest.TestCase):
    def data(self):
        identity=json.loads((Path(__file__).resolve().parents[2]/'packaging/github-identity.json').read_text())
        data=manifest()
        chrome=json.dumps({'name':'CueFlora','version':data['version'],'key':identity['chromePublicKey']}).encode()
        extension=json.dumps({'schema':1,'product':'cueflora','chromeId':data['chromeId'],'version':data['version'],'files':{'manifest.json':hashlib.sha256(chrome).hexdigest()}}).encode()
        runtime=json.dumps({'schema':1,'product':'cueflora','platform':'Windows','architecture':'AMD64','transportPolicy':'https-remote','hostVersion':data['version'],'sourceInventorySha256':data['sourceInventorySha256']}).encode()
        data['runtimeInventorySha256']=hashlib.sha256(runtime).hexdigest();data['extensionInventorySha256']=hashlib.sha256(extension).hexdigest()
        release=json.dumps({'product':'cueflora','mode':'public','distribution':'github','repositoryUrl':'https://github.com/TearsOfTheDawn/CueFlora',
            'extensionIds':{'chrome':data['chromeId']},'runtimeInventorySha256':data['runtimeInventorySha256'],
            'extensionInventorySha256':data['extensionInventorySha256'],'sourceInventorySha256':data['sourceInventorySha256']}).encode()
        return data,{'bundle/release.json':release,'bundle/runtime/runtime-manifest.json':runtime,'bundle/extension/cueflora-extension.json':extension,'bundle/extension/manifest.json':chrome}
    def executable(self,path,members):
        payload=b'';toc=b''
        for name,raw in members.items():
            packed=zlib.compress(raw);encoded=name.encode()+b'\0';length=ENTRY.size+len(encoded)
            toc+=ENTRY.pack(length,len(payload),len(packed),len(raw),1,b'x')+encoded;payload+=packed
        path.write_bytes(b'MZ'+b'\0'*510+payload+toc+COOKIE.pack(MAGIC,len(payload)+len(toc)+COOKIE.size,len(payload),len(toc),313,b'python313.dll'))
    def test_exact_metadata_binding_without_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'not-executable-setup.exe';data,members=self.data();self.executable(target,members)
            self.assertEqual(verify_update_payload(target,data),{'payloadBindingsVerified':True,'executed':False})
            for field in ('runtimeInventorySha256','extensionInventorySha256','sourceInventorySha256','chromeId','version'):
                with self.subTest(field=field),self.assertRaises(ValueError):verify_update_payload(target,{**data,field:'bad'})
    def test_truncation_missing_members_bombs_and_footer_bounds(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'synthetic.exe';data,members=self.data()
            for invalid in (b'not exe',b'MZ'+b'\0'*1000):
                target.write_bytes(invalid)
                with self.assertRaises(ValueError):inventories(target)
            self.executable(target,{key:value for key,value in members.items() if key!='bundle/release.json'})
            with self.assertRaises(ValueError):inventories(target)
            self.executable(target,members);raw=bytearray(target.read_bytes());raw[-COOKIE.size:]=COOKIE.pack(MAGIC,len(raw)*2,1,32,313,b'python313.dll');target.write_bytes(raw)
            with self.assertRaises(ValueError):inventories(target)


if __name__=='__main__':unittest.main()
