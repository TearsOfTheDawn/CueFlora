"""Read bounded JSON inventories from CueFlora's pinned onefile format, without execution.

This is not a generic extractor or a PyInstaller runtime dependency. Only four
known data members are decompressed; code, paths and archive instructions never run.
"""
import base64
import hashlib
import json
from pathlib import Path
import struct
import zlib

COOKIE=struct.Struct('!8sIIII64s')
ENTRY=struct.Struct('!IIIIBc')
MAGIC=b'MEI\x0c\x0b\x0a\x0b\x0e'
LIMITS={'bundle/release.json':65536,'bundle/runtime/runtime-manifest.json':16*1024*1024,
        'bundle/extension/cueflora-extension.json':1024*1024,'bundle/extension/manifest.json':65536}


def inventories(executable):
    path=Path(executable);size=path.stat().st_size
    if size<COOKIE.size+512:raise ValueError('Not a CueFlora onefile Setup')
    with path.open('rb') as stream:
        if stream.read(2)!=b'MZ':raise ValueError('Setup is not a Windows executable')
        stream.seek(-COOKIE.size,2);footer=stream.read(COOKIE.size)
        magic,length,toc_offset,toc_length,python_version,library=COOKIE.unpack(footer)
        start=size-length
        if magic!=MAGIC or start<512 or length>size or not 0<toc_length<=4*1024*1024 or toc_offset+toc_length!=length-COOKIE.size or not library.rstrip(b'\0'):
            raise ValueError('Unsupported or malformed CueFlora Setup footer')
        stream.seek(start+toc_offset);toc=stream.read(toc_length)
        if len(toc)!=toc_length:raise ValueError('Truncated Setup inventory')
        position=0;found={};seen=set()
        while position<len(toc):
            if len(toc)-position<ENTRY.size:raise ValueError('Truncated Setup entry')
            entry_length,offset,packed,unpacked,compressed,kind=ENTRY.unpack_from(toc,position)
            if not ENTRY.size<entry_length<=8192 or position+entry_length>len(toc) or offset+packed>toc_offset or compressed not in (0,1):raise ValueError('Unsafe Setup entry bounds')
            raw_name=toc[position+ENTRY.size:position+entry_length].rstrip(b'\0')
            if b'\0' in raw_name:raise ValueError('Invalid Setup member name')
            name=raw_name.decode('utf-8').replace('\\','/');position+=entry_length
            if kind==b'o':continue
            if name in seen:raise ValueError('Duplicate Setup member')
            seen.add(name)
            if name not in LIMITS:continue
            limit=LIMITS[name]
            if packed>limit or not 0<unpacked<=limit:raise ValueError('Oversized Setup inventory member')
            stream.seek(start+offset);data=stream.read(packed)
            if len(data)!=packed:raise ValueError('Truncated Setup member')
            if compressed:
                decoder=zlib.decompressobj();data=decoder.decompress(data,limit+1)
                if not decoder.eof or decoder.unconsumed_tail or decoder.unused_data:raise ValueError('Invalid bounded Setup compression')
            if len(data)!=unpacked:raise ValueError('Setup member size mismatch')
            found[name]=data
        if set(found)!=set(LIMITS):raise ValueError('Setup has no complete managed extension/helper pair')
        return found


def verify_update_payload(executable,manifest):
    raw=inventories(executable)
    release=json.loads(raw['bundle/release.json']);runtime=json.loads(raw['bundle/runtime/runtime-manifest.json'])
    extension=json.loads(raw['bundle/extension/cueflora-extension.json']);chrome=json.loads(raw['bundle/extension/manifest.json'])
    for name,field in [('bundle/runtime/runtime-manifest.json','runtimeInventorySha256'),('bundle/extension/cueflora-extension.json','extensionInventorySha256')]:
        checksum=hashlib.sha256(raw[name]).hexdigest()
        if checksum!=manifest[field] or release.get(field)!=checksum:raise ValueError('Setup payload differs from the frozen update binding')
    if release.get('product')!='cueflora' or release.get('mode')!='public' or release.get('distribution')!='github' or release.get('repositoryUrl')!='https://github.com/TearsOfTheDawn/CueFlora' or release.get('extensionIds')!={'chrome':manifest['chromeId']}:
        raise ValueError('Setup release identity mismatch')
    if runtime.get('product')!='cueflora' or runtime.get('platform')!='Windows' or str(runtime.get('architecture','')).lower() not in ('amd64','x86_64') or runtime.get('transportPolicy')!='https-remote':raise ValueError('Setup runtime platform/transport mismatch')
    if runtime.get('hostVersion')!=manifest['version'] or extension.get('version')!=manifest['version'] or chrome.get('version')!=manifest['version']:raise ValueError('Setup pair version mismatch')
    if runtime.get('sourceInventorySha256')!=manifest['sourceInventorySha256'] or release.get('sourceInventorySha256')!=manifest['sourceInventorySha256']:raise ValueError('Setup source binding mismatch')
    key=base64.b64decode(chrome.get('key',''),validate=True)
    chrome_id=''.join(chr(97+int(char,16)) for char in hashlib.sha256(key).hexdigest()[:32])
    if not key or chrome_id!=manifest['chromeId'] or extension.get('chromeId')!=chrome_id or extension.get('product')!='cueflora':raise ValueError('Setup extension identity mismatch')
    if extension.get('files',{}).get('manifest.json')!=hashlib.sha256(raw['bundle/extension/manifest.json']).hexdigest():raise ValueError('Setup Chrome manifest inventory mismatch')
    return {'payloadBindingsVerified':True,'executed':False}
