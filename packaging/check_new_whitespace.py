"""Check unstaged new source files without changing the Git index."""
import os
import json
import hashlib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def check_export(root):
    from source_export import inventory
    records,issues=inventory(root)
    if issues: raise ValueError('Source export has unresolved path/reason flags')
    lock=json.loads((root/'packaging/inputs-windows.lock.json').read_text())
    originals={'packaging/notices/'+item['file']:item['sha256'] for item in lock['files'] if item.get('role')=='licence-source-evidence'}
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
    for name in filter(None, names):
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
