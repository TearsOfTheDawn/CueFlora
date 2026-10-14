"""Setup entry point; CLI arguments never invoke a graphical browser."""
import sys

if __name__ == '__main__':
    if len(sys.argv) > 1:
        from cueflora_setup.cli import main
        try:
            main()
        except Exception as error:
            # A windowed executable still has a truly non-graphical CLI failure
            # path. Do not let PyInstaller display an exception dialog.
            import json
            from pathlib import Path
            if '--report' in sys.argv:
                try:
                    path = Path(sys.argv[sys.argv.index('--report') + 1])
                    with path.open('x', encoding='utf-8') as stream:
                        json.dump({'valid': False, 'error': str(error), 'errorType': type(error).__name__}, stream, indent=2)
                except (OSError, IndexError):
                    pass
            if sys.stderr is not None:
                print(str(error), file=sys.stderr)
            raise SystemExit(1)
    else:
        from cueflora_setup.gui import main
        main()
