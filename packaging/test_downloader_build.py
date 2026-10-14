import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from build_downloader import validate_lock,validate_capabilities,obtain,ROOT
from collect_curl_sources import validate as validate_curl,check_recipe


class DownloaderBuildTests(unittest.TestCase):
    def setUp(self):
        self.lock=json.loads((ROOT/'packaging/downloader-inputs.lock.json').read_text())

    def test_exact_upstream_lock_keeps_all_optional_features(self):
        self.assertEqual(len(validate_lock(self.lock)['dependencies']),13)
        for change in ({'ytDlpVersion':'latest'},{'pythonVersion':'3.10.11'},{'redistributionApproved':True},{'dependencies':[]}):
            with self.assertRaises(ValueError): validate_lock({**self.lock,**change})
        value=copy.deepcopy(self.lock); value['source']['file']='../source.zip'
        with self.assertRaises(ValueError): validate_lock(value)

    def test_malformed_wheels_sources_origins_and_duplicates_fail(self):
        for change in ({'file':'../input.whl'},{'url':'http://files.pythonhosted.org/input.whl'},
            {'url':'https://files.pythonhosted.org.evil.invalid/input.whl'},{'url':'https://files.pythonhosted.org:444/input.whl'},
            {'sha256':'bad'},{'file':'..'}):
            value=copy.deepcopy(self.lock); value['dependencies'][0]['wheel'].update(change)
            with self.assertRaises(ValueError): validate_lock(value)
        value=copy.deepcopy(self.lock); value['dependencies'][1]['wheel']=value['dependencies'][0]['wheel']
        with self.assertRaises(ValueError): validate_lock(value)
        value=copy.deepcopy(self.lock); value['dependencies'][0]['source']=None
        with self.assertRaises(ValueError): validate_lock(value)

    def test_offline_missing_input_never_downloads_or_substitutes(self):
        with tempfile.TemporaryDirectory() as folder,patch('build_downloader.download') as network:
            with self.assertRaisesRegex(ValueError,'Missing exact downloader input'): obtain(Path(folder))
            network.assert_not_called()

    def test_supported_runtime_same_extractors_and_optional_features_required(self):
        metadata=['Python 3.13.15 OpenSSL 3.5.7','JS runtimes: deno-2.9.7',
            'Optional libraries: '+', '.join(name+'-1.0' for name in ('Cryptodome','brotli','certifi','curl_cffi','mutagen','requests','urllib3','websockets','yt_dlp_ejs'))]
        previous={'extractors':['YouTube','Other']}; current={**previous,'metadata':metadata}
        validate_capabilities(previous,current)
        for change in ({'extractors':['YouTube']},{'metadata':metadata[:1]},{'metadata':[line.replace('Python 3.13.15','Python 3.10.11') for line in metadata]},
            {'metadata':[line.replace('mutagen-1.0','') for line in metadata]},{'metadata':metadata+['OpenSSL 1.1.1t']}):
            with self.assertRaises(ValueError): validate_capabilities(previous,{**current,**change})

    def test_curl_lock_requires_exact_origin_and_all_recipe_inputs(self):
        lock=json.loads((ROOT/'packaging/curl-native-inputs.lock.json').read_text())
        validate_curl(lock)
        for change in ({'redistributionApproved':True},{'dependencies':lock['dependencies'][:-1]},{'binary':{**lock['binary'],'member':'../other.dll'}}):
            with self.assertRaises(ValueError): validate_curl({**lock,**change})
        value=copy.deepcopy(lock); value['dependencies'][0]['url']='https://github.com.evil.invalid/source'
        with self.assertRaises(ValueError): validate_curl(value)

    def test_curl_recipe_hash_version_and_windows_idn_must_match(self):
        lock=json.loads((ROOT/'packaging/curl-native-inputs.lock.json').read_text())
        recipe='\n'.join('set('+item['recipeVariable']+'_'+('COMMIT' if item['recipeVariable']=='BORINGSSL' else 'VERSION')+' "'+item['version']+'")\nset('+item['recipeVariable']+'_URL_HASH "SHA256='+item['sha256']+'")' for item in lock['dependencies'])+'\n-DUSE_WIN32_IDN=ON -DUSE_LIBIDN2=OFF'
        check_recipe(lock,recipe)
        for value in (recipe.replace(lock['dependencies'][0]['sha256'],'a'*64),recipe.replace('1.63.0','latest'),recipe.replace('-DUSE_LIBIDN2=OFF','-DUSE_LIBIDN2=ON')):
            with self.assertRaises(ValueError): check_recipe(lock,value)
