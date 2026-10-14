"""Collect available interpreter notices; report missing evidence explicitly."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tkinter


def collect_interpreter_notices(bundle):
    destination = Path(bundle) / 'licenses' / 'interpreter'
    destination.mkdir(parents=True, exist_ok=True)
    base = Path(sys.base_prefix)
    candidates = {'Python': [base / 'LICENSE.txt', base / 'LICENSE'],
                  'Tcl': list((base / 'tcl').glob('tcl*/license.terms')),
                  'Tk': list((base / 'tcl').glob('tk*/license.terms'))}
    records = []
    for component, paths in candidates.items():
        source = next((path for path in paths if path.is_file()), None)
        provenance = 'interpreter installation'
        if component == 'Tcl' and source is None and base == Path(sys.base_prefix):
            fallback = Path(__file__).parent / 'notices/Tcl-8.6.12-license.terms'
            try:
                interpreter = tkinter.Tcl()
                if Path(interpreter.eval('info library')).is_relative_to(base) and interpreter.eval('info patchlevel') == '8.6.12' and fallback.is_file():
                    source = fallback
                    provenance = 'official core-8-6-12 notice; not a complete binary provenance proof'
            except tkinter.TclError:
                pass
        record = {'component': component, 'noticeFound': source is not None,
                  'redistributionApproved': False, 'provenance': provenance}
        if source:
            target = destination / (component + '-LICENSE.txt')
            shutil.copy2(source, target)
            record.update({'file': target.relative_to(bundle).as_posix(),
                           'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
        records.append(record)
    (destination / 'notice-inventory.json').write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')
