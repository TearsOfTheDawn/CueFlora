"""Assemble a local Setup/runtime ZIP and checksums; never publish it."""
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'native'))
from cueflora_setup.bundle import digest, verify_bundle
from cueflora_setup.manifests import validate_release
from verify_archive import verify_archive


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--setup', type=Path, required=True)
    parser.add_argument('--release', type=Path)
    parser.add_argument('--private-chrome-id', help='Build a private Windows package for this actual Chrome identity')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    runtime = verify_bundle(args.runtime)
    output = args.output.resolve()
    if output.exists():
        parser.error('Choose a fresh output directory')
    setup_exe = args.setup / ('CueFlora Setup.exe' if sys.platform == 'win32' else 'CueFlora Setup')
    if not setup_exe.is_file():
        parser.error('Compiled Setup executable is missing')
    release = validate_release(json.loads(args.release.read_text(encoding='utf-8'))) if args.release else None
    if args.private_chrome_id:
        if args.release or runtime['platform'] != 'Windows' or runtime['architecture'].lower() not in ('amd64', 'x86_64'):
            parser.error('Private Chrome assembly requires Windows x64 and no --release argument')
        release = validate_release({'owner': 'Private local installation', 'mode': 'private',
            'extensionIds': {'chrome': args.private_chrome_id},
            'runtimeInventorySha256': digest(args.runtime / 'runtime-manifest.json'),
            'publicReleaseAuthorized': False, 'redistributionApproved': False})
    output.mkdir(parents=True)
    contents = output / 'CueFlora Setup'
    shutil.copytree(args.setup, contents)
    shutil.copytree(args.runtime, contents / 'runtime')
    if release:
        (contents / 'release.json').write_text(json.dumps(release, indent=2), encoding='utf-8')
    notice = ('LOCAL PROTOTYPE - NOT A CERTIFIED RELEASE\n'
              'No live browser registration has been validated for this package.\n'
              'Normal GUI installation rejects prototype runtimes.\n'
              'Final release identities, licenses, signing and clean-system checks remain required.\n'
              'See DISTRIBUTION.md for manual commands and limitations.\n')
    (contents / 'READ-ME-FIRST.txt').write_text(notice, encoding='utf-8')
    if args.private_chrome_id:
        (contents / 'READ-ME-FIRST.txt').write_text(
            'PRIVATE WINDOWS CHROME INSTALLATION - UNSIGNED\n'
            'Extract this entire ZIP; keep the executable, _internal and runtime together.\n'
            'Open CueFlora Setup.exe, select Chrome, and choose Install / Upgrade.\n'
            'Close Setup afterward; it is not needed for normal operation.\n'
            'Repair uses this package runtime; rollback restores the previous installed runtime.\n'
            'Uninstall unregisters the host and quarantines runtime files for recovery.\n'
            'Browser settings and evidence are preserved. No AI services are installed.\n'
            'Existing foreign native registration is refused, never overwritten.\n'
            'Real-browser and clean-machine acceptance are deferred; no public distribution approval.\n'
            'Chrome extension ID: ' + args.private_chrome_id + '\n', encoding='utf-8')
    shutil.copy2(ROOT / 'docs/DISTRIBUTION.md', contents / 'DISTRIBUTION.md')
    shutil.copy2(ROOT / 'docs/REDISTRIBUTION_CHECKLIST.md', contents / 'REDISTRIBUTION_CHECKLIST.md')
    shutil.copy2(ROOT / 'docs/STAGE6_MANUAL_ACCEPTANCE.md', contents / 'STAGE6_MANUAL_ACCEPTANCE.md')
    if args.private_chrome_id:
        shutil.copy2(ROOT / 'docs/PRIVATE_WINDOWS_INSTALLATION.md', contents / 'PRIVATE_WINDOWS_INSTALLATION.md')
    shutil.copy2(ROOT / 'packaging/release.template.json', contents / 'release.template.json')
    shutil.copy2(ROOT / 'packaging/requirements-windows.lock', contents / 'prototype-build-requirements.txt')
    hashes = {p.relative_to(contents).as_posix(): digest(p) for p in sorted(contents.rglob('*')) if p.is_file()}
    (contents / 'SHA256SUMS.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')
    name = 'CueFlora-Setup-private-Windows-x64-Chrome' if args.private_chrome_id else 'CueFlora-Setup-prototype'
    archive = Path(shutil.make_archive(str(output / name), 'zip', output, contents.name))
    verification = verify_archive(archive)
    report = {'prototype': not bool(args.private_chrome_id), 'runtimePrototype': runtime.get('prototype'),
              'archive': archive.name, 'sha256': digest(archive), 'bytes': archive.stat().st_size,
              'runtimePlatform': runtime['platform'], 'releaseIdentitiesProvided': release is not None,
              'mode': 'private' if args.private_chrome_id else 'prototype',
              'publicReleaseAuthorized': False, 'archiveVerification': verification}
    (output / 'artifact-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
