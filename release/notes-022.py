"""Set this release's changelog and single-download instructions, never its bytes."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

sys.path[:0] = [str(Path('release-source/packaging').resolve()), str(Path('release-source/native').resolve())]
from stage_release import paired_release_notes

receipt = json.loads(Path('artifacts/publication-receipt.json').read_text())
assert receipt['version'] == '0.2.2' and receipt['sourceCommit'] == '2089edaa8d92e416e8daa3dccc61bdf55bacf7a5'
assert receipt['published'] is True and receipt['candidateRunId'] == 39813901477
assert len(receipt['anonymousDownloads']) == 10 and all(item['verified'] for item in receipt['anonymousDownloads'])
text = Path('release-source/CHANGELOG.md').read_text()
match = re.search(r'^## \[0\.2\.2\][^\n]*2026-10-22[^\n]*\n(?P<body>.*?)(?=^## |\Z)', text, re.M | re.S)
assert match and 'native-message input' in match.group('body')
fixes = match.group('body').split('### Upgrade and limitations', 1)[0].strip()
base = paired_release_notes(receipt['staging'])
installation = base[base.index('### New users'):]
notes = ('# CueFlora 0.2.2 — Windows & Chrome\n\n'
    '## [Download CueFlora Setup.exe — the only required download](https://github.com/TearsOfTheDawn/CueFlora/releases/download/v0.2.2/CueFlora-0.2.2-Setup.exe)\n\n'
    '**Updating from 0.2.0 or 0.2.1:** use this Setup manually if the old updater stalls. Finish all Runs, confirm Upgrade, then click CueFlora **Reload** at chrome://extensions and reload YouTube tabs. Do not remove/reinstall the extension or reset your keys/models.\n\n'
    '## Changelog — 2026-10-22\n\n' + fixes + '\n\n'
    'The reported open-connection downloader failure was reproduced and repaired. This release does not claim to fix every possible provider incompatibility or alter subtitle-generation settings.\n\n'
    '## Installation and optional files\n\n' + installation)
target = Path('artifacts/release-notes-0.2.2.md')
target.write_text(notes, encoding='utf-8')
subprocess.run(['gh', 'release', 'edit', 'v0.2.2', '--repo', 'TearsOfTheDawn/CueFlora',
                '--title', 'CueFlora 0.2.2 — Windows & Chrome', '--notes-file', str(target)], check=True, timeout=120)
result = {'version': '0.2.2', 'sourceCommit': receipt['sourceCommit'],
    'releaseNotesSha256': hashlib.sha256(notes.encode()).hexdigest(), 'datedChangelogIncluded': True,
    'singleDownloadProminent': True, 'manualUpgradeAndChromeReloadProminent': True, 'binaryAssetsModified': False}
Path('artifacts/release-notes-receipt.json').write_text(json.dumps(result, indent=2) + '\n')
print('CUEFLORA_022_RELEASE_NOTES=' + json.dumps(result, separators=(',', ':')))
