"""Assemble a private preview and keyless store-upload candidate; never publish."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / 'native'))
from cueflora_setup.bundle import digest, verify_bundle
from cueflora_setup.package_policy import validate_package
from verify_archive import verify_archive
from installation_guide import render as installation_guide


def extension_identity(key):
    hexadecimal = hashlib.sha256(base64.b64decode(key,validate=True)).hexdigest()[:32]
    return ''.join(chr(97+int(character,16)) for character in hexadecimal)


def assemble(setup, runtime, extension, output, store_extension=None, release_ledger=None):
    output = output.resolve()
    if output.exists():
        raise ValueError('Fresh assembly directory required')
    metadata = verify_bundle(runtime)
    release = json.loads((setup.parent.parent / 'bundle/release.json').read_text(encoding='utf-8'))
    validate_package(runtime,release,metadata,['chrome'])
    identity = json.loads((ROOT / 'preview-identity.json').read_text(encoding='utf-8'))
    manifest = json.loads((extension / 'manifest.json').read_text(encoding='utf-8'))
    public = release.get('mode') == 'public'
    if public:
        if metadata.get('transportPolicy') != 'https-remote': raise ValueError('Public runtime must enforce HTTPS')
        if 'key' in manifest and extension_identity(manifest['key']) != release['extensionIds']['chrome']:
            raise ValueError('Acceptance extension and installer identity disagree')
    elif extension_identity(manifest['key']) != identity['chromeId'] or release['extensionIds'] != {'chrome':identity['chromeId']}:
        raise ValueError('Preview identity and installer differ')
    contents = output / 'CueFlora Setup'
    contents.mkdir(parents=True)
    shutil.copy2(setup,contents / 'CueFlora Setup.exe')
    if not public: shutil.copytree(extension,contents / 'Chrome-preview')
    elif 'key' in manifest: shutil.copytree(extension,contents/'Chrome-acceptance')
    (contents/'START_HERE.md').write_text(installation_guide(release, metadata['hostVersion'],
        acceptance=public and 'key' in manifest), encoding='utf-8')
    # A future store upload must not carry the unpacked preview identity. The
    # store-assigned identity will require a separately bound future installer.
    store_extension = store_extension or extension
    store_manifest = json.loads((store_extension / 'manifest.json').read_text(encoding='utf-8'))
    if store_extension != extension and 'key' in store_manifest:
        raise ValueError('Store build must omit the development identity')
    store_manifest = {key:value for key,value in store_manifest.items() if key != 'key'}
    store_archive = contents / 'CueFlora-Chrome-store-upload.zip'
    with zipfile.ZipFile(store_archive,'w',zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(store_extension.rglob('*')):
            if file.is_file():
                name = file.relative_to(store_extension).as_posix()
                if name == 'manifest.json':
                    archive.writestr(name,json.dumps(store_manifest,indent=2)+'\n')
                else:
                    archive.write(file,name)
    with zipfile.ZipFile(store_archive) as archive:
        if archive.testzip() is not None or 'key' in json.loads(archive.read('manifest.json')):
            raise ValueError('Store-upload candidate invalid')
        expected = {p.relative_to(store_extension).as_posix():digest(p) for p in store_extension.rglob('*') if p.is_file() and p.name != 'manifest.json'}
        actual = {name:hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist() if name != 'manifest.json'}
        if actual != expected:
            raise ValueError('Store-upload content mismatch')
    documentation = [ROOT/'LICENSE.md',ROOT/'docs/INSTALLATION.md',ROOT/'docs/DISTRIBUTION.md',
        ROOT/'docs/REDISTRIBUTION_CHECKLIST.md',ROOT/'docs/RELEASE_COMPLETION.md'] if public else [ROOT / 'LICENSE.md',ROOT / 'docs/INSTALLATION.md',ROOT / 'docs/DISTRIBUTION.md',
                   ROOT / 'docs/REDISTRIBUTION_CHECKLIST.md', ROOT / 'docs/IMPLEMENTATION_HANDOFF.md', ROOT / 'docs/PRIVATE_PREVIEW_POLISH_HANDOFF.md',
                   ROOT / 'packaging/public-release.template.json', ROOT / 'docs/PUBLIC_RELEASE_BLOCKERS.md', ROOT / 'docs/PUBLIC_RELEASE_PREPARATION.md',
                   ROOT / 'docs/PUBLIC_RELEASE_HANDOFF.md', ROOT / 'packaging/inputs-windows.lock.json', ROOT / 'packaging/requirements-windows-hashed.lock',
                   ROOT / 'packaging/release.template.json',runtime / 'runtime-manifest.json',
                   setup.parent.parent / 'bundle/release.json']
    if public: documentation += [runtime/'runtime-manifest.json',setup.parent.parent/'bundle/release.json']
    for source in documentation:
        shutil.copy2(source,contents / source.name)
    shutil.copytree(runtime / 'licenses',contents / 'notices/runtime')
    shutil.copytree(ROOT / 'docs/store', contents / 'store-materials')
    if release_ledger:
        shutil.copytree(release_ledger,contents/'release-ledger')
    for name in (['SECURE_CREDENTIALS.md','STORE_POLICY_ASSESSMENT.md'] if public else ['SECURE_CREDENTIALS.md','SECURITY_HARDENING_HANDOFF.md','FFMPEG_REPLACEMENT_PROPOSAL.md','STORE_POLICY_ASSESSMENT.md']):
        source=ROOT/'docs'/name
        if source.is_file(): shutil.copy2(source,contents/name)
    shutil.copy2(ROOT/'docs/PUBLIC_CANDIDATE.md',contents/'PUBLIC_CANDIDATE.md')
    if (runtime/'corresponding-source').is_dir(): shutil.copytree(runtime/'corresponding-source',contents/'corresponding-source')
    shutil.copy2(ROOT/'packaging/evidence-windows.lock.json',contents/'evidence-windows.lock.json')
    bundle = setup.parent.parent / 'bundle'
    for path in bundle.glob('*notice*'):
        if path.is_file():
            shutil.copy2(path,contents / 'notices' / path.name)
        elif path.is_dir():
            shutil.copytree(path,contents / 'notices' / path.name)
    lock = json.loads((ROOT / 'package-lock.json').read_text(encoding='utf-8'))
    dependencies = []
    for path,item in lock['packages'].items():
        if not path or not path.startswith('node_modules/'):
            continue
        folder = ROOT / path
        description = json.loads((folder / 'package.json').read_text(encoding='utf-8')) if (folder / 'package.json').is_file() else {}
        name = description.get('name') or path.split('node_modules/')[-1]
        notices = []
        if folder.is_dir():
            for file in folder.iterdir():
                if file.is_file() and any(word in file.name.lower() for word in ['license','copying','notice']):
                    target = contents / 'notices/npm' / hashlib.sha256(path.encode()).hexdigest()[:12] / file.name
                    target.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(file,target)
                    notices.append(target.relative_to(contents).as_posix())
        dependencies.append({'name':name,'version':item.get('version'), 'lockfileDev':item.get('dev',False),
            'integrity':item.get('integrity'), 'license':description.get('license'),'notices':notices})
    emitted = [json.loads(p.read_text()) for p in extension.rglob('cueflora-bundled-dependencies-*.json')]
    if not emitted:
        raise ValueError('Observed extension inventories missing')
    shipped_js = {'scope':'Union of per-entrypoint Vite chunk modules, not all build dependencies', 'entrypoints':emitted,
        'packages':list({(item['name'],item['version']):item for record in emitted for item in record['packages']}.values())}
    inventory = {'product':'CueFlora','runtime':metadata['dependencies'], 'pythonBuildEnvironment':metadata.get('buildEnvironmentDependencies'),
        'observedExtensionBundle':shipped_js, 'npmBuildAndRuntimeDependencies':dependencies,
        'npmInventoryScope':'All locked dependencies, not a claim that each dependency is shipped or that bundled-code attribution is fully reviewed.',
        'redistributionApproved':False}
    (contents / 'dependency-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n',encoding='utf-8')
    hashes = {p.relative_to(contents).as_posix():digest(p) for p in sorted(contents.rglob('*')) if p.is_file()}
    (contents / 'SHA256SUMS.json').write_text(json.dumps(hashes,indent=2)+'\n',encoding='utf-8')
    archive = Path(shutil.make_archive(str(output / ('CueFlora-Windows-x64-Chrome-public-candidate' if public else 'CueFlora-Windows-x64-Chrome-preview')),'zip',output,contents.name))
    report = {'product':'CueFlora','previewOnly':not public,'developmentChromeId':None if public else identity['chromeId'],
        'setupSha256':digest(contents / 'CueFlora Setup.exe'), 'setupBytes':setup.stat().st_size,
        'archive':archive.name,'sha256':digest(archive),'archiveBytes':archive.stat().st_size,
        'archiveVerification':verify_archive(archive),'storeCandidateHasDevelopmentKey':False,
        'publicReleaseAuthorized':release['publicReleaseAuthorized'],'redistributionApproved':release['redistributionApproved'],
        'realBrowserAcceptance':False,'externalAcceptanceDeclarations':release.get('evidence') if public else None,
        'published':False,'unsigned':True}
    (output / 'artifact-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['setup','runtime','extension','output']:
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--store-extension',type=Path)
    parser.add_argument('--release-ledger',type=Path)
    args = parser.parse_args()
    print(json.dumps(assemble(args.setup,args.runtime,args.extension,args.output,args.store_extension,args.release_ledger),indent=2))
