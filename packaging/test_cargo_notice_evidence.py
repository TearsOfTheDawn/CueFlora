import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from cargo_notice_evidence import pins,obtain,inspect,validate_policy


class CargoNoticeEvidenceTests(unittest.TestCase):
    def fixture(self):
        return {'package':[{'name':'example','version':'1.2.3','checksum':'a'*64,'source':'registry+https://github.com/rust-lang/crates.io-index'}]}

    def test_exact_pins_reject_duplicates_paths_and_moving_origins(self):
        fixture=self.fixture(); expected=pins(fixture)
        self.assertEqual(expected[0]['crateFile'],'example-1.2.3.crate')
        for change in ({'name':'../escape'},{'version':'latest'},{'checksum':'bad'},{'source':'git+https://github.com/owner/repo#main'}):
            with self.assertRaises(ValueError): pins({'package':[{**fixture['package'][0],**change}]})
        with self.assertRaises(ValueError): pins({'package':fixture['package']*2})
        with self.assertRaises(ValueError): pins({'package':[fixture['package'][0],{**fixture['package'][0],'name':'Example'}]})

    def test_offline_missing_or_changed_archives_never_fetch(self):
        with tempfile.TemporaryDirectory() as temp,patch('cargo_notice_evidence.urlopen') as network:
            item=pins(self.fixture())[0]; cache=Path(temp)
            with self.assertRaisesRegex(ValueError,'Missing exact'): obtain(item,cache)
            (cache/item['crateFile']).write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'Changed'): obtain(item,cache,online=True)
            network.assert_not_called()

    def test_notice_scope_does_not_treat_nested_notice_as_package_licence(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); path=root/'source.crate'; item=pins(self.fixture())[0]
            with tarfile.open(path,'w') as archive:
                entries={'example-1.2.3/Cargo.toml':b'[package]\nname="example"\nversion="1.2.3"\nlicense="MIT"\n',
                    'example-1.2.3/test-data/LICENSE':b'nested test notice'}
                for name,content in entries.items():
                    member=tarfile.TarInfo(name); member.size=len(content); archive.addfile(member,io.BytesIO(content))
            result=inspect(item,path,root/'output')
            self.assertTrue(result['anyOriginalNoticeAvailable']); self.assertFalse(result['packageRootNoticeAvailable'])

    def test_explicit_license_file_is_retained_without_generic_substitution(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); path=root/'source.crate'; item=pins(self.fixture())[0]
            with tarfile.open(path,'w') as archive:
                for name,content in {'Cargo.toml':b'[package]\nname="example"\nversion="1.2.3"\nlicense-file="terms/original.md"\n','terms/original.md':b'exact original terms'}.items():
                    member=tarfile.TarInfo('example-1.2.3/'+name); member.size=len(content); archive.addfile(member,io.BytesIO(content))
            result=inspect(item,path,root/'output')
            self.assertTrue(result['packageRootNoticeAvailable']); self.assertEqual(len(result['notices']),1)

    def test_changed_cargo_lock_cannot_be_resigned_by_its_own_report(self):
        packages=pins(self.fixture()); raw=b'exact synthetic lock'; source={'sha256':'a'*64}
        policy={'schema':1,'redistributionApproved':False,'denoSourceSha256':'a'*64,'cargoLockSha256':hashlib.sha256(raw).hexdigest(),
            'registryPackageCount':1,'registryPinInventorySha256':hashlib.sha256(json.dumps(packages,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
        with patch('cargo_notice_evidence.Path.read_text',return_value=json.dumps(policy)):
            validate_policy(source,raw,packages)
            with self.assertRaises(ValueError): validate_policy(source,b'tampered lock',packages)
            with self.assertRaises(ValueError): validate_policy(source,raw,[])
