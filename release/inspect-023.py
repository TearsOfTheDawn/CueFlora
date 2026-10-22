"""Inspect this exact candidate without installing or executing its payload."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path('release-source').resolve()
sys.path[:0] = [str(ROOT / 'packaging'), str(ROOT / 'native')]
from github_candidate import ordinary
from cueflora_host import update_payload
from release_inputs import digest

candidate = Path('reviewed-candidate').resolve()
summary = json.loads((candidate / 'CANDIDATE_SUMMARY.json').read_text())
assert summary['version'] == '0.2.3' and summary['sourceCommit'] == '1efb73091ccac6dd70cc6f43626d9ec5bcfd6c53'
assert str(summary['workflowRunId']) == '39836085546' and summary['engineeringPassed'] is True
assert summary['artifacts']['sourceInventorySha256'] == '07ac77909c97b8457863554addaccd273721b2c75eb15a2671fd920f33116a83'
assert summary['sourceArchiveSha256'] == '2a77a46f2564c61c29535a090ea42067098df33c45bca4b7bb1dd9971dc91281'
inventory = json.loads((candidate / 'CANDIDATE_INVENTORY.json').read_text())
actual = {p.relative_to(candidate).as_posix() for p in candidate.rglob('*') if p.is_file()}
assert actual == set(inventory['files']) | {'CANDIDATE_INVENTORY.json'}
for name, checksum in inventory['files'].items():
    assert digest(ordinary(candidate, name)) == checksum
setup = ordinary(candidate, 'release-assets/CueFlora-0.2.3-Setup.exe')
assert digest(setup) == summary['artifacts']['setupSha256']


def read_selected(path, limits):
    original = update_payload.LIMITS
    try:
        update_payload.LIMITS = limits
        return update_payload.inventories(path)
    finally:
        update_payload.LIMITS = original


host_pem = 'bundle/runtime/_internal/certifi/cacert.pem'
downloader = 'bundle/runtime/tools/yt-dlp.exe'
selected = read_selected(setup, {host_pem: 512 * 1024, downloader: 128 * 1024 * 1024})
fixed = '50f79f98dac192b20dbf73f35c56f0b0c557ab267ff5199d1117cc1180b70785'
assert hashlib.sha256(selected[host_pem]).hexdigest() == fixed
with tempfile.TemporaryDirectory() as directory:
    target = Path(directory) / 'yt-dlp.exe'
    target.write_bytes(selected[downloader])
    inside = read_selected(target, {'certifi/cacert.pem': 512 * 1024})
assert hashlib.sha256(inside['certifi/cacert.pem']).hexdigest() == fixed
capabilities = json.loads((candidate / 'capability-verification/capabilities.json').read_text())
assert capabilities['persistentPort'] is True and capabilities['responsesBeforeClosingInput'] == 2
ready = json.loads((candidate / 'readiness.json').read_text())
assert ready['cleanSourceVerification']['passed'] is True
assert ready['cleanSourceVerification']['sourceArchiveSha256'] == summary['sourceArchiveSha256']
assert all(check['exitCode'] == 0 for check in ready['checks'])
out = Path('metadata')
out.mkdir()
for path in candidate.rglob('*'):
    if not path.is_file():
        continue
    relative = path.relative_to(candidate).as_posix()
    if path.suffix == '.json' or relative == 'release-assets/CueFlora-source.zip' or relative.startswith('verification/') and path.suffix == '.log':
        if path.stat().st_size > 32 * 1024 * 1024:
            raise ValueError('Oversized inspection metadata')
        destination = out / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
proof = {'candidateRunId': 39836085546, 'sourceCommit': summary['sourceCommit'], 'artifacts': summary['artifacts'],
    'version': '0.2.3', 'certifiVersion': '2026.10.19', 'expectedUpstreamBundleSha256': fixed,
    'frozenHostBundleMatches': True, 'embeddedDownloaderBundleMatches': True,
    'sourceMatchesLocalAuditedCandidate': True, 'persistentPortChecksPassed': True,
    'cleanSourcePassed': True, 'setupExecuted': False, 'allCandidateFilesVerified': len(inventory['files'])}
(out / 'frozen-certificate-verification.json').write_text(json.dumps(proof, indent=2) + '\n')
print('CUEFLORA_023_REVIEW_METADATA=' + json.dumps({'summary': summary, 'verification': proof}, separators=(',', ':')))
