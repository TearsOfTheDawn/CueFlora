import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from .account_store import AccountStore
from .chatgpt_auth import callback_values, validate_id_token, access_token, disconnect, login, ISSUER
from .chatgpt_translate import consume_events, events, translate
from .translate import TranslationError


class ChatGPTTests(unittest.TestCase):
    def test_ninth_account_write_preserves_the_readable_existing_store(self):
        import uuid
        with tempfile.TemporaryDirectory() as directory:
            store=AccountStore(directory,lambda data,entropy,decrypt=False:data)
            data={'schema':1,'hostId':'urn:uuid:'+str(uuid.uuid4()),'accounts':{str(uuid.uuid4()):{'label':'synthetic'} for _ in range(8)}}
            store.write(data);before=(Path(directory)/'accounts.dpapi.json').read_bytes()
            data['accounts'][str(uuid.uuid4())]={'label':'ninth'}
            with self.assertRaisesRegex(RuntimeError,'eight'):store.write(data)
            self.assertEqual((Path(directory)/'accounts.dpapi.json').read_bytes(),before)
            self.assertEqual(len(store.read()['accounts']),8)

    @unittest.skipUnless(os.name=='nt','Real DPAPI requires Windows')
    def test_full_synthetic_loopback_pkce_exchange_and_listener_shutdown(self):
        import base64,hashlib,socket
        from urllib.parse import parse_qs,urlsplit,urlencode
        import urllib.request
        key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        jwk=json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()));jwk.update(kid='loopback',alg='RS256',use='sig')
        pending={};callbacks=[];calls=[]
        def opener(url):
            query=parse_qs(urlsplit(url).query);pending.update({name:values[0] for name,values in query.items()})
            self.assertEqual(pending['client_id'],'dynamic_agent_client');self.assertEqual(pending['agent_name_hint'],'CueFlora')
            self.assertEqual(pending['code_challenge_method'],'S256')
            def callback():
                with urllib.request.urlopen(pending['redirect_uri']+'?'+urlencode({'code':'synthetic-code','state':pending['state'],'client_id':'oaiapp_loopback'}),timeout=3) as response:callbacks.append(response.status)
            thread=threading.Thread(target=callback);thread.start();pending['thread']=thread;return True
        def handler(request):
            calls.append(request)
            if request.url.path.endswith('/oauth/token'):
                body={name:values[0] for name,values in parse_qs(request.content.decode()).items()}
                self.assertEqual(body['redirect_uri'],pending['redirect_uri']);self.assertNotIn('client_secret',body)
                self.assertEqual(base64.urlsafe_b64encode(hashlib.sha256(body['code_verifier'].encode()).digest()).rstrip(b'=').decode(),pending['code_challenge'])
                claims={'iss':ISSUER,'aud':'oaiapp_loopback','sub':'synthetic-subject','nonce':pending['nonce'],'iat':int(time.time()),'exp':int(time.time())+300}
                return httpx.Response(200,json={'access_token':'synthetic-loopback-access','refresh_token':'synthetic-loopback-refresh','id_token':jwt.encode(claims,key,algorithm='RS256',headers={'kid':'loopback'}),'scope':'openid offline_access resource.invoke chatgpt.tokens.use.direct','token_type':'Bearer','expires_in':3600})
            if 'configuration' in request.url.path:return httpx.Response(200,json={'issuer':ISSUER,'jwks_uri':ISSUER+'/jwks','revocation_endpoint':ISSUER+'/revoke'})
            return httpx.Response(200,json={'keys':[jwk]})
        with tempfile.TemporaryDirectory(prefix='CueFlora callback Ω ') as folder:
            store=AccountStore(folder);client=httpx.Client(transport=httpx.MockTransport(handler))
            with patch('cueflora_host.chatgpt_auth.httpx.Client',return_value=client):
                result=login(threading.Event(),lambda stage:None,store=store,opener=opener,lifetime=5)
            pending['thread'].join(timeout=3);self.assertEqual(callbacks,[200]);self.assertTrue(result['connected'])
            self.assertNotIn('synthetic-loopback-access',json.dumps(result));self.assertTrue(result['needsUsageNotice'])
            self.assertEqual(len([call for call in calls if call.method=='POST']),1)
            with socket.socket() as connection:self.assertNotEqual(connection.connect_ex(('127.0.0.1',urlsplit(pending['redirect_uri']).port)),0)
            self.assertNotIn('synthetic-loopback-refresh',(Path(folder)/'accounts.dpapi.json').read_text())

    def test_callback_state_duplicates_issued_identity_and_denial(self):
        self.assertEqual(callback_values('/auth/callback?state=good&code=code&client_id=oaiapp_synthetic','good'),('code','oaiapp_synthetic'))
        for value in ['state=wrong&code=code&client_id=oaiapp_synthetic', 'state=good&state=good&code=code',
                      'state=good&error=access_denied', 'state=good&code=code&client_id=dynamic_agent_client',
                      'state=good&code=code&client_id=oaiapp_other']:
            with self.subTest(value=value),self.assertRaises(ValueError): callback_values('/auth/callback?'+value,'good','oaiapp_expected')

    def test_jwt_signature_nonce_issuer_audience_scope_boundary(self):
        key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        jwk=json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()));jwk.update(kid='synthetic',alg='RS256',use='sig')
        def handler(request):
            return httpx.Response(200,json={'issuer':ISSUER,'jwks_uri':ISSUER+'/jwks','revocation_endpoint':ISSUER+'/revoke'} if 'configuration' in request.url.path else {'keys':[jwk]})
        client=httpx.Client(transport=httpx.MockTransport(handler))
        claims={'iss':ISSUER,'aud':'oaiapp_synthetic','sub':'subject','nonce':'nonce','iat':int(time.time()),'exp':int(time.time())+300}
        token=jwt.encode(claims,key,algorithm='RS256',headers={'kid':'synthetic'})
        self.assertEqual(validate_id_token(token,'oaiapp_synthetic','nonce',client)['sub'],'subject')
        for args in [('wrong','nonce',None),('oaiapp_synthetic','wrong',None),('oaiapp_synthetic','nonce','other')]:
            with self.assertRaises(Exception):validate_id_token(token,args[0],args[1],client,args[2])
        bad=jwt.encode({**claims,'exp':1},key,algorithm='RS256',headers={'kid':'synthetic'})
        with self.assertRaises(Exception):validate_id_token(bad,'oaiapp_synthetic','nonce',client)
        wrong_key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        bad=jwt.encode(claims,wrong_key,algorithm='RS256',headers={'kid':'synthetic'})
        with self.assertRaises(Exception):validate_id_token(bad,'oaiapp_synthetic','nonce',client)
        from .chatgpt_auth import token_record
        with self.assertRaisesRegex(ValueError,'permission'):
            token_record({'scope':'openid profile','token_type':'Bearer'},'oaiapp_synthetic',client)

    @unittest.skipUnless(os.name=='nt','Real DPAPI requires Windows')
    def test_real_protected_store_refresh_serialization_and_revocation_failure(self):
        with tempfile.TemporaryDirectory(prefix='CueFlora auth Ω ') as folder:
            store=AccountStore(Path(folder));ref='12345678-1234-1234-1234-123456789abc'
            with store.transaction():
                data=store.read();data['accounts'][ref]={'label':'ChatGPT account 1','subject':'synthetic','client_id':'oaiapp_synthetic',
                    'access_token':'synthetic-old-access','refresh_token':'synthetic-refresh','id_token':'synthetic-id-token',
                    'expiresAt':0,'scopes':['chatgpt.tokens.use.direct','resource.invoke','offline_access']};store.write(data)
            content=(Path(folder)/'accounts.dpapi.json').read_text()
            for value in ('synthetic-old-access','synthetic-refresh','synthetic-id-token'):self.assertNotIn(value,content)
            calls=[]
            def handler(request):
                calls.append(request)
                return httpx.Response(200,json={'access_token':'synthetic-new-access','refresh_token':'synthetic-rotated','token_type':'Bearer','expires_in':3600})
            client=httpx.Client(transport=httpx.MockTransport(handler))
            values=[]
            with patch('cueflora_host.chatgpt_auth.httpx.Client',return_value=client):
                threads=[threading.Thread(target=lambda:values.append(access_token(ref,store))) for _ in range(2)]
                for thread in threads:thread.start()
                for thread in threads:thread.join(timeout=5)
            self.assertEqual(values,['synthetic-new-access']*2);self.assertEqual(len(calls),1)
            self.assertNotIn(b'scope=',calls[0].content)
            with patch('cueflora_host.chatgpt_auth.discovery',side_effect=RuntimeError('synthetic secret')):
                result=disconnect(ref,store)
            self.assertFalse(result['revocationConfirmed'])
            with store.transaction():account=store.read()['accounts'][ref]
            self.assertEqual(set(account),{'client_id','subject','label'})

    def test_login_timeout_cancellation_no_browser_and_no_network(self):
        def crypt(data,entropy,decrypt=False):return data  # Synthetic store only; not production protection.
        for cancelled in (False,True):
            with tempfile.TemporaryDirectory() as folder:
                cancel=threading.Event()
                if cancelled:cancel.set()
                with patch('cueflora_host.chatgpt_auth.httpx.Client') as network:
                    with self.assertRaises(RuntimeError):login(cancel,lambda stage:None,store=AccountStore(folder,crypt),opener=lambda url:True,lifetime=0)
                network.assert_not_called()

    def test_completed_stream_alignment_and_incomplete_stream_errors(self):
        text=json.dumps({'translations':[{'id':1,'text':'two'},{'id':0,'text':'one'}]})
        delta={'type':'response.output_text.delta','delta':text}
        complete={'type':'response.completed','response':{'status':'completed'}}
        self.assertEqual(consume_events([delta,complete],2),['one','two'])
        for stream in ([delta],[delta,{'type':'response.failed','response':{'error':{'code':'subscription_sharing_usage_limit_exceeded'}}}],
                       [delta,{'type':'response.incomplete'}],[delta,{'type':'response.completed','response':{'status':'incomplete'}}]):
            with self.assertRaises(TranslationError):consume_events(stream,2)
        invalid={'type':'response.output_text.delta','delta':'{"translations":[{"id":0,"text":"one"},{"id":0,"text":"two"}]}'}
        with self.assertRaises(TranslationError):consume_events([invalid,complete],2)
        raw=('data: '+json.dumps(delta)+'\r\n\r\ndata: '+json.dumps(complete)+'\n\n').encode()
        self.assertEqual(consume_events(events([raw[:13],raw[13:]]),2),['one','two'])

    def test_responses_contract_one_post_no_unsupported_fields_or_paid_fallback(self):
        calls=[]
        payload=[{'type':'response.output_text.delta','delta':'{"translations":[{"id":0,"text":"Hello"}]}'},
                 {'type':'response.completed','response':{'status':'completed'}}]
        def handler(request):
            calls.append(request)
            return httpx.Response(200,headers={'content-type':'text/event-stream'},content=''.join('data: '+json.dumps(item)+'\n\n' for item in payload))
        client=httpx.Client(transport=httpx.MockTransport(handler))
        with patch('cueflora_host.chatgpt_translate.access_token',return_value='synthetic-bearer'),patch('cueflora_host.chatgpt_translate.httpx.Client',return_value=client):
            result=translate([{'text':'你好'}],'Translate','opaque-ref','explicit-model')
        self.assertEqual(result['requestCount'],1);self.assertEqual(len(calls),1)
        self.assertEqual(str(calls[0].url),'https://api.openai.com/v1/responses')
        body=json.loads(calls[0].content);self.assertFalse(body['store']);self.assertTrue(body['stream'])
        for field in ('temperature','max_output_tokens','max_tokens','top_p','metadata','previous_response_id'):self.assertNotIn(field,body)
        self.assertEqual(body['text']['format']['type'],'json_schema')
        self.assertNotIn('synthetic-bearer',json.dumps(result))


if __name__=='__main__':unittest.main()
