"""CueFlora Setup command-line/manual equivalent. Mutations require --apply."""
import argparse
import json
import sys
from pathlib import Path
from .detection import detected_browsers
from .engine import Setup
from .distribution import distribution_root
from .bundle import verify_bundle
from .package_policy import validate_package
from .terms import TERMS,requires_acceptance


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['detect', 'status', 'self-check', 'validate-package', 'terms', 'install', 'repair', 'rollback', 'uninstall'])
    parser.add_argument('--payload', type=Path)
    parser.add_argument('--release', type=Path)
    parser.add_argument('--extension',type=Path)
    parser.add_argument('--adopt-extension',type=Path,help='Exact currently loaded CueFlora extension folder, never a Chrome profile')
    parser.add_argument('--confirm-adoption',action='store_true',help='Explicitly permit validated extension-folder adoption with recoverable backup')
    parser.add_argument('--browser', action='append', choices=['chrome', 'firefox'], default=[])
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--report', type=Path, help='Write JSON without requiring a console')
    parser.add_argument('--allow-prototype', action='store_true', help='Developer test only; not release certification')
    parser.add_argument('--accept-third-party-terms',action='store_true',help='Acknowledge bundled third-party terms for install/repair; use terms to read them')
    args = parser.parse_args(argv)
    if requires_acceptance(args.action,args.apply) and not args.accept_third_party_terms:
        parser.error('Install/repair requires --accept-third-party-terms; read terms first. No installation was attempted.')
    setup = Setup()
    if args.action == 'terms':
        result={'terms':TERMS,'applied':False}
    elif args.action == 'self-check':
        import tkinter
        interpreter = tkinter.Tcl()  # No window or browser is created.
        result = {'tclVersion': interpreter.eval('info patchlevel'), 'guiOpened': False,
                  'browserRegistrationVerified': False}
    elif args.action == 'validate-package':
        root = distribution_root()
        payload = args.payload or root / 'runtime'
        release = json.loads((args.release or root / 'release.json').read_text(encoding='utf-8'))
        metadata = verify_bundle(payload)
        validate_package(payload, release, metadata, list(release['extensionIds']))
        result = {'valid': True, 'release': release, 'inventory': metadata, 'liveRegistration': False}
        if release.get('extensionInventorySha256'):
            from .extension_pair import verify_extension
            result['extensionInventory']=verify_extension(args.extension or root/'extension',release['extensionInventorySha256'])[0]
    elif args.action == 'detect':
        result = {'detected': detected_browsers(), 'certified': False}
    elif args.action == 'status':
        result = setup.state()
    elif not args.apply:
        result = {'action': args.action, 'installRoot': str(setup.root), 'browsers': args.browser,
                  'applied': False, 'instruction': 'Review arguments and add --apply to change installation.'}
    elif args.action == 'install':
        if getattr(sys, 'frozen', False):
            args.payload = args.payload or distribution_root() / 'runtime'
            args.release = args.release or distribution_root() / 'release.json'
        if not args.payload or not args.release or not args.browser:
            parser.error('install requires --payload, --release and explicit --browser')
        if set(args.browser) - set(detected_browsers()):
            parser.error('Only supported detected browsers can be registered')
        release = json.loads(args.release.read_text(encoding='utf-8'))
        extension=args.extension or (distribution_root()/'extension' if getattr(sys,'frozen',False) and release.get('extensionInventorySha256') else None)
        result = setup.install(args.payload, release, args.browser, allow_prototype=args.allow_prototype,
                               launcher=Path(sys.executable) if getattr(sys, 'frozen', False) else None,
                               extension=extension,adopt_extension=args.adopt_extension,confirm_adoption=args.confirm_adoption)
    elif args.action == 'repair':
        if getattr(sys, 'frozen', False):
            args.payload = args.payload or distribution_root() / 'runtime'
        if not args.payload:
            parser.error('repair requires --payload')
        result = setup.repair(args.payload, allow_prototype=args.allow_prototype,
                              launcher=Path(sys.executable) if getattr(sys, 'frozen', False) else None,
                              extension=args.extension or (distribution_root()/'extension' if (distribution_root()/'extension').is_dir() else None))
    elif args.action == 'rollback':
        result = setup.rollback()
    else:
        result = {'removedTo': str(setup.uninstall()), 'recoverable': True, 'settingsAndEvidencePreserved': True}
    if args.report:
        with args.report.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2)
    if sys.stdout is not None:
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
