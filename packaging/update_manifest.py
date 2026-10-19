"""Prepare metadata for a separately authorised future stable GitHub release."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'native'))
from cueflora_setup.bundle import digest
from cueflora_setup.extension_pair import verify_extension,INVENTORY
from cueflora_host.updates import REPOSITORY,CHROME_ID,version,validate_manifest


def build(setup,runtime,extension,release,output):
    setup=Path(setup);runtime=Path(runtime);extension=Path(extension)
    config=json.loads(Path(release).read_text());metadata=json.loads((runtime/'runtime-manifest.json').read_text())
    ext,_=verify_extension(extension,config.get('extensionInventorySha256'))
    target=metadata['hostVersion'];version(target)
    if config.get('distribution')!='github' or config['extensionIds']!={'chrome':CHROME_ID} or config['runtimeInventorySha256']!=digest(runtime/'runtime-manifest.json') or ext['version']!=target:raise ValueError('Matching GitHub extension/helper/configuration required')
    name='CueFlora-'+target+'-Setup.exe'
    data={'schema':1,'product':'cueflora','repository':REPOSITORY,'version':target,'platform':'Windows','architecture':'x64','chromeId':CHROME_ID,
        'minimumUpdaterVersion':'0.2.0','runtimeInventorySha256':digest(runtime/'runtime-manifest.json'),
        'extensionInventorySha256':digest(extension/INVENTORY),'sourceInventorySha256':metadata['sourceInventorySha256'],
        'setup':{'name':name,'size':setup.stat().st_size,'sha256':digest(setup),
                 'url':'https://github.com/'+REPOSITORY+'/releases/download/v'+target+'/'+name}}
    # Validate construction against a synthetic earlier installed version, not an approval.
    validate_manifest(data,current='0.0.0')
    from cueflora_host.update_payload import verify_update_payload
    verify_update_payload(setup,data)
    with Path(output).open('x',encoding='utf-8') as stream:json.dump(data,stream,indent=2);stream.write('\n')
    return data


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('setup','runtime','extension','release','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();build(args.setup,args.runtime,args.extension,args.release,args.output)
