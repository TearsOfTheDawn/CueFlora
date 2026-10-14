"""Build the on-demand Setup app. Never run/install it as part of a build."""
import argparse
from pathlib import Path
import subprocess
import sys
import tkinter
from runtime_notices import collect_interpreter_notices
from build_isolation import environment, native_inputs
import json

ROOT = Path(__file__).resolve().parents[1]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error('Choose a fresh output directory')
    output.mkdir(parents=True)
    # A successful PyInstaller exit can otherwise silently exclude a broken Tk.
    tkinter.Tcl().eval('info library')
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--onedir', '--noupx',
                    '--name', 'CueFlora Setup', '--paths', str(ROOT / 'native'),
                    '--paths', str(Path(tkinter.__file__).parent.parent), '--hidden-import', 'tkinter',
                    '--distpath', str(output / 'dist'), '--workpath', str(output / 'work'),
                    '--specpath', str(output), str(ROOT / 'packaging/setup_entry.py')], check=True, env=environment())
    (output/'native-input-isolation.json').write_text(json.dumps({'inheritedPathUsed':False,
        'inputs':native_inputs(output/'work/CueFlora Setup/Analysis-00.toc')},indent=2)+'\n',encoding='utf-8')
    collect_interpreter_notices(output / 'dist' / 'CueFlora Setup')
