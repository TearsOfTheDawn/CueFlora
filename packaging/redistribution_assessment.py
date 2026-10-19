"""Verify a recorded dependency review; never manufacture legal approval."""
import hashlib
import json
from pathlib import Path,PurePosixPath
import re
from release_inputs import digest

REVIEWABLE={'yt-dlp native dependencies','Deno/V8','CPython native dependencies','Authentication native dependencies'}
PURPOSES={'notice','corresponding-source','build-recipe','binary-scope','redistribution-terms'}


def ledger_identity(ledger):
    return hashlib.sha256(json.dumps(ledger,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def template(ledger,bindings):
    return {'artifacts':bindings,'gate':'licences','status':'pending','reviewedBy':None,'reason':None,
        'redistributionAssessment':{'schema':1,'ledgerSha256':ledger_identity(ledger),'reviewedBy':None,
            'findings':[{**issue,'disposition':'unresolved','basis':'','references':[]} for issue in ledger.get('unresolvedEvidence',[])]},
        'instructions':'Pending template only. Actual reviewer must address every exact issue with candidate-relative hashed evidence. No waiver, invented copyright text or automatic legal approval.'}


def verify(record,ledger,bindings,preparation):
    """Files/claims are authenticated to a candidate, not to a reviewer identity."""
    if not isinstance(record,dict) or record.get('gate')!='licences' or record.get('status')!='passed' or record.get('artifacts')!=bindings or not isinstance(record.get('reviewedBy'),str) or not record['reviewedBy'].strip():
        raise ValueError('A verified, non-waived licence decision is required')
    review=record.get('redistributionAssessment')
    if not isinstance(review,dict) or set(review)!={'schema','ledgerSha256','reviewedBy','findings'} or review['schema']!=1 or review['ledgerSha256']!=ledger_identity(ledger) or review['reviewedBy']!=record.get('reviewedBy'):
        raise ValueError('Dependency assessment does not match exact ledger/reviewer')
    issues=ledger.get('unresolvedEvidence')
    if not isinstance(issues,list) or not issues or any(not isinstance(item,dict) or item.get('component') not in REVIEWABLE for item in issues) or ledger.get('unassignedRuntimeFiles'):
        raise ValueError('Mandatory missing source/notice/file-attribution evidence cannot be cleared by review')
    expected={(item['component'],item['reason']) for item in issues}
    findings=review['findings']
    if not isinstance(findings,list) or len(findings)!=len(expected): raise ValueError('Every unresolved dependency issue needs a finding')
    root=Path(preparation).resolve(); seen=set(); references=[]
    for item in findings:
        if not isinstance(item,dict) or set(item)!={'component','reason','disposition','basis','references'}:
            raise ValueError('Malformed dependency finding')
        key=(item['component'],item['reason'])
        if key not in expected or key in seen or item['disposition'] not in ('obligations-satisfied','not-shipped','no-corresponding-source-required') or not isinstance(item['basis'],str) or len(item['basis'].strip())<20 or len(item['basis'])>6000:
            raise ValueError('Unknown/duplicate/unresolved dependency finding')
        seen.add(key); refs=item['references']
        if not isinstance(refs,list) or not refs or len(refs)>100: raise ValueError('Actual hashed dependency evidence files required')
        purposes=set()
        for ref in refs:
            if not isinstance(ref,dict) or set(ref)!={'path','sha256','purpose'} or ref['purpose'] not in PURPOSES or not re.fullmatch('[0-9a-f]{64}',str(ref['sha256'])):
                raise ValueError('Malformed dependency evidence reference')
            name=ref['path']
            if not isinstance(name,str) or not name or '\\' in name or ':' in name: raise ValueError('Unsafe dependency evidence path')
            relative=PurePosixPath(name)
            if relative.is_absolute() or '..' in relative.parts or relative.as_posix()!=name: raise ValueError('Unsafe dependency evidence path')
            path=root/name
            if path.resolve()!=path or not path.is_file() or path.stat().st_size>2*1024*1024*1024 or digest(path)!=ref['sha256']:
                raise ValueError('Missing/linked/changed dependency evidence')
            purposes.add(ref['purpose']); references.append(ref)
        if item['disposition']=='not-shipped' and 'binary-scope' not in purposes:
            raise ValueError('Non-shipment judgment requires binary scope evidence')
        if item['disposition']=='no-corresponding-source-required' and not purposes.intersection({'notice','redistribution-terms'}):
            raise ValueError('Notice-only judgment requires actual licence/terms evidence')
    return {'acceptedRecordedAssessment':True,'ledgerSha256':review['ledgerSha256'],'reviewedBy':review['reviewedBy'],
        'findingCount':len(findings),'verifiedReferences':references,
        'scope':'Exact-bound recorded reviewer judgments with real evidence bytes; not reviewer authentication, legal advice or independent proof of software safety.'}
