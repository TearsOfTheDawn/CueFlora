import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from build_downloader import validate_lock
from downloader_security import validate_origin,verify_source_pins,security_manifest,verify_runtime_overrides
from release_inputs import ROOT


class DownloaderSecurityTests(unittest.TestCase):
    def setUp(self):
        self.lock=json.loads((ROOT/'packaging/downloader-inputs.lock.json').read_text())
        self.item=next(item for item in self.lock['dependencies'] if item['name']=='urllib3')

    def test_explicit_patch_has_primary_snapshot_and_never_claims_original_upstream_hash(self):
        validate_lock(self.lock)
        self.assertFalse(self.item['upstreamWheelHashVerified'])
        self.assertEqual(self.item['version'],'2.8.0')
        self.assertEqual(self.item['securityOverride']['baselineVersion'],'2.7.0')
        self.assertEqual(len(security_manifest(self.lock)),2)
        self.assertFalse(self.lock['redistributionApproved'])
        self.assertEqual(len(self.lock['dependencies']),13)

    def test_malformed_or_hidden_overrides_and_changed_metadata_fail(self):
        cases=[]
        item=copy.deepcopy(self.item); item['upstreamWheelHashVerified']=True; cases.append(item)
        item=copy.deepcopy(self.item); item.pop('securityOverride'); cases.append(item)
        item=copy.deepcopy(self.item); item['securityOverride']['baselineVersion']='2.8.0'; cases.append(item)
        item=copy.deepcopy(self.item); item['securityOverride']['baselineVersion']='1.0.0'; cases.append(item)
        item=copy.deepcopy(self.item); item['securityOverride']['advisories']=[]; cases.append(item)
        item=copy.deepcopy(self.item); item['securityOverride']['advisories']*=2; cases.append(item)
        item=copy.deepcopy(self.item); item['securityOverride']['advisories'][0]='https://github.com.evil.invalid/advisory'; cases.append(item)
        for change in ({'file':'../metadata.json'},{'url':'http://pypi.org/pypi/urllib3/2.8.0/json'},
                {'sha256':'a'*64},{'bytes':True},{'bytes':2*1024*1024+1}):
            item=copy.deepcopy(self.item); item['securityOverride']['metadata'].update(change); cases.append(item)
        item=copy.deepcopy(self.item); item['source']['sha256']='a'*64; cases.append(item)
        item=copy.deepcopy(self.item); item['declaredLicence']='invented licence'; cases.append(item)
        for index,item in enumerate(cases):
            with self.subTest(index=index),self.assertRaises(ValueError): validate_origin(item,2)
        with self.assertRaises(ValueError): validate_origin(self.item,1)
        with patch('downloader_security.digest',return_value='a'*64),self.assertRaisesRegex(ValueError,'snapshot'):
            validate_origin(self.item,2)

    def test_actual_upstream_versions_and_hashes_remain_required_except_the_explicit_override(self):
        baseline={item['name']:item.get('securityOverride',{}).get('baselineVersion',item['version']) for item in self.lock['dependencies']}
        hashes={(item['name'],item['version']):{item['wheel']['sha256']} for item in self.lock['dependencies']}
        with patch('downloader_security.upstream_pins',return_value=(baseline,hashes)):
            verify_source_pins(self.lock,Path('synthetic.zip'))
            bad=copy.deepcopy(self.lock); next(item for item in bad['dependencies'] if item['name']=='urllib3')['securityOverride']['baselineVersion']='2.6.0'
            with self.assertRaisesRegex(ValueError,'baseline'): verify_source_pins(bad,Path('synthetic.zip'))
            bad=copy.deepcopy(self.lock); bad['dependencies'][0]['wheel']['sha256']='a'*64
            with self.assertRaisesRegex(ValueError,'original upstream'): verify_source_pins(bad,Path('synthetic.zip'))
        with patch('downloader_security.upstream_pins',return_value=({},{})),self.assertRaisesRegex(ValueError,'set changed'):
            verify_source_pins(self.lock,Path('synthetic.zip'))

    def test_old_schema_still_accepts_an_original_upstream_pin_but_not_a_hidden_patch(self):
        legacy=copy.deepcopy(self.lock); legacy['schema']=1
        certifi=next(item for item in legacy['dependencies'] if item['name']=='certifi')
        certifi.pop('securityOverride');certifi['upstreamWheelHashVerified']=True;certifi['version']='2026.7.22'
        certifi['wheel']={'file':'certifi-2026.7.22-py3-none-any.whl',
            'url':'https://files.pythonhosted.org/packages/0b/a7/71ac2cff56fec219ed242bb11b8efb69fcc4bec75db06fb7bfe35de520e6/certifi-2026.7.22-py3-none-any.whl',
            'sha256':'62f22742b58a1a33014a2b6b706588a8d7e2a88ae7bd1a6ebe8c992928483775'}
        certifi['source']={'file':'certifi-2026.7.22.tar.gz',
            'url':'https://files.pythonhosted.org/packages/a3/c2/24167ea9858356b47a87a50d39908bfdb72ceeefe0041586e704e5376b3a/certifi-2026.7.22.tar.gz',
            'sha256':'741e2c3b351ddf169a738da9f2c048608ff7f2c5cc02f1ebc6b118bb090d5d55'}
        item=next(item for item in legacy['dependencies'] if item['name']=='urllib3')
        item.pop('securityOverride'); item['upstreamWheelHashVerified']=True
        item['version']='2.7.0'
        item['wheel']={'file':'urllib3-2.7.0-py3-none-any.whl',
            'url':'https://files.pythonhosted.org/packages/7f/3e/5db95bcf282c52709639744ca2a8b149baccf648e39c8cc87553df9eae0c/urllib3-2.7.0-py3-none-any.whl',
            'sha256':'9fb4c81ebbb1ce9531cce37674bbc6f1360472bc18ca9a553ede278ef7276897'}
        item['source']={'file':'urllib3-2.7.0.tar.gz',
            'url':'https://files.pythonhosted.org/packages/53/0c/06f8b233b8fd13b9e5ee11424ef85419ba0d8ba0b3138bf360be2ff56953/urllib3-2.7.0.tar.gz',
            'sha256':'231e0ec3b63ceb14667c67be60f2f2c40a518cb38b03af60abc813da26505f4c'}
        validate_lock(legacy)
        with self.assertRaises(ValueError): validate_lock({**self.lock,'schema':1})

    def test_runtime_must_report_exact_patched_version_not_an_old_or_prefixed_variant(self):
        verify_runtime_overrides(self.lock,{'metadata':['Optional libraries: certifi-2026.10.19, requests-2.34.2, urllib3-2.8.0']})
        for text in ('urllib3-2.7.0','urllib3-2.8.00','urllib3-2.8.0-evil','noturllib3-2.8.0',''):
            with self.subTest(text=text),self.assertRaises(ValueError): verify_runtime_overrides(self.lock,{'metadata':[text]})
