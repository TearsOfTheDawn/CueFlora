"""Private installation authorization is distinct from public release approval."""
import re
from pathlib import Path
from .bundle import digest
from .manifests import validate_release


def validate_package(payload, config, metadata, browsers, allow_prototype=False):
    validate_release(config)
    if set(browsers) - set(config['extensionIds']):
        raise ValueError('Selected browser has no configured identity')
    mode = config.get('mode', 'prototype')
    if mode not in ('prototype', 'private', 'public'):
        raise ValueError('Unsupported installation mode')
    if mode == 'public':
        from .public_release import validate_public
        validate_public(config, metadata)
        if digest(Path(payload) / 'runtime-manifest.json') != config['runtimeInventorySha256']:
            raise ValueError('Public package runtime binding mismatch')
        return
    if mode == 'private':
        if config.get('product') is not None and (config['product'] != 'cueflora' or metadata.get('product') != 'cueflora'):
            raise ValueError('Foreign product payload rejected')
        expected = config.get('runtimeInventorySha256')
        if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected):
            raise ValueError('Private package requires runtime inventory binding')
        if digest(Path(payload) / 'runtime-manifest.json') != expected:
            raise ValueError('Private package runtime binding mismatch')
        if config.get('publicReleaseAuthorized') is not False or config.get('redistributionApproved') is not False:
            raise ValueError('Private package cannot grant release approval')
    elif not allow_prototype:
        raise ValueError('Prototype payload is not a configured private installation')
