"""Copy verified public inputs into a fresh cache; preserve every prior cache."""
import argparse
import json
from pathlib import Path
import shutil
from release_inputs import ROOT,digest,obtain_inputs
from node_inputs import obtain as obtain_node


def seed(source,node_cache,output):
    if output.exists(): raise ValueError('Fresh offline cache required')
    lock=json.loads((ROOT/'packaging/inputs-windows.lock.json').read_text())
    # Read/validate source inputs before creating the target. No private audio or
    # interpreter snapshot is copied into this public-source build cache.
    for item in lock['files']:
        if item['file'] in ('ffmpeg.exe','ffprobe.exe','python-3.13.15-local-base.zip') or item['file'].startswith('FFmpeg-5d4d3bdc61-'): continue
        path=source/item['file']
        if path.is_symlink() or not path.is_file() or digest(path)!=item['sha256']: raise ValueError('Source cache input mismatch: '+item['file'])
    node,_=obtain_node(node_cache)
    output.mkdir(parents=True)
    for item in lock['files']:
        path=source/item['file']
        if item['file'] in ('ffmpeg.exe','ffprobe.exe','python-3.13.15-local-base.zip') or item['file'].startswith('FFmpeg-5d4d3bdc61-'): continue
        shutil.copy2(path,output/path.name)
    shutil.copy2(node,output/node.name)
    npm=output/'npm'; npm.mkdir()
    for name in ('_cacache','cueflora-npm-inputs.json'):
        path=source/'npm'/name
        if path.is_dir(): shutil.copytree(path,npm/name)
        elif path.is_file(): shutil.copy2(path,npm/name)
        else: raise ValueError('Pinned npm cache is incomplete')
    obtain_inputs(lock,output,source_audio=True)
    print('Fresh public-input cache seeded; no old audio binaries or private interpreter snapshot copied.')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','node-cache','output'): parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args(); seed(args.source.resolve(),args.node_cache.resolve(),args.output.resolve())
