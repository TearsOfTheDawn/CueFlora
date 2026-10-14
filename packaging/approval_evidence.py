"""Validate explicit external decisions against unchanged candidate artifact hashes."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

GATES = ('licences','downloadPolicy','nativeSecurity','cleanWindows','chromeRun','screenshots','publicLocations','storeApproval','publication')
WAIVABLE = {'cleanWindows','chromeRun'}
BINDINGS = {'sourceInventorySha256','runtimeInventorySha256','setupSha256','extensionSha256'}


def validate_bindings(value):
    if not isinstance(value,dict) or set(value) != BINDINGS or any(not isinstance(v,str) or not re.fullmatch('[0-9a-f]{64}',v) for v in value.values()):
        raise ValueError('Complete exact artifact bindings required')
    return value


def verified_decisions(decisions, root, bindings):
    """Report files prove recorded declarations, not reviewer authenticity or safety."""
    validate_bindings(bindings)
    if not isinstance(decisions,dict) or set(decisions) != {'schema','artifacts','gates'} or decisions['schema'] != 1 or decisions['artifacts'] != bindings:
        raise ValueError('Approval sidecar does not match candidate')
    gates = decisions['gates']
    if not isinstance(gates,dict) or set(gates) != set(GATES): raise ValueError('All release decisions must be explicit')
    root = Path(root).resolve()
    result = {}
    for name,item in gates.items():
        if not isinstance(item,dict) or set(item) != {'status','reviewedBy','reason','report','reportSha256'}:
            raise ValueError('Malformed release decision')
        status = item['status']
        if status not in ('pending','passed','failed','waived'): raise ValueError('Unknown release decision status')
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
        result[name] = status
    return result


def pending(bindings):
    validate_bindings(bindings)
    return {'schema':1,'artifacts':bindings,'gates':{name:{'status':'pending','reviewedBy':None,'reason':None,'report':None,'reportSha256':None} for name in GATES}}
