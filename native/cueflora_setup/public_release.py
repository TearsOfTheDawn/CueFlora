"""Explicit public-package contract. Declarations are not legal/store approval."""
import re
import ipaddress
import base64
import hashlib
from urllib.parse import urlsplit

DEVELOPMENT_ID = 'klnnagigpdlgchlablabnafceoldfalm'
GATES = ('licences', 'downloadPolicy', 'nativeSecurity', 'cleanWindows', 'chromeRun')


def public_url(value):
    if not isinstance(value, str) or not value or len(value) > 2048 or any(c.isspace() for c in value) or '\\' in value:
        raise ValueError('Real public HTTPS locations are required')
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment or parsed.port not in (None, 443):
        raise ValueError('Invalid public HTTPS location')
    host = parsed.hostname.lower().rstrip('.')
    if host in ('localhost', '127.0.0.1', '::1') or host.endswith(('.invalid', '.localhost', '.local', '.test')):
        raise ValueError('Placeholder/local release location rejected')
    try: address = ipaddress.ip_address(host)
    except ValueError: address = None
    if address is not None and not address.is_global: raise ValueError('Nonpublic release address rejected')
    return value


def validate_spki(data):
    """Bounded canonical DER shape, no private key and no external crypto runtime."""
    if len(data)<64 or len(data)>16384: raise ValueError('Invalid public-key size')
    def tlv(raw,offset=0):
        if offset+2>len(raw): raise ValueError('Truncated DER')
        tag=raw[offset]; size=raw[offset+1]; start=offset+2
        if size&0x80:
            count=size&0x7f
            if count<1 or count>3 or start+count>len(raw) or raw[start]==0: raise ValueError('Invalid DER length')
            size=int.from_bytes(raw[start:start+count],'big'); start+=count
            if size<128: raise ValueError('Noncanonical DER length')
        end=start+size
        if end>len(raw): raise ValueError('Truncated DER body')
        return tag,raw[start:end],end
    tag,body,end=tlv(data)
    if tag!=0x30 or end!=len(data): raise ValueError('Public key must be a complete SPKI sequence')
    tag,algorithm,end=tlv(body)
    if tag!=0x30: raise ValueError('Invalid SPKI algorithm')
    oid,identifier,position=tlv(algorithm)
    if oid!=6 or not identifier: raise ValueError('Missing SPKI algorithm identifier')
    if position<len(algorithm):
        _,_,position=tlv(algorithm,position)
    if position!=len(algorithm): raise ValueError('Malformed SPKI algorithm parameters')
    tag,bits,end=tlv(body,end)
    if tag!=3 or end!=len(body) or len(bits)<32 or bits[0]!=0: raise ValueError('Invalid SPKI public bit string')


def validate_identity(value, require_binding=True):
    """Schema 2 constructs a public-identity candidate, never an approval."""
    from .manifests import validate_release
    if not isinstance(value, dict): raise ValueError('Public configuration must be an object')
    validate_release(value)
    allowed = {'schema','mode','product','owner','extensionIds','privacyUrl','downloadUrl','supportUrl',
        'runtimeInventorySha256','sourceInventorySha256','signing','chromePublicKey',
        'publicReleaseAuthorized','redistributionApproved','note','repositoryUrl'}
    if set(value) - allowed or value.get('schema') != 2 or value.get('mode') != 'public' or value.get('product') != 'cueflora' or set(value['extensionIds']) != {'chrome'}:
        raise ValueError('Schema 2 public Windows/Chrome identity required; no secrets or approvals')
    if value['extensionIds']['chrome'] == DEVELOPMENT_ID: raise ValueError('Development identity is not a public identity')
    for field in ('privacyUrl','downloadUrl','supportUrl'): public_url(value.get(field))
    if value.get('repositoryUrl') is not None:
        public_url(value['repositoryUrl'])
        if not re.fullmatch(r'https://github\.com/[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+',value['repositoryUrl']) or value['repositoryUrl'].endswith('.git'):
            raise ValueError('Canonical GitHub repository URL required')
    if value.get('signing') != 'unsigned' or value.get('publicReleaseAuthorized') is not False or value.get('redistributionApproved') is not False:
        raise ValueError('Candidate construction cannot grant release or redistribution approval')
    for field in ('runtimeInventorySha256','sourceInventorySha256'):
        checksum = value.get(field)
        if checksum is None and not require_binding: continue
        if not isinstance(checksum,str) or not re.fullmatch('[0-9a-f]{64}',checksum): raise ValueError('Exact source/runtime inventory binding required')
    key = value.get('chromePublicKey')
    if key is not None:
        try:
            decoded = base64.b64decode(key,validate=True)
            validate_spki(decoded)
            identity = ''.join(chr(97+int(c,16)) for c in hashlib.sha256(decoded).hexdigest()[:32])
        except (ValueError,TypeError): raise ValueError('Invalid Store public key') from None
        if identity != value['extensionIds']['chrome']: raise ValueError('Store public key and assigned identity disagree')
    return value


