"""Build a self-contained private Setup; no live installation/publication."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tkinter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'native'))
from cueflora_setup.bundle import digest, verify_bundle
from runtime_notices import collect_interpreter_notices
from build_isolation import environment, native_inputs


def build(runtime, output, public_config=None, private_chrome_id=None, extension=None):
    if public_config and private_chrome_id: raise ValueError('Choose public release or private acceptance binding, not both')
    runtime = runtime.resolve()
    metadata = verify_bundle(runtime)
    if metadata.get('product') != 'cueflora' or metadata.get('platform') != 'Windows' or metadata.get('architecture', '').lower() not in ('amd64', 'x86_64'):
        raise ValueError('CueFlora Windows x64 runtime required')
    output = output.resolve()
    if output.exists():
        raise ValueError('Fresh output directory required')
    bundle = output / 'bundle'
    bundle.mkdir(parents=True)
    shutil.copytree(runtime, bundle / 'runtime')
    if public_config:
        from cueflora_setup.public_release import validate_public
        from cueflora_setup.package_policy import validate_package
        release = json.loads(public_config.read_text(encoding='utf-8'))
        checksum = digest(runtime/'runtime-manifest.json')
        if release.get('runtimeInventorySha256') not in (None,checksum): raise ValueError('Declared runtime binding does not match payload')
        release['runtimeInventorySha256'] = checksum
        source_hash = metadata['sourceInventorySha256']
        if release.get('sourceInventorySha256') not in (None,source_hash): raise ValueError('Declared source binding does not match payload')
        release['sourceInventorySha256'] = source_hash
        validate_public(release,metadata)
        validate_package(runtime,release,metadata,['chrome'])
    else:
        identity = json.loads((ROOT / 'preview-identity.json').read_text())
        if identity.get('developmentOnly') is not True:
            raise ValueError('Development-only identity required')
        if private_chrome_id:
            import re
            if not re.fullmatch('[a-p]{32}',private_chrome_id) or metadata.get('transportPolicy') != 'https-remote':
                raise ValueError('Private acceptance requires an explicit valid Chrome ID and HTTPS runtime')
        release = {'owner': 'Private CueFlora release acceptance' if private_chrome_id else 'Private CueFlora development preview', 'mode': 'private', 'product': 'cueflora',
            'extensionIds': {'chrome': private_chrome_id or identity['chromeId']}, 'runtimeInventorySha256': digest(runtime / 'runtime-manifest.json'),
            'publicReleaseAuthorized': False, 'redistributionApproved': False}
    if extension is not None:
        from cueflora_setup.extension_pair import verify_extension,INVENTORY
        data,_=verify_extension(extension)
        if data['version']!=metadata['hostVersion'] or data['chromeId']!=release['extensionIds']['chrome']:raise ValueError('Setup requires an exact matching extension/helper version and identity')
        shutil.copytree(extension,bundle/'extension')
        release['extensionInventorySha256']=digest(bundle/'extension'/INVENTORY)
        verify_extension(bundle/'extension',release['extensionInventorySha256'])
    elif tuple(map(int,metadata['hostVersion'].split('.'))) >= (0,2,0):raise ValueError('CueFlora 0.2 Setup requires a matched extension payload')
    (bundle / 'release.json').write_text(json.dumps(release, indent=2) + '\n', encoding='utf-8')
    for source in [ROOT / 'LICENSE.md', ROOT / 'docs/REDISTRIBUTION_CHECKLIST.md', ROOT / 'packaging/requirements-windows.lock']:
        shutil.copy2(source, bundle / source.name)
    collect_interpreter_notices(bundle)
    tkinter.Tcl().eval('info library')
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--onefile', '--windowed', '--noupx',
        '--name', 'CueFlora Setup', '--icon', str(ROOT / 'public/icon/flower.ico'),
        '--paths', str(ROOT / 'native'), '--paths', str(Path(tkinter.__file__).parent.parent), '--hidden-import', 'tkinter',
        '--add-data', str(bundle) + ':bundle', '--add-data',str(ROOT/'native/cueflora_setup/legacy_extensions.json')+':cueflora_setup', '--distpath', str(output / 'dist'), '--workpath', str(output / 'work'),
        '--specpath', str(output), str(ROOT / 'packaging/setup_entry.py')], check=True, env=environment())
    (output/'native-input-isolation.json').write_text(json.dumps({'inheritedPathUsed':False,
        'inputs':native_inputs(output/'work/CueFlora Setup/Analysis-00.toc',payload=(bundle/'runtime',metadata['files']))},indent=2)+'\n',encoding='utf-8')
    print(output / 'dist/CueFlora Setup.exe')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--public-config', type=Path, help='Authorized exact public identity/evidence, never a preview override')
    parser.add_argument('--private-chrome-id', help='Real assigned ID for private acceptance only; no release approval')
    parser.add_argument('--extension',type=Path,help='Matching identified/inventoried Chrome extension for paired installation')
    args = parser.parse_args()
    build(args.runtime, args.output, args.public_config,args.private_chrome_id,args.extension)
