"""Restore only exact OAuth dependency inputs; no moving package resolution."""
import argparse
import json
from pathlib import Path
import shutil
import urllib.request
from release_inputs import ROOT, digest


def restore(cache, online=False):
    cache=Path(cache); cache.mkdir(parents=True,exist_ok=True)
    lock=json.loads((ROOT/'packaging/inputs-windows.lock.json').read_text())
    names={item['file'] for item in lock['pythonWheels'] if item['name'].lower() in ('pyjwt','cryptography','cffi','pycparser')}
    sources={'pyjwt-2.15.1.tar.gz','cryptography-50.0.2.tar.gz','cffi-2.1.1.tar.gz','pycparser-3.11.tar.gz'}
    rows=[item for item in lock['files'] if item['file'] in names|sources]
    if len(rows)!=8: raise ValueError('OAuth wheel/source pins missing')
    for item in rows:
        target=cache/item['file']
        if not target.exists():
            if not online: raise ValueError('Missing exact OAuth input: '+item['file'])
            temporary=cache/(item['file']+'.partial')
            with urllib.request.urlopen(item['url'],timeout=30) as source,temporary.open('xb') as output:
                shutil.copyfileobj(source,output)
            if digest(temporary)!=item['sha256']: raise ValueError('OAuth input hash mismatch')
            temporary.rename(target)
        if target.is_symlink() or digest(target)!=item['sha256']: raise ValueError('Changed OAuth input')
    return rows


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,required=True); parser.add_argument('--online',action='store_true')
    args=parser.parse_args(); print(json.dumps(restore(args.cache,args.online),indent=2))
