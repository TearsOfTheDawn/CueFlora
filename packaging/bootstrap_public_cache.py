"""Fetch only exact published build inputs; no private FFmpeg/Python copies needed."""
import argparse
import json
from pathlib import Path
from release_inputs import ROOT, obtain_inputs
from audio_build import obtain, validate_inputs


def bootstrap(cache, audio_cache, evidence_cache, online=False):
    from node_inputs import obtain as obtain_node
    obtain_node(cache,online)
    from observed_sources import obtain as obtain_observed
    obtain_observed(evidence_cache,online)
    obtain_inputs(json.loads((ROOT/'packaging/inputs-windows.lock.json').read_text()),cache,offline=not online,source_audio=True)
    from build_downloader import obtain as obtain_downloader
    obtain_downloader(cache/'downloader',online)
    from collect_curl_sources import obtain as obtain_curl
    obtain_curl(evidence_cache,online)
    from collect_v8_notices import obtain as obtain_v8
    obtain_v8(evidence_cache,online)
    from cargo_notice_evidence import source_pins,obtain as obtain_cargo
    for item in source_pins(cache)[2]: obtain_cargo(item,evidence_cache/'cargo-registry-cache',online)
    from repository_notice_evidence import obtain_inputs as obtain_repository
    obtain_repository(evidence_cache/'cargo-repository-cache',ROOT/'packaging/repository-notice-inputs.lock.json',online)
    obtain(json.loads((ROOT/'packaging/audio-inputs.lock.json').read_text()),audio_cache,online)
    obtain(json.loads((ROOT/'packaging/audio-toolchain.lock.json').read_text()),audio_cache,online)
    from urllib.request import urlopen
    from release_inputs import digest
    import shutil
    lock = json.loads((ROOT/'packaging/evidence-windows.lock.json').read_text())
    validate_inputs({'schema':1,'files':lock['files']})
    evidence_cache.mkdir(parents=True,exist_ok=True)
    for item in lock['files']:
        if item['role'] in ('origin-checksums','binary-origin-evidence','candidate-build-recipes'): continue
        target = evidence_cache/item['file']
        if target.is_symlink(): raise ValueError('Linked source evidence')
        if not target.exists():
            if not online: raise ValueError('Missing exact source evidence')
            partial = target.with_suffix(target.suffix+'.partial')
            with urlopen(item['url'],timeout=60) as response, partial.open('xb') as stream: shutil.copyfileobj(response,stream)
            if digest(partial)!=item['sha256']: raise ValueError('Source evidence mismatch')
            partial.rename(target)
        if digest(target)!=item['sha256']: raise ValueError('Changed source evidence')
    print('Published-input cache verified. This is not redistribution approval.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--audio-cache',type=Path,required=True)
    parser.add_argument('--evidence-cache',type=Path,required=True)
    parser.add_argument('--online',action='store_true')
    args = parser.parse_args()
    bootstrap(args.cache.resolve(),args.audio_cache.resolve(),args.evidence_cache.resolve(),args.online)
