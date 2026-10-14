import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from node_inputs import validate,restore
from release_inputs import ROOT,digest


class NodeInputsTests(unittest.TestCase):
    def test_real_lock_is_exact_and_cannot_follow_latest_or_change_origins(self):
        lock=json.loads((ROOT/'packaging/node-inputs.lock.json').read_text()); validate(lock)
        for name,value in [('nodeVersion','latest'),('nodeExeSha256','not-a-hash'),('buildOnly',False),('npmFileCount',0)]:
            with self.subTest(field=name),self.assertRaises(ValueError): validate({**lock,name:value})
        with self.assertRaises(ValueError): validate({**lock,'archive':{**lock['archive'],'url':'https://evil.invalid/node.zip'}})

    def test_archive_npm_and_node_bytes_are_checked_before_use(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); archive=root/'node.zip'
            prefix='node-v24.19.0-win-x64/'
            node=b'synthetic node, never executed'; npm=b'{"version":"11.17.0"}'
            npm_files={'node_modules/npm/package.json':hashlib.sha256(npm).hexdigest()}
            lock=json.loads((ROOT/'packaging/node-inputs.lock.json').read_text())
            lock.update(nodeExeSha256=hashlib.sha256(node).hexdigest(),npmFileCount=1,
                npmFileInventorySha256=hashlib.sha256(json.dumps(npm_files,sort_keys=True,separators=(',',':')).encode()).hexdigest())
            with zipfile.ZipFile(archive,'w') as package: package.writestr(prefix+'node.exe',node); package.writestr(prefix+'node_modules/npm/package.json',npm)
            with patch('node_inputs.obtain',return_value=(archive,lock)):
                restored,report=restore(root,root/'restored')
                self.assertEqual((restored/'node.exe').read_bytes(),node); self.assertFalse(report['installedGlobalModulesUsed'])
                with self.assertRaises(ValueError): restore(root,root/'restored')
                bad={**lock,'npmFileInventorySha256':'a'*64}
                with patch('node_inputs.obtain',return_value=(archive,bad)),self.assertRaises(ValueError): restore(root,root/'bad')
            with zipfile.ZipFile(archive,'a') as package: package.writestr(prefix+'../outside',b'bad')
            with patch('node_inputs.obtain',return_value=(archive,lock)),self.assertRaises(ValueError): restore(root,root/'unsafe')
            self.assertFalse((root/'unsafe').exists())
