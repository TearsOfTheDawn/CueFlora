"""Validate explicit external decisions against unchanged candidate artifact hashes."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

GATES = ('licences','downloadPolicy','nativeSecurity','cleanWindows','chromeRun','screenshots','publicLocations','storeApproval','publication')
GITHUB_GATES = tuple(name for name in GATES if name not in ('screenshots','storeApproval'))
WAIVABLE = {'cleanWindows','chromeRun'}
BINDINGS = {'sourceInventorySha256','runtimeInventorySha256','setupSha256','extensionSha256'}


def validate_bindings(value):
    if not isinstance(value,dict) or set(value) != BINDINGS or any(not isinstance(v,str) or not re.fullmatch('[0-9a-f]{64}',v) for v in value.values()):
        raise ValueError('Complete exact artifact bindings required')
    return value


def verified_decisions(decisions, root, bindings, distribution='chrome-store'):
    """Report files prove recorded declarations, not reviewer authenticity or safety."""
    validate_bindings(bindings)
    if distribution not in ('chrome-store','github'): raise ValueError('Unknown decision channel')
    github = distribution == 'github'
    fields = {'schema','artifacts','gates','distribution'} if github else {'schema','artifacts','gates'}
    if not isinstance(decisions,dict) or set(decisions) != fields or decisions['schema'] != (2 if github else 1) or decisions['artifacts'] != bindings or (github and decisions['distribution'] != 'github'):
        raise ValueError('Approval sidecar does not match candidate')
    gates = decisions['gates']
    if not isinstance(gates,dict) or set(gates) != set(GITHUB_GATES if github else GATES): raise ValueError('All channel-specific release decisions must be explicit')
    root = Path(root).resolve()
    result = {}
    for name,item in gates.items():
        if not isinstance(item,dict) or set(item) != {'status','reviewedBy','reason','report','reportSha256'}:
            raise ValueError('Malformed release decision')
        status = item['status']
        allowed = ('pending','passed','failed','waived','reviewed') if github and name == 'downloadPolicy' else ('pending','passed','failed','waived')
        if status not in allowed: raise ValueError('Unknown release decision status')
        if status == 'waived' and name not in WAIVABLE: raise ValueError('Only explicit manual acceptance may be waived')
        if status in ('pending','failed'):
            result[name] = status
            continue
        if not isinstance(item['reviewedBy'],str) or not item['reviewedBy'].strip() or len(item['reviewedBy']) > 200 or not isinstance(item['reason'],str) or not item['reason'].strip() or len(item['reason']) > 2000:
            raise ValueError('Reviewer and reason required; never generate approval from a build pass')
        report = item['report']
        if not isinstance(report,str) or not report or '\\' in report or ':' in report:
            raise ValueError('Evidence must use a relative ordinary file')
        relative = PurePosixPath(report)
        if relative.is_absolute() or any(part in ('..','.') for part in relative.parts) or relative.as_posix() != report:
            raise ValueError('Unsafe evidence path')
        path = root/report
        if path.resolve() != path or not path.is_file() or path.stat().st_size > 8*1024*1024:
            raise ValueError('Missing/linked/oversized evidence')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != item['reportSha256']: raise ValueError('Evidence content hash mismatch')
        record = json.loads(raw)
        if not isinstance(record,dict) or record.get('artifacts') != bindings or record.get('gate') != name or record.get('status') != status or record.get('reviewedBy') != item['reviewedBy'] or record.get('reason') != item['reason']:
            raise ValueError('Evidence claims/bindings do not match decision')
        if status == 'reviewed' and (record.get('authorizationEstablished') is not False or record.get('publisherDirectedPublication') is not True or record.get('publisherDirection') != 'Yes, publish anyway'):
            raise ValueError('Reviewed risk requires absent authorisation and the explicit publisher decision')
        result[name] = status
    return result


def pending(bindings, distribution='chrome-store'):
    validate_bindings(bindings)
    if distribution not in ('chrome-store','github'): raise ValueError('Unknown decision channel')
    result = {'schema':2 if distribution == 'github' else 1,'artifacts':bindings,'gates':{name:{'status':'pending','reviewedBy':None,'reason':None,'report':None,'reportSha256':None} for name in (GITHUB_GATES if distribution == 'github' else GATES)}}
    if distribution == 'github': result['distribution'] = 'github'
    return result
