import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import httpx
from .updates import Updates,validate_manifest,download_bytes,REPOSITORY,CHROME_ID,API


def manifest(payload=b'x'*(1024*1024)):
    return {'schema':1,'product':'cueflora','repository':REPOSITORY,'version':'0.2.1','platform':'Windows','architecture':'x64','chromeId':CHROME_ID,
        'minimumUpdaterVersion':'0.2.0','runtimeInventorySha256':'1'*64,'extensionInventorySha256':'2'*64,'sourceInventorySha256':'3'*64,
        'setup':{'name':'CueFlora-0.2.1-Setup.exe','size':len(payload),'sha256':hashlib.sha256(payload).hexdigest(),
                 'url':'https://github.com/'+REPOSITORY+'/releases/download/v0.2.1/CueFlora-0.2.1-Setup.exe'}}


class UpdatesTests(unittest.TestCase):
    def test_json_accept_regression_and_already_current_performs_no_download_or_write(self):
        requests=[]
        def handler(request):
            requests.append(request)
            if request.headers.get('Accept')!='application/vnd.github+json':
                return httpx.Response(415,json={'message':'Unsupported Accept header'})
            return httpx.Response(200,json=[{'draft':False,'prerelease':False,'published_at':'2026-10-19T00:00:00Z','tag_name':'v0.2.1'}])
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'unused'
            with patch('cueflora_host.updates.httpx.Client',return_value=httpx.Client(transport=httpx.MockTransport(handler))):
                result=Updates(root,current='0.2.1').check()
            self.assertEqual(result,{'available':False,'currentVersion':'0.2.1'})
            self.assertEqual(len(requests),1);self.assertFalse(root.exists())
    def test_metadata_http_failure_retains_safe_status_not_provider_body(self):
        from .updates import metadata
        from .failures import OperationFailure
        client=httpx.Client(transport=httpx.MockTransport(lambda _:httpx.Response(415,text='synthetic-secret https://private.invalid')))
        with self.assertRaises(OperationFailure) as caught:metadata(client,API+'/releases?per_page=20')
        self.assertEqual(caught.exception.detail,{'stage':'update-check','code':'provider-request','httpStatus':415})
        self.assertNotIn('synthetic-secret',str(caught.exception))
    def test_manifest_rejects_identity_platform_version_and_arbitrary_assets(self):
        data=manifest();validate_manifest(data)
        for changes in [{'repository':'foreign/repository'},{'chromeId':'a'*32},{'version':'0.2.0'},{'version':'0.2.1-beta'},{'platform':'Linux'},
                        {'minimumUpdaterVersion':'99.0.0'},{'extensionInventorySha256':'bad'},{'setup':{**data['setup'],'url':'https://foreign.invalid/setup.exe'}},
                        {'setup':{**data['setup'],'name':'anything.exe'}},{'setup':{**data['setup'],'size':True}},{'unknown':'field'}]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):validate_manifest({**data,**changes})
    @patch('cueflora_host.updates.verify_update_payload')
    def test_stable_selection_download_hash_cancellation_and_no_arbitrary_launch(self,verify_payload):
        payload=b'x'*(1024*1024);data=manifest(payload);requests=[]
        manifest_url='https://github.com/'+REPOSITORY+'/releases/download/v0.2.1/CueFlora-0.2.1-update.json'
        release={'draft':False,'prerelease':False,'published_at':'2026-10-19T00:00:00Z','tag_name':'v0.2.1',
            'assets':[{'name':'CueFlora-0.2.1-update.json','browser_download_url':manifest_url},
                      {'name':data['setup']['name'],'browser_download_url':data['setup']['url'],'size':len(payload)}]}
        def handler(request):
            requests.append(request)
            self.assertNotIn('Authorization',request.headers)
            if str(request.url)==API+'/releases?per_page=20':return httpx.Response(200,json=[release,{**release,'tag_name':'v9.0.0','prerelease':True}])
            if str(request.url)==manifest_url:return httpx.Response(200,json=data)
            if str(request.url)==data['setup']['url']:return httpx.Response(302,headers={'location':'https://release-assets.githubusercontent.com/synthetic?sig=temporary'})
            return httpx.Response(200,content=payload)
        with tempfile.TemporaryDirectory(prefix='CueFlora updates Ω ') as folder:
            updater=Updates(Path(folder).resolve(),current='0.2.0');cancel=threading.Event();client=httpx.Client(transport=httpx.MockTransport(handler))
            with patch('cueflora_host.updates.httpx.Client',return_value=client):selected=updater.check()
            ref=selected['selectionRef'];self.assertEqual(selected['version'],'0.2.1')
            # Recreate each client because production closes each bounded HTTP session.
            with patch('cueflora_host.updates.httpx.Client',return_value=httpx.Client(transport=httpx.MockTransport(handler))):
                ready=updater.download(ref,cancel,lambda value:None)
            self.assertTrue(ready['ready'])
            verify_payload.assert_called()
            with patch('cueflora_host.updates.subprocess.Popen') as launch:
                self.assertTrue(updater.launch(ref)['launched']);self.assertEqual(launch.call_args.args[0],[str(updater.verify(ref))])
            target=updater.verify(ref);target.write_bytes(b'corrupt')
            with patch('cueflora_host.updates.subprocess.Popen') as launch:
                with self.assertRaises(ValueError):updater.launch(ref)
                launch.assert_not_called()
            cancel.set()
            with patch('cueflora_host.updates.httpx.Client',return_value=httpx.Client(transport=httpx.MockTransport(handler))):
                with self.assertRaises(RuntimeError):updater.download(ref,cancel,lambda value:None)
            self.assertFalse(any(path.suffix=='.partial' for path in Path(folder).rglob('*')))
    def test_redirects_and_oversized_metadata_are_rejected_without_following_foreign_hosts(self):
        for destination in ('https://foreign.invalid/file','http://release-assets.githubusercontent.com/file','https://name:secret@github.com/file'):
            seen=[]
            def handler(request):seen.append(request);return httpx.Response(302,headers={'location':destination})
            client=httpx.Client(transport=httpx.MockTransport(handler))
            with self.assertRaises(ValueError):download_bytes(client,'https://github.com/'+REPOSITORY+'/releases/download/v0.2.1/file',100,allow_redirects=True)
            self.assertEqual(len(seen),1)
        client=httpx.Client(transport=httpx.MockTransport(lambda _:httpx.Response(200,content=b'x'*101)))
        with self.assertRaises(ValueError):download_bytes(client,API+'/releases?per_page=20',100)


if __name__=='__main__':unittest.main()
