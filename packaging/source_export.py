"""Reviewable source-only export from actual files, independent of Git history."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = ('.agents', '.github', 'docs', 'entrypoints', 'native', 'packaging', 'public', 'scripts', 'utils')
ROOT_FILES = ('AGENTS.md','LICENSE.md','README.md','CHANGELOG.md','.gitignore','.gitattributes','package.json','package-lock.json',
    'wxt.config.ts','tsconfig.json','vitest.config.ts','product.json','preview-identity.json')
SKIP_DIRS = {'__pycache__','.venv','.packaging-venv','node_modules','.git','testdata','artifacts','build','dist','.output','.wxt'}
SKIP_FILES = {'SOURCE_COPY_BASELINE.json'}
BANNED_SUFFIXES = {'.exe','.dll','.pyd','.pyc','.pyo','.wav','.mp3','.m4a','.ogg','.opus','.webm','.mp4','.log'}
SECRET_PATTERN = re.compile(r'(?:sk-[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AIza[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
TEXT_SUFFIXES = {'.md','.json','.ts','.mjs','.mts','.py','.sh','.ps1','.css','.html','.svg','.txt','.terms','.lock','.yml','.yaml'}


def source_identity(records):
    return hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def inventory(root=ROOT):
    root = Path(root).resolve()
    candidates = [root/name for name in ROOT_FILES if (root/name).is_file()]
    for directory in DIRECTORIES:
        folder = root/directory
        if folder.is_dir(): candidates.extend(path for path in folder.rglob('*') if path.is_file())
    records = {}
    issues = []
    for path in sorted(set(candidates)):
        relative = path.relative_to(root)
        if any(part in SKIP_DIRS for part in relative.parts) or path.name in SKIP_FILES: continue
        if path.name.startswith('.env') or path.name.endswith(('.private.json','.bak','.backup')) or re.search(r'_old\d*\.py$',path.name):
            issues.append({'path':relative.as_posix(),'reason':'private-or-backup-file'}); continue
        if path.is_symlink() or path.resolve() != path:
            issues.append({'path':relative.as_posix(),'reason':'linked-source-path'}); continue
        if path.suffix.lower() in BANNED_SUFFIXES:
            issues.append({'path':relative.as_posix(),'reason':'binary-media-or-generated-file'}); continue
        if path.stat().st_size > 8*1024*1024:
            issues.append({'path':relative.as_posix(),'reason':'unexpected-large-source-file'}); continue
        content = path.read_bytes()
        if path.suffix.lower() in TEXT_SUFFIXES or path.name.startswith('.'):
            text = content.decode('utf-8')
            if SECRET_PATTERN.search(text): issues.append({'path':relative.as_posix(),'reason':'possible-secret'})
            if re.search(r'C:[/\\]Users[/\\]',text,re.I):
                issues.append({'path':relative.as_posix(),'reason':'private-user-path'})
        records[relative.as_posix()] = hashlib.sha256(content).hexdigest()
    if not records or 'LICENSE.md' not in records: raise ValueError('Incomplete source export')
    return records, issues


def export(output, root=ROOT):
    records, issues = inventory(root)
    output = Path(output).resolve()
    if output.exists(): raise ValueError('Fresh source-export directory required')
    output.mkdir(parents=True)
    report = {'schema':1,'files':records,'sourceInventorySha256':source_identity(records),'issues':issues,'passed':not issues,
        'scope':'Allowlisted actual source files; pattern checks are not exhaustive secrets/security clearance.',
        'developmentKey':'preview-identity.json contains a public development key, not a private signing key.',
        'published':False}
    (output/'source-audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if issues: raise ValueError('Source export blocked; inspect path/reason-only source-audit.json')
    archive = output/'CueFlora-source.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as package:
        for name in records:
            entry = zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = (0o100755 if name.endswith('.sh') else 0o100644) << 16
            package.writestr(entry,(Path(root)/name).read_bytes())
    with zipfile.ZipFile(archive) as package:
        actual = {name:hashlib.sha256(package.read(name)).hexdigest() for name in package.namelist()}
        if actual != records or len(package.namelist()) != len(records): raise ValueError('Independent source-archive verification failed')
    report['archiveSha256'] = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output/'source-audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'files':len(records),'archive':str(archive),'sha256':report['archiveSha256']}))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    export(args.output)
