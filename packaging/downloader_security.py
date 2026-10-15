"""Explicit, source-bound downloader security overrides; no latest or hidden repins."""
import json
from pathlib import Path
import re
from packaging.version import Version
from pin_downloader_inputs import pins as upstream_pins
from release_inputs import ROOT,digest


def validate_origin(item,schema):
    override=item.get('securityOverride')
    if item.get('upstreamWheelHashVerified') is True:
        if override is not None: raise ValueError('Security overrides must not claim the original upstream wheel hash')
        return
    if schema!=2 or item.get('upstreamWheelHashVerified') is not False or not isinstance(override,dict) or set(override)!={'baselineVersion','advisories','metadata'}:
        raise ValueError('Unverified downloader pin requires an explicit security override')
    baseline=override['baselineVersion']
    if not isinstance(baseline,str) or not re.fullmatch(r'\d+(?:\.\d+){1,3}',baseline) or Version(item['version'])<=Version(baseline) or Version(item['version']).major!=Version(baseline).major:
        raise ValueError('Security override must be a bounded same-major upgrade')
    advisories=override['advisories']
    if not isinstance(advisories,list) or not advisories or len(advisories)>20 or any(not isinstance(url,str) or not re.fullmatch(r'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/security/advisories/GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}',url) for url in advisories) or len(set(advisories))!=len(advisories):
        raise ValueError('Exact primary advisory references required')
    metadata=override['metadata']
    if not isinstance(metadata,dict) or set(metadata)!={'file','url','sha256','bytes'} or metadata['file']!=item['name']+'-'+item['version']+'.pypi.json' or metadata['url']!='https://pypi.org/pypi/'+item['name']+'/'+item['version']+'/json' or not re.fullmatch('[0-9a-f]{64}',str(metadata['sha256'])) or type(metadata['bytes']) is not int or not 0<metadata['bytes']<=2*1024*1024:
        raise ValueError('Malformed exact security metadata binding')
    path=ROOT/'packaging/source-metadata'/metadata['file']
    if path.resolve()!=path or not path.is_file() or path.stat().st_size!=metadata['bytes'] or digest(path)!=metadata['sha256']:
        raise ValueError('Missing/changed immutable security metadata snapshot')
    original=json.loads(path.read_bytes())
    info=original.get('info',{})
    if info.get('name','').lower().replace('_','-')!=item['name'] or info.get('version')!=item['version'] or (info.get('license_expression') or info.get('license'))!=item.get('declaredLicence'):
        raise ValueError('Security metadata package/version/licence mismatch')
    for key in ('wheel','source'):
        record=item[key]
        matching=[entry for entry in original.get('urls',[]) if entry.get('filename')==record['file']]
        if len(matching)!=1 or matching[0].get('url')!=record['url'] or matching[0].get('digests',{}).get('sha256')!=record['sha256']:
            raise ValueError('Security wheel/source differs from exact primary metadata')


def verify_source_pins(lock,source):
    expected,hashes=upstream_pins(source)
    if set(expected)!={item['name'] for item in lock['dependencies']}: raise ValueError('Downloader upstream dependency set changed')
    for item in lock['dependencies']:
        override=item.get('securityOverride')
        baseline=override['baselineVersion'] if override else item['version']
        if expected[item['name']]!=baseline: raise ValueError('Security baseline differs from actual upstream source pin')
        if not override and item['wheel']['sha256'] not in hashes.get((item['name'],item['version']),set()):
            raise ValueError('Downloader wheel is not in the original upstream hash lock')
        validate_origin(item,lock['schema'])


def security_manifest(lock):
    return [{'name':item['name'],'baselineVersion':item['securityOverride']['baselineVersion'],
        'version':item['version'],'wheelSha256':item['wheel']['sha256'],'sourceSha256':item['source']['sha256'],
        'metadata':item['securityOverride']['metadata'],'advisories':item['securityOverride']['advisories']}
        for item in lock['dependencies'] if item.get('securityOverride')]


def verify_runtime_overrides(lock,probe):
    lines=probe.get('metadata',[])
    for item in security_manifest(lock):
        token=re.escape(item['name'].replace('-','_')+'-'+item['version'])
        if not any(re.search(r'(?<![\w.-])'+token+r'(?![\w.-])',line) for line in lines):
            raise ValueError('Security-patched library version not observed in built downloader')
