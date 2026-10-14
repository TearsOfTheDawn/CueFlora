"""Compile twice at the same visible path; preserve both results and explain bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import pefile
from audio_build import build,digest,ROOT,INPUT_LOCK,TOOLCHAIN_LOCK


def normalized_pe(path):
    raw=bytearray(path.read_bytes()); image=pefile.PE(data=bytes(raw)); fields=[]
    structures=[('COFF.TimeDateStamp',image.FILE_HEADER,'TimeDateStamp'),('OPTIONAL.CheckSum',image.OPTIONAL_HEADER,'CheckSum')]
    if hasattr(image,'DIRECTORY_ENTRY_EXPORT'): structures.append(('EXPORT.TimeDateStamp',image.DIRECTORY_ENTRY_EXPORT.struct,'TimeDateStamp'))
    for index,entry in enumerate(getattr(image,'DIRECTORY_ENTRY_DEBUG',[])):
        structures.append(('DEBUG.'+str(index)+'.TimeDateStamp',entry.struct,'TimeDateStamp'))
    for name,structure,field in structures:
        offset=structure.get_field_absolute_offset(field)
        fields.append({'field':name,'offset':offset,'value':getattr(structure,field)})
        raw[offset:offset+4]=b'\0'*4
    image.close()
    return hashlib.sha256(raw).hexdigest(),fields


def compare(first,second):
    from verify_audio_conformance import validate_recipe
    manifests=[validate_recipe(folder) for folder in (first,second)]
    a,b=manifests
    for field in ('inputLockSha256','toolchainLockSha256','configureOpus','configureFFmpeg'):
        if a.get(field)!=b.get(field): raise ValueError('Controlled rebuild changed an effective input: '+field)
    if set(a['files'])!=set(b['files']): raise ValueError('Controlled rebuild changed file membership')
    rows=[]
    for name in sorted(a['files']):
        paths=[folder/'install/bin'/name for folder in (first,second)]
        for manifest,path in zip(manifests,paths):
            if digest(path)!=manifest['files'][name]: raise ValueError('Changed rebuild artifact')
        normalized=[normalized_pe(path) for path in paths]
        identical=a['files'][name]==b['files'][name]
        rows.append({'file':name,'sha256':[a['files'][name],b['files'][name]],'byteIdentical':identical,
            'normalizedSha256':[item[0] for item in normalized],'measuredMetadata':[item[1] for item in normalized],
            'onlyMeasuredPeMetadataDifferent':normalized[0][0]==normalized[1][0],
            'unexplainedDifference':normalized[0][0]!=normalized[1][0]})
    unresolved=[row['file'] for row in rows if row['unexplainedDifference']]
    return {'schema':1,'sameEffectiveCommands':True,'files':rows,'unexplainedFiles':unresolved,'passed':not unresolved,
        'byteIdentical':all(row['byteIdentical'] for row in rows),
        'scope':'Same visible build root and exact source/compiler inputs. Only measured COFF/export/debug timestamps and PE checksum are normalized; other differences fail.'}


def preserve_working(working,target,root):
    root=root.resolve(); working=working.resolve(); target=target.resolve()
    if working!=root/'working' or target not in (root/'first',root/'second') or working.is_symlink() or not working.is_dir() or target.exists():
        raise ValueError('Unsafe or occupied controlled-build preservation path')
    # Own fresh experiment only. Never rename prior packages or workspace roots.
    working.rename(target)


def verify(cache,toolchain,output):
    output=output.resolve()
    if output.exists(): raise ValueError('Fresh audio rebuild experiment required')
    output.mkdir(parents=True); working=output/'working'
    report={'schema':1,'passed':False,'sourceInputLockSha256':digest(INPUT_LOCK),'compilerLockSha256':digest(TOOLCHAIN_LOCK),
        'audioBuilderSha256':digest(ROOT/'packaging/audio_build.py'),'sameVisibleBuildRoot':str(working),
        'inference':False,'liveInstallation':False,'steps':[]}
    status=output/'audio-rebuild-status.json'
    def save(): status.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    save()
    try:
        for name in ('first','second'):
            print(name+' audio compilation started',flush=True)
            build(cache,toolchain,working)
            preserve_working(working,output/name,output)
            report['steps'].append({'build':name,'preserved':True}); save()
            print(name+' audio compilation preserved',flush=True)
        if report['audioBuilderSha256']!=digest(ROOT/'packaging/audio_build.py') or report['sourceInputLockSha256']!=digest(INPUT_LOCK) or report['compilerLockSha256']!=digest(TOOLCHAIN_LOCK):
            raise ValueError('Source/compiler recipe changed during controlled rebuild')
        result=compare(output/'first',output/'second')
        (output/'audio-rebuild-comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        report['passed']=result['passed']; report['unexplainedFiles']=result['unexplainedFiles']; save()
        if not result['passed']: raise ValueError('Unexplained controlled audio rebuild payload differences')
        print('Controlled audio rebuild explained; no inference or adoption performed',flush=True)
        return result
    except Exception as error:
        report['failure']=str(error); save(); raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('cache','toolchain','output'): parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args(); verify(args.cache.resolve(),args.toolchain.resolve(),args.output.resolve())
