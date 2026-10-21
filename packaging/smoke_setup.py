"""Exercise actual payload installation in a disposable root, with fake registration.

No browser/profile/registry is modified. All generated files are retained as evidence.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'native'))
from cueflora_setup.engine import Setup
from cueflora_setup.test_setup import FakeRegistration
from cueflora_setup.test_maintenance import FakeMaintenance
from probe_runtime import probe


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--payload', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--release', type=Path, help='Use actual private configuration without prototype overrides')
    parser.add_argument('--launcher', type=Path, help='Retain the actual Setup with simulated Start Menu writes')
    parser.add_argument('--extension',type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error('Choose a fresh evidence directory')
    output.mkdir(parents=True)
    # Fixture identities are exclusively used with the in-memory adapter.
    release = {'owner': 'Local fake-registration smoke test',
               'extensionIds': {'chrome': 'a'*32, 'firefox': 'test@example.invalid'}}
    if args.release:
        release = json.loads(args.release.read_text(encoding='utf-8'))
    browsers = list(release['extensionIds'])
    options = {} if args.release else {'allow_prototype': True}
    if args.extension:options['extension']=args.extension
    setup = Setup(output / 'spaces and Ω' / 'CueFlora', output, registration=FakeRegistration(),maintenance=FakeMaintenance(output,'Windows'))
    first = setup.install(args.payload, release, browsers, launcher=args.launcher, **options)
    executable_name = 'cueflora-host.exe' if sys.platform == 'win32' else 'cueflora-host'
    first_ping = probe(setup._version(first['current']) / executable_name, repeats=3)
    upgraded = setup.install(args.payload, release, browsers, launcher=args.launcher, **options)
    rolled = setup.rollback()
    assert rolled['current'] == first['current']
    if args.launcher:
        assert rolled['maintenance'] == first['maintenance']
    repaired = setup.repair(args.payload, **options)
    repaired_ping = probe(setup._version(repaired['current']) / executable_name, repeats=1)
    recovery_path = setup.uninstall()
    if args.launcher:
        assert not setup.maintenance.path.exists()
    report = {'install': first['current'], 'upgrade': upgraded['current'], 'rollback': rolled['current'],
              'repair': repaired['current'], 'uninstallRecoveryPath': str(recovery_path),
              'firstPing': first_ping, 'repairedPing': repaired_ping,
              'prototypeOverride': not bool(args.release),
              'maintenanceLauncherRetained':bool(args.launcher), 'startMenuAdapterSimulated':True,
              'realBrowserRegistration': False, 'cleanMachine': False}
    (output / 'smoke-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
