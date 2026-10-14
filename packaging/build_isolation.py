"""Keep PyInstaller DLL discovery inside the reviewed interpreter inputs."""
import ast
import json
import os
from pathlib import Path
import sys
from release_inputs import ROOT, digest


def environment(original=None, interpreter=None):
    # Windows environment names are case-insensitive; dict(os.environ) exposes
    # uppercase names even when callers used SystemRoot/Path spellings.
    result = {key.upper():value for key,value in (os.environ if original is None else original).items()}
    interpreter = Path(interpreter or sys.base_prefix).resolve()
    system = Path(result['SYSTEMROOT']).resolve() / 'System32'
    result['PATH'] = os.pathsep.join(map(str, [interpreter, interpreter/'DLLs', system]))
    for key in ('PYTHONPATH', 'PYTHONHOME', 'LD_LIBRARY_PATH', 'DYLD_LIBRARY_PATH'):
        result.pop(key, None)
    return result


def native_inputs(analysis, lock=None, payload=None):
    lock = lock or json.loads((ROOT/'packaging/inputs-windows.lock.json').read_text())
    known = {item['sha256']:item['file'] for item in lock['interpreterFiles']}
    rows = []
    def walk(value):
        if not isinstance(value, (list, tuple)): return
        if len(value) == 3 and isinstance(value[0],str) and value[0].lower().endswith(('.dll','.pyd')) and value[2] in ('BINARY','EXTENSION'):
            checksum = digest(value[1])
            runtime_file = None
            if payload is not None:
                root, inventory = payload
                source = Path(value[1]).resolve()
                root = Path(root).resolve()
                if source.is_relative_to(root):
                    candidate = source.relative_to(root).as_posix()
                    if inventory.get(candidate) == checksum: runtime_file = candidate
            if checksum not in known and runtime_file is None:
                raise ValueError('Unpinned native dependency collected: '+Path(value[0]).name)
            rows.append({'name':value[0].replace('\\','/'),'sha256':checksum,'lockedInterpreterFile':known.get(checksum),
                'lockedRuntimeFile':runtime_file})
        else:
            for child in value: walk(child)
    walk(ast.literal_eval(Path(analysis).read_text(encoding='utf-8')))
    if not rows: raise ValueError('Native dependency analysis missing')
    return rows
