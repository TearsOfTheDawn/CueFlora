"""Run local engineering gates with per-command evidence; never launch browsers."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def run(output):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    npm = ['cmd.exe', '/d', '/c', 'npm'] if sys.platform == 'win32' else ['npm']
    python = sys.executable
    modules = ['cueflora_setup.test_setup', 'cueflora_host.test_runtime_tools', 'cueflora_host.test_deno',
        'cueflora_setup.test_maintenance', 'cueflora_setup.test_terms', 'cueflora_setup.test_extension_pair', 'cueflora_host.test_provider_check', 'cueflora_host.test_credentials', 'cueflora_host.test_chatgpt',
        'cueflora_host.test_controlled_evidence', 'cueflora_host.test_audio_preparation','cueflora_host.test_download_progress','cueflora_host.test_updates','cueflora_host.test_update_payload',
        'cueflora_host.test_translate', 'cueflora_host.test_whisper_regressions',
        'cueflora_host.test_evidence', 'cueflora_host.test_quality_benchmark',
        'cueflora_host.test_quality_translation', 'cueflora_host.test_native_protocol']
    checks = [(name, npm + ['run', name], ROOT) for name in
              ('typecheck', 'test', 'build:firefox', 'build:chrome')]
    checks += [('native', [python, '-m', 'unittest', *modules], ROOT / 'native'),
               ('packaging', [python, '-m', 'unittest', 'discover', '-s', 'packaging', '-p', 'test_*.py'], ROOT),
               ('release-config', ['node', '--test', 'scripts/release-config.test.mjs'], ROOT),
               ('python-compile', [python, '-m', 'compileall', '-q', 'native/cueflora_host', 'native/cueflora_setup', 'packaging'], ROOT)]
    if (ROOT/'.git').exists():
        checks += [('whitespace', ['git', '-c', 'core.safecrlf=false', 'diff', '--check'], ROOT),
               ('staged-whitespace', ['git', '-c', 'core.safecrlf=false', 'diff', '--cached', '--check'], ROOT)]
    checks += [('new-whitespace', [python, 'packaging/check_new_whitespace.py'], ROOT)]
    report = {'browserAutomation': False, 'liveBrowserAcceptance': False,
              'checks': [], 'passed': False,'gitHistoryRequired':False,
              'gitWhitespaceChecks':'available' if (ROOT/'.git').exists() else 'not applicable to source export; source whitespace still checked'}
    for index, (name, command, cwd) in enumerate(checks):
        started = time.monotonic()
        log = output / f'{index:02d}-{name.replace(":", "-")}.log'
        with log.open('wb') as stream:
            try:
                result = subprocess.run(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
                                        timeout=600, check=False)
                code = result.returncode
            except (OSError, subprocess.TimeoutExpired) as error:
                stream.write((type(error).__name__ + '\n').encode())
                code = -1
        report['checks'].append({'name': name, 'exitCode': code,
            'durationSeconds': round(time.monotonic() - started, 2), 'log': log.name})
        (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(f'{name}: {"PASS" if code == 0 else "FAIL"}', flush=True)
        if code:
            return 1
    report['passed'] = True
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Fresh local evidence directory')
    args = parser.parse_args()
    raise SystemExit(run(args.output))
