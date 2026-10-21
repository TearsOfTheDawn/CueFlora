"""Create an exact identified extension inventory for paired Setup payloads."""
import argparse
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'native'))
from cueflora_setup.extension_pair import tree,identity,verify_extension,INVENTORY


def build(source,output):
    source=Path(source).absolute();output=Path(output).absolute()
    if output.exists():raise ValueError('Fresh extension payload output required')
    files=tree(source)
    if INVENTORY in files:verify_extension(source);files.pop(INVENTORY)
    chrome_id,version=identity(source)
    shutil.copytree(source,output)
    (output/INVENTORY).write_text(json.dumps({'schema':1,'product':'cueflora','version':version,'chromeId':chrome_id,'files':files},sort_keys=True,indent=2)+'\n',encoding='utf-8')
    verify_extension(output)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();build(args.input,args.output)
