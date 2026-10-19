"""Official OSS OAuth/PKCE; no cookies, borrowed clients or embedded secrets."""
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import re
import secrets
import time
from urllib.parse import parse_qs, urlencode, urlsplit
import uuid
import webbrowser
import httpx
from .account_store import AccountStore

ISSUER = 'https://auth.openai.com'
RESOURCE = 'https://api.openai.com/v1'
AUTHORIZE = ISSUER + '/api/accounts/authorize'
TOKEN = ISSUER + '/api/accounts/oauth/token'
SCOPES = 'openid profile email offline_access resource.invoke chatgpt.tokens.use.direct'


def json_request(client, method, url, **kwargs):
    with client.stream(method, url, **kwargs) as response:
        if response.status_code != 200: raise RuntimeError('ChatGPT authentication request failed. Reconnect or retry; no API fallback is used.')
        raw = bytearray()
        for chunk in response.iter_bytes():
            raw.extend(chunk)
            if len(raw) > 4 * 1024 * 1024: raise RuntimeError('Invalid ChatGPT metadata response')
        return json.loads(raw)


def discovery(client):
    data = json_request(client, 'GET', ISSUER+'/.well-known/openid-configuration')
    if data.get('issuer') != ISSUER: raise ValueError('Invalid OpenAI issuer')
    for key in ('jwks_uri','revocation_endpoint'):
        url = urlsplit(data.get(key,''))
        if url.scheme != 'https' or url.netloc != 'auth.openai.com' or not url.path.startswith('/') or url.query or url.fragment:
            raise ValueError('Invalid OpenAI discovery endpoint')
    return data


def validate_id_token(token, client_id, nonce, client, expected_subject=None):
    import jwt  # PyJWT[crypto], exact build inputs are hash-locked.
    if not isinstance(token,str) or len(token) > 32768: raise ValueError('Invalid ID token')
    header = jwt.get_unverified_header(token)
    if header.get('alg') != 'RS256' or not isinstance(header.get('kid'),str): raise ValueError('Invalid signing algorithm')
    metadata = discovery(client)
    keys = json_request(client,'GET',metadata['jwks_uri']).get('keys',[])
    matches = [key for key in keys if key.get('kid') == header['kid'] and key.get('kty') == 'RSA' and key.get('use','sig') == 'sig' and key.get('alg','RS256') == 'RS256']
    if len(matches) != 1: raise ValueError('Invalid signing key')
    key = jwt.PyJWK.from_dict(matches[0], algorithm='RS256').key
    claims = jwt.decode(token,key,algorithms=['RS256'],audience=client_id,issuer=ISSUER,
                        options={'require':['exp','iat','iss','aud','sub'] + (['nonce'] if nonce is not None else [])})
    if not isinstance(claims.get('sub'),str) or not claims['sub']: raise ValueError('Missing subject')
    if ('azp' in claims or isinstance(claims.get('aud'),list) and len(claims['aud'])>1) and claims.get('azp')!=client_id:raise ValueError('Invalid authorised party')
    if nonce is not None and not secrets.compare_digest(str(claims.get('nonce','')),nonce): raise ValueError('Invalid nonce')
    if expected_subject is not None and claims['sub'] != expected_subject: raise ValueError('Account mismatch')
    return claims


def token_record(payload, client_id, client, nonce=None, previous=None):
    previous = previous or {}
    scopes = payload.get('scope')
    scopes = scopes.split() if isinstance(scopes,str) else previous.get('scopes',[])
    if not {'chatgpt.tokens.use.direct','resource.invoke','offline_access'}.issubset(scopes): raise ValueError('ChatGPT plan permission not granted')
    if str(payload.get('token_type','')).lower() != 'bearer': raise ValueError('Invalid token type')
    for field in ('access_token','refresh_token'):
        value = payload.get(field, previous.get(field))
        if not isinstance(value,str) or not value or len(value)>16384: raise ValueError('Invalid credential response')
    expires = payload.get('expires_in')
    if isinstance(expires,bool) or not isinstance(expires,(int,float)) or not 1 <= expires <= 172800: raise ValueError('Invalid token expiry')
    id_token = payload.get('id_token')
    if id_token is not None:
        claims = validate_id_token(id_token,client_id,nonce,client,previous.get('subject'))
        if 'at_hash' in claims:
            expected=base64.urlsafe_b64encode(hashlib.sha256(payload['access_token'].encode()).digest()[:16]).rstrip(b'=').decode()
            if not isinstance(claims['at_hash'],str) or not secrets.compare_digest(claims['at_hash'],expected):raise ValueError('Invalid access-token binding')
        subject = claims['sub']
    elif nonce is not None: raise ValueError('Missing ID token')
    else: subject = previous.get('subject')
    return {**previous,'client_id':client_id,'subject':subject,'id_token':id_token or previous.get('id_token'),
            'access_token':payload['access_token'],'refresh_token':payload.get('refresh_token',previous.get('refresh_token')),
            'scopes':scopes,'expiresAt':time.time()+expires}


