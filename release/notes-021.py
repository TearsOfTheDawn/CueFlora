"""Update only the newly published 0.2.1 notes; binaries/tags are never replaced."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
sys.path[:0]=[str(Path('release-source/packaging').resolve()),str(Path('release-source/native').resolve())]
from stage_release import paired_release_notes
receipt=json.loads(Path('artifacts/publication-receipt.json').read_text())
assert receipt['version']=='0.2.1' and receipt['sourceCommit']=='abaf8e19411ab496cafdca33a2c6fad03ababca2' and receipt['published'] is True
assert receipt['candidateRunId']==39684774078 and len(receipt['anonymousDownloads'])==10 and all(item['verified'] for item in receipt['anonymousDownloads'])
text=Path('release-source/CHANGELOG.md').read_text()
match=re.search(r'^## \[0\.2\.1\][^\n]*2026-10-21\n(?P<body>.*?)(?=^## |\Z)',text,re.M|re.S)
assert match and 'GHSA-6q48-6c7w-9gw2' in match.group('body')
base=paired_release_notes(receipt['staging'])
installation=base[base.index('### New users'):]
notes=('# CueFlora 0.2.1 — Windows & Chrome\n\n'
    '## [Download CueFlora Setup.exe — the only required download](https://github.com/TearsOfTheDawn/CueFlora/releases/download/v0.2.1/CueFlora-0.2.1-Setup.exe)\n\n'
    '**Upgrading from 0.2.0:** its updater is broken. Download this Setup manually, finish all Runs, confirm Upgrade, then click CueFlora **Reload** at chrome://extensions and reload YouTube tabs. Do not remove/reinstall the extension.\n\n'
    '## Changelog — 2026-10-21\n\n'+match.group('body').strip()+'\n\n'
    '## Installation and optional files\n\n'+installation)
target=Path('artifacts/release-notes-0.2.1.md');target.write_text(notes,encoding='utf-8')
subprocess.run(['gh','release','edit','v0.2.1','--repo','TearsOfTheDawn/CueFlora','--notes-file',str(target)],check=True,timeout=120)
Path('artifacts/release-notes-receipt.json').write_text(json.dumps({'version':'0.2.1','sourceCommit':receipt['sourceCommit'],
    'releaseNotesSha256':hashlib.sha256(notes.encode()).hexdigest(),'datedChangelogIncluded':True,
    'manual020BootstrapProminent':True,'binaryAssetsModified':False},indent=2)+'\n')
print('CUEFLORA_021_RELEASE_NOTES='+json.dumps(json.loads(Path('artifacts/release-notes-receipt.json').read_text()),separators=(',',':')))
