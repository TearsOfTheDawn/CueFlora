"""Inventory available third-party sources without asserting licence closure."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from release_inputs import digest


def bundle(audio, evidence, output):
    if output.exists(): raise ValueError('Fresh source-bundle directory required')
    if audio.is_symlink() or evidence.is_symlink() or not audio.is_dir() or not evidence.is_dir():
        raise ValueError('Ordinary source-evidence directories required')
    audio, evidence, output = audio.resolve(), evidence.resolve(), output.resolve()
    files = {}
    for prefix, root in [('audio',audio),('other-evidence',evidence)]:
        for path in sorted(root.rglob('*')):
            if not path.is_file(): continue
            relative = path.relative_to(root)
            if path.is_symlink() or path.resolve() != path or '..' in relative.parts or ':' in relative.as_posix():
                raise ValueError('Linked or unsafe source-evidence path')
            if path.suffix.lower() in ('.exe','.dll','.pyd','.wav','.mp3','.opus','.webm'):
                raise ValueError('Binary/media payload does not belong in source evidence')
            # Historical unmatched FFmpeg origin experiments are not candidate sources.
            if 'BtbN-' in path.name or path.name.startswith('FFmpeg-5d4d3bdc61-'): continue
            files[prefix+'/'+relative.as_posix()] = path
    if not files or not any(name.endswith('ffmpeg-9.0.2.tar.xz') for name in files):
        raise ValueError('Matching FFmpeg source evidence required')
    hashes = {name:digest(path) for name,path in files.items()}
    report = {'schema':1,'files':hashes,'completeCorrespondingSourceClosure':False,'redistributionApproved':False,
        'scope':'Available matching FFmpeg/Opus sources and partial dependency evidence, not complete legal clearance.'}
    output.mkdir(parents=True)
    archive = output/'CueFlora-third-party-sources.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as package:
        for name,path in files.items(): package.write(path,name)
        package.writestr('SOURCE_EVIDENCE_INVENTORY.json',json.dumps(report,indent=2)+'\n')
    with zipfile.ZipFile(archive) as package:
        expected = set(hashes) | {'SOURCE_EVIDENCE_INVENTORY.json'}
        if set(package.namelist()) != expected or len(package.namelist()) != len(expected): raise ValueError('Source-bundle membership mismatch')
        for name,checksum in hashes.items():
            computed = hashlib.sha256()
            with package.open(name) as stream:
                for chunk in iter(lambda:stream.read(1024*1024),b''): computed.update(chunk)
            if computed.hexdigest() != checksum: raise ValueError('Source-bundle hash mismatch')
        if json.loads(package.read('SOURCE_EVIDENCE_INVENTORY.json')) != report: raise ValueError('Source-bundle inventory mismatch')
    report.update({'archiveSha256':digest(archive),'verifiedMembers':len(hashes)+1})
    (output/'source-bundle-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('audio','evidence','output'): parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    result=bundle(args.audio.resolve(),args.evidence.resolve(),args.output.resolve())
    print(json.dumps({'members':result['verifiedMembers'],'sha256':result['archiveSha256']}))