def callback_values(path, expected_state, issued=None):
    parsed = urlsplit(path)
    if parsed.path != '/auth/callback' or len(path)>16384: raise ValueError('Invalid callback path')
    query = parse_qs(parsed.query,keep_blank_values=True,max_num_fields=12)
    if any(len(values)!=1 for values in query.values()): raise ValueError('Ambiguous callback')
    state = query.get('state',[''])[0]
    if not secrets.compare_digest(state, expected_state): raise ValueError('Invalid callback state')
    if 'error' in query: raise ValueError('ChatGPT sign-in was declined')
    client_id = query.get('client_id',[issued or ''])[0]
    if not re.fullmatch(r'[A-Za-z0-9_-]{8,200}',client_id) or client_id == 'dynamic_agent_client' or (issued and client_id != issued): raise ValueError('Invalid issued client identity')
    code = query.get('code',[''])[0]
    if not code or len(code)>8192: raise ValueError('Missing authorization code')
    return code, client_id


def login(cancel, progress, account_ref=None, store=None, opener=webbrowser.open, lifetime=600):
    store = store or AccountStore()
    with store.transaction():
        data = store.read(); store.write(data)  # Persist the host ID before authorization.
        previous = data['accounts'].get(account_ref) if account_ref else None
        if account_ref and not previous: raise ValueError('Unknown account reference')
    state, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(3))
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    result = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass  # Callback URLs and credentials must never be logged.
        def do_GET(self):
            expected_host = '127.0.0.1:'+str(server.server_port)
            if self.headers.get('Host') != expected_host or urlsplit(self.path).path != '/auth/callback':
                self.send_error(404); return
            try:
                result.append(callback_values(self.path,state,previous.get('client_id') if previous else None))
                status, text = 200, b'CueFlora sign-in received. You can close this page.'
            except ValueError:
                result.append(None); status, text = 400, b'CueFlora sign-in could not be validated. Start again in settings.'
            self.send_response(status); self.send_header('Content-Type','text/plain; charset=utf-8')
            self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(text))); self.end_headers(); self.wfile.write(text)
    class Listener(HTTPServer):
        def get_request(self):
            connection,address = super().get_request(); connection.settimeout(1); return connection,address
    with Listener(('127.0.0.1',0),Handler) as server:
        server.timeout = 0.2
        redirect = f'http://127.0.0.1:{server.server_port}/auth/callback'
        parameters = {'client_id':previous['client_id'] if previous else 'dynamic_agent_client','ext_agent_host_id':data['hostId'],
            'response_type':'code','redirect_uri':redirect,'scope':SCOPES,'resource':RESOURCE,'state':state,'nonce':nonce,
            'code_challenge_method':'S256','code_challenge':challenge}
        if not previous: parameters['agent_name_hint']='CueFlora'
        elif previous.get('id_token'): parameters['id_token_hint']=previous['id_token']
        progress('waiting-for-user')
        if cancel.is_set():raise RuntimeError('ChatGPT sign-in cancelled')
        if not opener(AUTHORIZE+'?'+urlencode(parameters)): raise RuntimeError('Could not open ChatGPT sign-in. Retry in settings.')
        deadline = time.monotonic()+min(lifetime,600)
        while not result:
            if cancel.is_set(): raise RuntimeError('ChatGPT sign-in cancelled')
            if time.monotonic() >= deadline: raise RuntimeError('ChatGPT sign-in expired after ten minutes')
            server.handle_request()
    if cancel.is_set(): raise RuntimeError('ChatGPT sign-in cancelled')
    if not result[0]: raise RuntimeError('ChatGPT callback failed validation. Start sign-in again.')
    code, client_id = result[0]
    progress('validating-account')
    with httpx.Client(timeout=8,follow_redirects=False) as client:
        payload = json_request(client,'POST',TOKEN,data={'grant_type':'authorization_code','client_id':client_id,'code':code,
            'code_verifier':verifier,'redirect_uri':redirect,'resource':RESOURCE})
        record = token_record(payload,client_id,client,nonce,previous)
    if cancel.is_set(): raise RuntimeError('ChatGPT sign-in cancelled')
    with store.transaction():
        data = store.read()
        ref = account_ref or next((ref for ref,item in data['accounts'].items() if item['client_id']==client_id and item['subject']==record['subject']),None) or str(uuid.uuid4())
        record['label'] = data['accounts'].get(ref,{}).get('label','ChatGPT account '+str(len(data['accounts'])+1))
        data['accounts'][ref]=record; store.write(data)
    return {'accountRef':ref,'label':record['label'],'connected':True,'planEnabled':True,'needsUsageNotice':not record.get('usageAcknowledged',False)}


