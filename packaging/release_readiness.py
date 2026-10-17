"""Separate measured engineering readiness from external release authorization."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'native'))
from cueflora_setup.public_release import validate_public
from approval_evidence import verified_decisions

HELPER_GATES = ('engineering','sourceExport','redistributionEvidence',
    'redistributionAuthorized','securityAndPolicy','publicationAuthorized')


def assess(engineering, source, ledger, configuration=None, approvals=None, evidence_root=None, preparation_root=None):
    github = isinstance(configuration,dict) and configuration.get('distribution') == 'github'
    gates = {'engineering':engineering.get('engineeringPassed') is True,
        'sourceExport':source.get('passed') is True and source.get('issues') == [],
        'redistributionEvidence':ledger.get('correspondingSourceComplete') is True and ledger.get('remainingObligations') == [],
        'publicIdentityAndAcceptance':False,'chromeStoreApproval':False,'publicationAuthorized':False,
        'redistributionAuthorized':False,'securityAndPolicy':False,'publicMaterials':False}
    issues = []
    if github: gates.pop('chromeStoreApproval')
    decisions = {}
    dependency_assessment=None
    if configuration is not None:
        try: validate_public(configuration)
        except (ValueError, TypeError): issues.append('Invalid or incomplete public identity')
        else:
            try:
                if approvals is None or evidence_root is None: raise ValueError('Hash-bound external decision sidecar is missing')
                bindings = engineering['artifactBindings']
                if bindings['sourceInventorySha256'] != source['sourceInventorySha256'] or bindings['sourceInventorySha256'] != configuration['sourceInventorySha256'] or bindings['runtimeInventorySha256'] != configuration['runtimeInventorySha256']:
                    raise ValueError('Readiness reports/configuration refer to different source or runtime')
                decisions = verified_decisions(approvals,evidence_root,bindings,'github' if github else 'chrome-store')
                gates['publicIdentityAndAcceptance'] = all(decisions[name] in ('passed','waived') for name in ('cleanWindows','chromeRun'))
                if not github: gates['chromeStoreApproval'] = decisions['storeApproval'] == 'passed'
                gates['publicationAuthorized'] = decisions['publication'] == 'passed'
                gates['redistributionAuthorized'] = decisions['licences'] == 'passed'
                if not gates['redistributionEvidence'] and decisions['licences']=='passed' and preparation_root is not None:
                    try:
                        path=Path(evidence_root)/approvals['gates']['licences']['report']
                        record=json.loads(path.read_text())
                        from redistribution_assessment import verify
                        dependency_assessment=verify(record,ledger,bindings,preparation_root)
                        gates['redistributionEvidence']=True
                    except (ValueError,TypeError,KeyError,OSError):
                        issues.append('Dependency assessment is missing, incomplete or does not match actual candidate evidence')
                gates['securityAndPolicy'] = decisions['nativeSecurity'] == 'passed' and decisions['downloadPolicy'] in (('passed','reviewed') if github else ('passed',))
                gates['publicMaterials'] = all(decisions[name] == 'passed' for name in (('publicLocations',) if github else ('screenshots','publicLocations')))
            except (ValueError,TypeError,KeyError,OSError): issues.append('External evidence is missing, malformed or does not match candidate artifacts')
    return {'schema':1,'gates':gates,'publicReleaseReady':all(gates.values()),'published':False,
        'helperDownloadReady':all(gates[name] for name in HELPER_GATES),
        'helperRemaining':[name for name in HELPER_GATES if not gates[name]],
        'unsignedAccepted':True,'remaining':[name for name,passed in gates.items() if not passed],
        'decisions':decisions,'waived':[name for name,status in decisions.items() if status == 'waived'],'issues':issues,
        'dependencyAssessment':dependency_assessment,
        'distribution':'github' if github else 'chrome-store',
        'downloadPermissionEstablished':False if decisions.get('downloadPolicy') == 'reviewed' else None,
        'interpretation':'Recorded engineering and publisher decisions, not YouTube permission, Store approval, legal advice or a guarantee of safety.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('engineering','source','ledger','output'): parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--configuration',type=Path)
    parser.add_argument('--approvals',type=Path)
    args = parser.parse_args()
    result = assess(json.loads(args.engineering.read_text()),json.loads(args.source.read_text()),json.loads(args.ledger.read_text()),
        json.loads(args.configuration.read_text()) if args.configuration else None,
        json.loads(args.approvals.read_text()) if args.approvals else None,args.approvals.parent if args.approvals else None,args.engineering.parent)
    with args.output.open('x',encoding='utf-8') as stream: json.dump(result,stream,indent=2)
    print(json.dumps(result,indent=2))
