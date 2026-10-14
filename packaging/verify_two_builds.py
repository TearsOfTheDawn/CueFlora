"""Reject unexplained two-build differences; hashes/attestations are not safety."""
import hashlib
import io
import json
from pathlib import Path
import zipfile
import argparse
from release_inputs import digest,compare_outputs,explain_frozen_differences,explain_library_order


def normalized_bootloader(path):
    from PyInstaller.archive.readers import CArchiveReader
    import pefile
    archive=CArchiveReader(str(path)); raw=bytearray(path.read_bytes()[:archive._start_offset])
    image=pefile.PE(str(path),fast_load=True)
    offsets=[image.FILE_HEADER.get_field_absolute_offset('TimeDateStamp'),image.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum')]
    image.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_DEBUG']])
    offsets.extend(entry.struct.get_field_absolute_offset('TimeDateStamp') for entry in getattr(image,'DIRECTORY_ENTRY_DEBUG',[]))
    for offset in offsets:
        if offset+4>len(raw): raise ValueError('PE timestamp/checksum outside bootloader')
        raw[offset:offset+4]=b'\0'*4
    image.close()
    return hashlib.sha256(raw).hexdigest()


def zip_members(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if len(set(archive.namelist())) != len(archive.namelist()): raise ValueError('Duplicate Python archive member')
        return {name:hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()}


def verify(first_runtime,second_runtime,first_setup,second_setup):
    runtime=compare_outputs(first_runtime,second_runtime)
    allowed={'cueflora-host.exe','_internal/base_library.zip','runtime-manifest.json'}
    differences=set(runtime['different']) if 'different' in runtime else set(runtime.get('differentFiles',[]))
    # compare_outputs uses the measured field names, never assume an empty fallback.
    if runtime.get('onlyFirst') or runtime.get('onlySecond') or runtime.get('onlyLeft') or runtime.get('onlyRight'):
        raise ValueError('Runtime build membership differs')
    first_files={path.relative_to(first_runtime).as_posix():digest(path) for path in first_runtime.rglob('*') if path.is_file()}
    second_files={path.relative_to(second_runtime).as_posix():digest(path) for path in second_runtime.rglob('*') if path.is_file()}
    if set(first_files)!=set(second_files): raise ValueError('Runtime build membership differs')
    differences={name for name in first_files if first_files[name]!=second_files[name]}
    if differences-allowed: raise ValueError('Unexplained runtime payload differences: '+', '.join(sorted(differences-allowed)))
    host=explain_frozen_differences(first_runtime/'cueflora-host.exe',second_runtime/'cueflora-host.exe')
    if not host['equalAfterNormalizingPeTimestampAndChecksum']: raise ValueError('Host difference is not PE timestamp/checksum only')
    library=explain_library_order(first_runtime/'_internal/base_library.zip',second_runtime/'_internal/base_library.zip')
    if library['differentEntryContents']: raise ValueError('Python standard-library payload changed')
    metadata=[]
    for root,files in ((first_runtime,first_files),(second_runtime,second_files)):
        value=json.loads((root/'runtime-manifest.json').read_text())
        for name in value['files']:
            if value['files'][name] != files.get(name): raise ValueError('Runtime manifest does not match its actual payload')
        value['files']={name:checksum for name,checksum in value['files'].items() if name not in allowed}
        metadata.append(value)
    if metadata[0]!=metadata[1]: raise ValueError('Runtime metadata changed beyond known output hashes')
    from PyInstaller.archive.readers import CArchiveReader
    left,right=CArchiveReader(str(first_setup)),CArchiveReader(str(second_setup))
    if set(left.toc)!=set(right.toc) or normalized_bootloader(first_setup)!=normalized_bootloader(second_setup):
        raise ValueError('Setup membership/bootloader differs beyond PE metadata')
    known={'base_library.zip',*[('bundle/runtime/'+name) for name in allowed],'bundle/release.json'}
    changed=[]
    for name in left.toc:
        a,b=left.extract(name),right.extract(name)
        if a==b: continue
        normalized=name.replace('\\','/'); changed.append(normalized)
        if normalized not in known: raise ValueError('Unexplained embedded Setup payload difference: '+normalized)
        if normalized.endswith('base_library.zip'):
            if zip_members(a)!=zip_members(b): raise ValueError('Embedded Python ZIP content changed')
        elif normalized=='bundle/release.json':
            first,second=json.loads(a),json.loads(b)
            if first.pop('runtimeInventorySha256')!=digest(first_runtime/'runtime-manifest.json') or second.pop('runtimeInventorySha256')!=digest(second_runtime/'runtime-manifest.json') or first!=second:
                raise ValueError('Setup release changed beyond exact runtime binding')
        else:
            relative=normalized.removeprefix('bundle/runtime/')
            if hashlib.sha256(a).hexdigest()!=first_files[relative] or hashlib.sha256(b).hexdigest()!=second_files[relative]:
                raise ValueError('Embedded runtime differs from independently checked build')
    return {'passed':True,'runtimeDifferences':sorted(differences),'setupMemberDifferences':changed,
        'hostExplanation':host,'libraryExplanation':library,'bootloadersMatchAfterMeasuredPeNormalization':True,
        'unexplainedDifferences':[],'byteIdentical':first_files==second_files and digest(first_setup)==digest(second_setup),
        'interpretation':'Only measured PE metadata, identical-content ZIP ordering and exact embedded output/binding differences are allowed.'}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('first-runtime','second-runtime','first-setup','second-setup','output'): parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    result=verify(args.first_runtime.resolve(),args.second_runtime.resolve(),args.first_setup.resolve(),args.second_setup.resolve())
    with args.output.open('x',encoding='utf-8') as stream: json.dump(result,stream,indent=2)
    print(json.dumps({'passed':result['passed'],'unexplainedDifferences':result['unexplainedDifferences']}))
