"""Check unstaged new source files without changing the Git index."""
import os
import json
import hashlib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def original_inputs(root):
    lock=json.loads((root/'packaging/inputs-windows.lock.json').read_text())
    originals={'packaging/notices/'+item['file']:item['sha256'] for item in lock['files'] if item.get('role')=='licence-source-evidence'}
    if (root/'packaging/v8-submodule-notices.lock.json').is_file():
        from v8_submodule_notices import load
        _,_,sources,_=load(root)
        for path in sources.values(): originals[path.relative_to(root).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    if (root/'packaging/cargo-standard-terms.lock.json').is_file():
        from cargo_declarations import standard_terms
        for item,path in standard_terms(root).values(): originals[path.relative_to(root).as_posix()]=item['sha256']
    return originals


def check_export(root):
    from source_export import inventory
    records,issues=inventory(root)
    if issues: raise ValueError('Source export has unresolved path/reason flags')
    originals=original_inputs(root)
    for name in records:
        path=root/name
        if name in originals:
            if hashlib.sha256(path.read_bytes()).hexdigest()!=originals[name]: raise ValueError('Upstream notice differs from pinned original: '+name)
            continue  # Licence bytes are retained verbatim, including original whitespace.
        if path.suffix in ('.png','.ico'): continue
        try: lines=path.read_text(encoding='utf-8').splitlines()
        except UnicodeDecodeError: continue
        if any(line.rstrip(' \t') != line for line in lines): raise ValueError('Trailing source whitespace: '+name)


def check():
    if not (ROOT/'.git').exists():
        check_export(ROOT)
        return
    names = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode('utf-8').split('\0')
    originals=original_inputs(ROOT)
    for name in filter(None, names):
        if name in originals:
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=originals[name]: raise ValueError('Original notice bytes changed')
            continue
        result = subprocess.run(['git', '-c', 'core.safecrlf=false', 'diff', '--no-index', '--check', '--', os.devnull, name],
                                cwd=ROOT, capture_output=True, text=True)
        # --no-index returns 1 for different files even when whitespace is valid.
        if result.returncode not in (0, 1) or result.stdout.strip() or result.stderr.strip():
            print(result.stdout + result.stderr)
            return 1
    print('New source whitespace: PASS (index unchanged)')
    return 0


if __name__ == '__main__':
    raise SystemExit(check())
