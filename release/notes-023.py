"""Publish this release's changelog/instructions without changing its assets."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

sys.path[:0] = [str(Path('release-source/packaging').resolve()), str(Path('release-source/native').resolve())]
from stage_release import paired_release_notes

receipt = json.loads(Path('artifacts/publication-receipt.json').read_text())
assert receipt['version'] == '0.2.3' and receipt['sourceCommit'] == '1efb73091ccac6dd70cc6f43626d9ec5bcfd6c53'
assert receipt['published'] is True and receipt['candidateRunId'] == 39836085546
assert len(receipt['anonymousDownloads']) == 10 and all(item['verified'] for item in receipt['anonymousDownloads'])
text = Path('release-source/CHANGELOG.md').read_text()
match = re.search(r'^## 0\.2\.3[^\n]*2026-10-22[^\n]*\n(?P<body>.*?)(?=^## |\Z)', text, re.M | re.S)
assert match and 'eight-call budget' in match.group('body')
fixes = match.group('body').split('### Upgrade and limitations', 1)[0].strip()
base = paired_release_notes(receipt['staging'])
installation = base[base.index('### New users'):]
notes = ('# CueFlora 0.2.3 — Windows & Chrome\n\n'
    '## [Download CueFlora Setup.exe — the only required download](https://github.com/TearsOfTheDawn/CueFlora/releases/download/v0.2.3/CueFlora-0.2.3-Setup.exe)\n\n'
    '**Existing users:** finish all Runs, install the update and confirm Upgrade, then click **Restart CueFlora** (or CueFlora **Reload** at chrome://extensions) and reload YouTube tabs. Do not remove/reinstall the extension or reset keys/models. Use the Setup download above if an older updater fails or stalls.\n\n'
    '## Changelog — 2026-10-22\n\n' + fixes + '\n\n'
    'The exact synthetic scheduling regression now resolves in two model calls instead of exhausting eight. The eight-call ceiling, subtitle timing and validation rules are retained. This does not guarantee every model response is valid or establish live-browser/semantic acceptance.\n\n'
    '## Installation and optional files\n\n' + installation)
target = Path('artifacts/release-notes-0.2.3.md')
target.write_text(notes, encoding='utf-8')
subprocess.run(['gh', 'release', 'edit', 'v0.2.3', '--repo', 'TearsOfTheDawn/CueFlora',
                '--title', 'CueFlora 0.2.3 — Windows & Chrome', '--notes-file', str(target)], check=True, timeout=120)
result = {'version': '0.2.3', 'sourceCommit': receipt['sourceCommit'],
    'releaseNotesSha256': hashlib.sha256(notes.encode()).hexdigest(), 'datedChangelogIncluded': True,
    'singleDownloadProminent': True, 'manualUpgradeAndChromeReloadProminent': True, 'binaryAssetsModified': False}
Path('artifacts/release-notes-receipt.json').write_text(json.dumps(result, indent=2) + '\n')
print('CUEFLORA_023_RELEASE_NOTES=' + json.dumps(result, separators=(',', ':')))
