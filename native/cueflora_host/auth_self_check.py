"""Explicit local synthetic-key self-test. Never signs in or invokes a model."""
import json
from pathlib import Path
import tempfile
import time
import jwt
import httpx
from cryptography.hazmat.primitives.asymmetric import rsa
from .account_store import AccountStore
from .chatgpt_auth import ISSUER,validate_id_token


def check():
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    jwk=json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()));jwk.update(kid='cueflora-self-check',alg='RS256',use='sig')
    def handler(request):
        if 'configuration' in request.url.path:return httpx.Response(200,json={'issuer':ISSUER,'jwks_uri':ISSUER+'/self-check-jwks','revocation_endpoint':ISSUER+'/self-check-revoke'})
        return httpx.Response(200,json={'keys':[jwk]})
    token=jwt.encode({'iss':ISSUER,'aud':'oaiapp_synthetic_self_check','sub':'synthetic-subject','nonce':'synthetic-nonce','iat':int(time.time()),'exp':int(time.time())+60},key,algorithm='RS256',headers={'kid':'cueflora-self-check'})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        claims=validate_id_token(token,'oaiapp_synthetic_self_check','synthetic-nonce',client)
        if claims['sub']!='synthetic-subject':raise RuntimeError('Synthetic JWT check failed')
    with tempfile.TemporaryDirectory(prefix='CueFlora auth self-check Ω ') as folder:
        store=AccountStore(Path(folder));ref='12345678-1234-1234-1234-123456789abc'
        with store.transaction():
            data=store.read();data['accounts'][ref]={'label':'Synthetic account','access_token':'synthetic-access-only','refresh_token':'synthetic-refresh-only','id_token':token};store.write(data)
            if store.read()['accounts'][ref]['refresh_token']!='synthetic-refresh-only':raise RuntimeError('Synthetic DPAPI check failed')
        encoded=(Path(folder)/'accounts.dpapi.json').read_text()
        if any(value in encoded for value in ('synthetic-access-only','synthetic-refresh-only',token)):raise RuntimeError('Synthetic protected-store privacy check failed')
    return {'passed':True,'jwtSignatureValidation':True,'userScopedDpapi':True,'tokensRedacted':True,'genuineLogin':False,'network':'mocked','inference':False}
