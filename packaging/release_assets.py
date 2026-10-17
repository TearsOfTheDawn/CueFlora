"""Copy immutable reviewed bytes to predictable release filenames; never publish."""
import argparse
import json
from pathlib import Path
import shutil
from release_inputs import digest
import re


def assemble(preparation,output):
    if output.exists(): raise ValueError('Fresh release-assets directory required')
    report=json.loads((preparation/'readiness.json').read_text())
    if report.get('engineeringPassed') is not True: raise ValueError('Engineering candidate has not passed')
    bindings=report['artifactBindings']; version=report['effectiveConfiguration']['version']
    if not re.fullmatch(r'\d+\.\d+\.\d+',version): raise ValueError('Exact candidate version required')
    files={'CueFlora-'+version+'-Setup.exe':(preparation/'delivery/CueFlora Setup/CueFlora Setup.exe',bindings['setupSha256']),
        'CueFlora-Chrome-store-upload.zip':(preparation/'delivery/CueFlora Setup/CueFlora-Chrome-store-upload.zip',bindings['extensionSha256']),
        'CueFlora-source.zip':(preparation/'source-export/CueFlora-source.zip',report['sourceArchive']['archiveSha256']),
        'CueFlora-third-party-sources.zip':(preparation/'source-bundle/CueFlora-third-party-sources.zip',json.loads((preparation/'source-bundle/source-bundle-report.json').read_text())['archiveSha256'])}
    github = report['effectiveConfiguration'].get('distribution') == 'github'
    if github:
        files.pop('CueFlora-Chrome-store-upload.zip')
        files['CueFlora-Chrome-extension.zip'] = (preparation/'delivery/CueFlora Setup/CueFlora-Chrome-extension.zip',bindings['extensionSha256'])
        files['CueFlora-'+version+'-Windows-x64.zip'] = (preparation/'delivery'/report['artifacts']['archive'],report['artifacts']['sha256'])
    for source,checksum in files.values():
        if source.is_symlink() or digest(source)!=checksum: raise ValueError('Candidate artifact differs from verified report')
    output.mkdir(parents=True)
    for name,(source,_) in files.items(): shutil.copy2(source,output/name)
    if github:
        import zipfile
        notices_root = preparation/'delivery/CueFlora Setup/notices'
        with zipfile.ZipFile(output/'CueFlora-notices.zip','x',zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(notices_root.rglob('*')):
                if path.is_symlink() or path.resolve()!=path: raise ValueError('Linked notice path')
                if path.is_file(): archive.write(path,path.relative_to(notices_root).as_posix())
    for name in ('readiness.json','release-gates.json','external-approvals.json','build-comparison.json'):
        shutil.copy2(preparation/name,output/name)
    # Older candidates did not emit this pending template; retain compatibility.
    template=preparation/'licence-assessment.template.json'
    if template.exists():
        if template.is_symlink() or not template.is_file(): raise ValueError('Invalid licence assessment template')
        shutil.copy2(template,output/template.name)
    shutil.copytree(preparation/'release-ledger',output/'release-ledger')
    manifest={'schema':1,'version':version,'artifacts':bindings,'files':{path.relative_to(output).as_posix():digest(path) for path in output.rglob('*') if path.is_file()},
        'published':False,'publicReleaseReady':False,'approval':'See hash-bound external decisions; file assembly does not grant release approval'}
    (output/'RELEASE_ASSETS.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('preparation','output'): parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args(); assemble(args.preparation.resolve(),args.output.resolve())
