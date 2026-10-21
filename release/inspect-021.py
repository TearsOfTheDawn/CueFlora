"""Inspect the exact CI candidate and certificate payloads without executing them."""
import hashlib,json,shutil,sys,tempfile
from pathlib import Path
ROOT=Path('release-source').resolve()
sys.path[:0]=[str(ROOT/'packaging'),str(ROOT/'native')]
from github_candidate import ordinary
from cueflora_host import update_payload
from release_inputs import digest
candidate=Path('reviewed-candidate').resolve()
summary=json.loads((candidate/'CANDIDATE_SUMMARY.json').read_text())
assert summary['version']=='0.2.1' and summary['sourceCommit']=='1c6e0f8fb52bb20b7e89007ff1789de13f20692c'
assert str(summary['workflowRunId'])=='39684774078' and summary['engineeringPassed'] is True
assert summary['artifacts']['sourceInventorySha256']=='7a75c1da5c6266ca25ab42df57a1f37bd2d695289707a1278952aaba69a039ae'
inventory=json.loads((candidate/'CANDIDATE_INVENTORY.json').read_text())
actual={p.relative_to(candidate).as_posix() for p in candidate.rglob('*') if p.is_file()}
assert actual==set(inventory['files'])|{'CANDIDATE_INVENTORY.json'}
for name,checksum in inventory['files'].items():assert digest(ordinary(candidate,name))==checksum
setup=ordinary(candidate,'release-assets/CueFlora-0.2.1-Setup.exe')
assert digest(setup)==summary['artifacts']['setupSha256']
def read_selected(path,limits):
    saved=update_payload.LIMITS
    try:
        update_payload.LIMITS=limits
        return update_payload.inventories(path)
    finally:update_payload.LIMITS=saved
host_pem='bundle/runtime/_internal/certifi/cacert.pem'
downloader='bundle/runtime/tools/yt-dlp.exe'
selected=read_selected(setup,{host_pem:512*1024,downloader:128*1024*1024})
fixed='50f79f98dac192b20dbf73f35c56f0b0c557ab267ff5199d1117cc1180b70785'
assert hashlib.sha256(selected[host_pem]).hexdigest()==fixed
with tempfile.TemporaryDirectory() as directory:
    target=Path(directory)/'yt-dlp.exe';target.write_bytes(selected[downloader])
    inside=read_selected(target,{'certifi/cacert.pem':512*1024})
assert hashlib.sha256(inside['certifi/cacert.pem']).hexdigest()==fixed
out=Path('metadata');out.mkdir()
for p in candidate.rglob('*'):
    if not p.is_file():continue
    relative=p.relative_to(candidate).as_posix()
    if p.suffix=='.json' or relative=='release-assets/CueFlora-source.zip' or relative.startswith('verification/') and p.suffix=='.log':
        if p.stat().st_size>32*1024*1024:raise ValueError('Oversized metadata')
        dest=out/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
proof={'candidateRunId':39684774078,'sourceCommit':summary['sourceCommit'],'artifacts':summary['artifacts'],
    'version':'0.2.1','certifiVersion':'2026.10.19','expectedUpstreamBundleSha256':fixed,
    'frozenHostBundleMatches':True,'embeddedDownloaderBundleMatches':True,
    'setupExecuted':False,'allCandidateFilesVerified':len(inventory['files'])}
(out/'frozen-certificate-verification.json').write_text(json.dumps(proof,indent=2)+'\n')
print('CUEFLORA_021_REVIEW_METADATA='+json.dumps({'summary':summary,'certificateVerification':proof},separators=(',',':')))