def access_token(account_ref, store=None):
    store = store or AccountStore()
    # OS + thread lock spans refresh and durable rotation, across all host processes.
    with store.transaction():
        data = store.read(); account = data['accounts'].get(account_ref)
        if not account or not account.get('access_token'): raise RuntimeError('ChatGPT account is disconnected. Sign in again; no API fallback is used.')
        if account.get('expiresAt',0) < time.time()+60:
            with httpx.Client(timeout=8,follow_redirects=False) as client:
                payload = json_request(client,'POST',TOKEN,data={'grant_type':'refresh_token','client_id':account['client_id'],
                    'refresh_token':account['refresh_token'],'resource':RESOURCE})
                account = token_record(payload,account['client_id'],client,previous=account)
            data['accounts'][account_ref]=account; store.write(data)
        return account['access_token']


def models(account_ref, store=None):
    store=store or AccountStore()
    token = access_token(account_ref,store)
    with httpx.Client(timeout=8,follow_redirects=False) as client:
        data = json_request(client,'GET',RESOURCE+'/models',headers={'Authorization':'Bearer '+token})
    if not isinstance(data.get('models'),list): raise ValueError('Invalid ChatGPT model list')
    result=[]
    for item in data['models']:
        if not isinstance(item,dict) or item.get('visibility') != 'list': continue
        slug,label=item.get('slug'),item.get('display_name')
        if not isinstance(slug,str) or not re.fullmatch(r'[\w.:/\-]{1,200}',slug,re.ASCII) or not isinstance(label,str) or not 0<len(label)<=200: raise ValueError('Invalid model')
        if slug not in [item['id'] for item in result]: result.append({'id':slug,'label':label})
    with store.transaction():
        saved=store.read();account=saved['accounts'].get(account_ref)
        if not account or not account.get('access_token'):raise ValueError('Account disconnected during discovery')
        account['eligibleModels']=[item['id'] for item in result[:500]];account['modelsCheckedAt']=time.time();store.write(saved)
    return {'models':result[:500],'partial':len(result)>500}


def cached_models(account_ref,store=None):
    store=store or AccountStore()
    with store.transaction():
        account=store.read()['accounts'].get(account_ref)
        if not account or not account.get('access_token') or time.time()-account.get('modelsCheckedAt',0)>900:raise ValueError('Load eligible models before saving this choice')
        return {'models':[{'id':model,'label':model} for model in account.get('eligibleModels',[])],'partial':False}


def disconnect(account_ref, store=None):
    store = store or AccountStore(); confirmed=False
    with store.transaction():
        data=store.read(); account=data['accounts'].get(account_ref)
        if not account: raise ValueError('Unknown ChatGPT account')
        try:
            if account.get('refresh_token'):
                with httpx.Client(timeout=4,follow_redirects=False) as client:
                    endpoint=discovery(client)['revocation_endpoint']
                    for attempt in range(2):
                        try:
                            response=client.post(endpoint,data={'token':account['refresh_token'],'token_type_hint':'refresh_token','client_id':account['client_id']})
                            confirmed=response.status_code==200
                            if confirmed or response.status_code<500: break
                        except httpx.HTTPError: pass
                        if attempt==0: time.sleep(0.2)
        except Exception: pass
        data['accounts'][account_ref]={key:account[key] for key in ('client_id','subject','label','usageAcknowledged') if key in account}
        store.write(data)
    return {'disconnected':True,'revocationConfirmed':confirmed}


def acknowledge_usage(account_ref,store=None):
    store=store or AccountStore()
    with store.transaction():
        data=store.read()
        if account_ref not in data['accounts']:raise ValueError('Unknown account')
        data['accounts'][account_ref]['usageAcknowledged']=True;store.write(data)
    return {'acknowledged':True}
