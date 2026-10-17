"""Original fixed-commit notices for V8 dependencies; no inferred binary closure."""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from release_inputs import ROOT, digest

DEPENDENCIES = {'dragonbox':'dragonbox/src','fast_float':'fast_float/src','simdutf':'simdutf',
    'abseil-cpp':'abseil-cpp','zlib':'zlib','perfetto':'perfetto','protobuf':'protobuf',
    'libcplusplus':'libc++/src','libcplusplusabi':'libc++abi/src','libunwind':'libunwind/src'}


def notice_name(name):
    return isinstance(name,str) and re.fullmatch(r'(?:LICEN[CS]E|COPYING|NOTICE|COPYRIGHT)(?:[-_.][A-Za-z0-9_-]+)*',name,re.I) is not None and name.rsplit('.',1)[-1].lower() not in {'c','cc','cpp','h','hpp','rs','py','js'}


def original(path, expected):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>1024*1024 or digest(path)!=expected:
        raise ValueError('Missing/changed original V8 submodule evidence')
    return path.read_bytes()


def load(root=ROOT, deps=None):
    root=Path(root); lock_path=root/'packaging/v8-submodule-notices.lock.json'
    lock=json.loads(lock_path.read_text(encoding='utf-8'))
    if lock.get('schema')!=1 or lock.get('denoVersion')!='2.9.7' or lock.get('v8Commit')!='ac1e23989121713ca642f6650b34deff7b686896' or not re.fullmatch('[0-9a-f]{64}',str(lock.get('depsSha256',''))) or not isinstance(lock.get('trees'),list) or not isinstance(lock.get('notices'),list):
        raise ValueError('Exact V8 submodule notice lock required')
    if deps is not None and hashlib.sha256(deps).hexdigest()!=lock['depsSha256']:
        raise ValueError('V8 dependency source changed')
    trees={}; sources={lock_path.name:lock_path}; contents={}; origins={}
    for tree in lock['trees']:
        component=tree.get('component'); filename=tree.get('file',''); repository=tree.get('repository',''); commit=tree.get('commit','')
        if component not in DEPENDENCIES or component in trees or filename!='V8-submodule-'+component+'-tree.json' or not re.fullmatch('[0-9a-f]{40}',commit):
            raise ValueError('Invalid/duplicate V8 submodule origin')
        parsed=urlsplit(repository)
        if parsed.scheme!='https' or parsed.netloc!='chromium.googlesource.com' or parsed.query or parsed.fragment or not re.fullmatch('/[A-Za-z0-9_./+-]+',parsed.path) or '..' in parsed.path.split('/'):
            raise ValueError('Unsafe V8 submodule repository')
        base=repository+'/+/'+commit+'/'
        if tree.get('url')!=base+'?format=JSON': raise ValueError('Submodule tree URL mismatch')
        path=root/'packaging/source-metadata'/filename
        raw=original(path,tree.get('sha256'))
        if not raw.startswith(b")]}'\n"): raise ValueError('Invalid original Gitiles tree')
        entries=json.loads(raw[5:]).get('entries')
        if not isinstance(entries,list): raise ValueError('Missing original Gitiles entries')
        if deps is not None:
            pattern=r"'third_party/"+re.escape(DEPENDENCIES[component])+r"':\s*(?:\{\s*'url':\s*)?Var\('chromium_url'\)\s*\+\s*'([^']+)'\s*\+\s*'@'\s*\+\s*'([0-9a-f]{40})'"
            found=re.search(pattern,deps.decode('utf-8'))
            if not found or 'https://chromium.googlesource.com'+found[1]!=repository or found[2]!=commit:
                raise ValueError('Submodule commit does not match V8 DEPS')
        trees[component]=(tree,entries,base); sources[filename]=path
    if set(trees)!=set(DEPENDENCIES): raise ValueError('Missing V8 submodule origins')
    for item in lock['notices']:
        component=item.get('component'); entry=item.get('sourceEntry'); filename=item.get('file','')
        if component not in trees or not notice_name(entry) or filename!='V8-submodule-'+component+'-'+entry+'.txt' or filename in contents:
            raise ValueError('Unsafe/duplicate V8 notice file')
        tree,entries,base=trees[component]
        if item.get('url')!=base+entry+'?format=TEXT': raise ValueError('V8 notice URL mismatch')
        original_entry=[row for row in entries if row.get('name')==entry and row.get('type')=='blob']
        path=root/'packaging/source-metadata'/filename; raw=original(path,item.get('sha256'))
        blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        if len(original_entry)!=1 or original_entry[0].get('id')!=blob or item.get('gitBlobSha')!=blob or type(item.get('bytes')) is not int or item['bytes']!=len(raw):
            raise ValueError('Original V8 notice blob/size mismatch')
        raw.decode('utf-8'); contents[filename]=raw; sources[filename]=path
        origins[filename]={**item,'sourceArchive':'v8-submodule-notices.lock.json',
            'scope':'Original fixed V8 dependency notice; conservative source scope, not a binary inclusion declaration'}
    if not contents or {item['component'] for item in lock['notices']}!=set(trees):
        raise ValueError('Missing V8 submodule notice coverage')
    evidence={'lockSha256':digest(lock_path),'depsSha256':lock['depsSha256'],'v8Commit':lock['v8Commit'],
        'selectedOrigins':len(trees),'originalNoticeCount':len(contents),'allSelectedOriginsVerified':True,
        'noticeFiles':{name:hashlib.sha256(raw).hexdigest() for name,raw in contents.items()}}
    return contents,origins,sources,evidence


def validate_collected(evidence, notices):
    _,_,_,expected=load()
    if evidence!=expected or any(notices.get(name)!=checksum for name,checksum in expected['noticeFiles'].items()):
        raise ValueError('V8 submodule notice evidence binding mismatch')
    return expected