def validate_public(value, metadata=None, require_binding=True):
    if isinstance(value,dict) and value.get('schema') == 2:
        validate_identity(value,require_binding)
        if metadata is not None:
            if metadata.get('product') != 'cueflora' or metadata.get('platform') != 'Windows' or metadata.get('architecture','').lower() not in ('amd64','x86_64') or metadata.get('transportPolicy') != 'https-remote':
                raise ValueError('Public candidate requires Windows x64 HTTPS runtime')
            if metadata.get('sourceInventorySha256') != value['sourceInventorySha256'] or metadata.get('publicEvidence') is not None:
                raise ValueError('Candidate source binding mismatch or embedded approval declaration')
        return value
    from .manifests import validate_release
    validate_release(value)
    allowed = {'schema','mode','product','owner','extensionIds','privacyUrl','downloadUrl','supportUrl',
        'runtimeInventorySha256','sourceInventorySha256','signing','evidence','publicReleaseAuthorized','redistributionApproved','note','storeApproval'}
    if set(value)-allowed: raise ValueError('Unsupported public configuration fields; never include credentials')
    if value.get('schema') != 1 or value.get('mode') != 'public' or value.get('product') != 'cueflora' or value.get('extensionIds', {}).keys() != {'chrome'}:
        raise ValueError('Public Windows/Chrome configuration required')
    if value['extensionIds']['chrome'] == DEVELOPMENT_ID:
        raise ValueError('Development Chrome identity cannot be used for public installation')
    for name in ('privacyUrl', 'downloadUrl', 'supportUrl'): public_url(value.get(name))
    for name in ('runtimeInventorySha256', 'sourceInventorySha256'):
        if not re.fullmatch('[0-9a-f]{64}', str(value.get(name, ''))): raise ValueError('Public source/runtime binding required')
    if value.get('publicReleaseAuthorized') is not True or value.get('redistributionApproved') is not True or value.get('signing') != 'unsigned':
        raise ValueError('Explicit release/redistribution authorization and unsigned status required')
    evidence = value.get('evidence')
    if not isinstance(evidence, dict) or set(evidence) != set(GATES): raise ValueError('Public release evidence is incomplete')
    for item in evidence.values():
        if not isinstance(item, dict) or set(item) != {'status', 'reviewedBy', 'reportSha256'} or item.get('status') != 'passed' or not isinstance(item.get('reviewedBy'), str) or not item['reviewedBy'].strip() or len(item['reviewedBy']) > 200 or not re.fullmatch('[0-9a-f]{64}', str(item.get('reportSha256', ''))):
            raise ValueError('Unresolved public release acceptance gate')
    approval = value.get('storeApproval')
    if approval is not None:
        if not isinstance(approval,dict) or set(approval)!={'status','extensionId','reportSha256'} or approval.get('status') not in ('pending','approved') or approval.get('extensionId')!=value['extensionIds']['chrome']:
            raise ValueError('Invalid store approval declaration')
        if approval['status']=='approved' and not re.fullmatch('[0-9a-f]{64}',str(approval.get('reportSha256',''))):
            raise ValueError('Store approval evidence required')
    if metadata is not None:
        if metadata.get('product') != 'cueflora' or metadata.get('platform') != 'Windows' or metadata.get('architecture', '').lower() not in ('amd64', 'x86_64') or metadata.get('transportPolicy') != 'https-remote':
            raise ValueError('Public Windows x64 HTTPS runtime required')
        if metadata.get('sourceInventorySha256') != value['sourceInventorySha256'] or metadata.get('publicEvidence') != evidence:
            raise ValueError('Public release evidence/source binding mismatch')
    return value
