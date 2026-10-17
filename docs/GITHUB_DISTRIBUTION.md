# GitHub-only distribution

Windows x64 / Google Chrome, source version 0.1.13. Chrome Web Store distribution was abandoned on 2026-10-17; historical Store handoffs remain evidence, not release requirements.

## Install and update

Use the complete Windows ZIP from GitHub Releases. Extract permanently, load `CueFlora Setup/Chrome-extension` through `chrome://extensions` → Developer mode → Load unpacked, then run the included Setup, select Chrome and confirm. Configure existing compatible AI services, choose languages and press Run. Caption-only use depends on the video.

The extension retains release public key/ID `akcolbcdfnjcahhhodnpablekjagfadf`; the helper permits exactly that ID. The separate development ID remains `klnnagigpdlgchlablabnafceoldfalm`. A Store installation is not needed to load the keyed folder. Do not use a keyless Store ZIP.

Keep the same folder/ID for updates, replace extension files and Reload, then reload YouTube tabs. Use matching Setup for helper upgrades. Maintenance retains locking, recovery, repair, rollback, identity conflict rejection and recoverable uninstall. Do not remove/reinstall merely to update or promise settings transfer across IDs. Never touch Substrata. Unsigned files must not be an excuse to disable security protections.

## Implemented engineering

- `scripts/build-profile.mjs` and `packaging/github-identity.json` select the GitHub channel, release key/ID and remote HTTPS without hidden provider defaults.
- `prepare_windows.py` builds two fresh runtime/Setup pairs, keyed extension, full Windows ZIP, clean source, original notices and third-party sources. Legacy Store/private profiles remain compatible.
- `assemble_preview.py`, `installation_guide.py`, `release_assets.py` and `github_materials.py` generate channel-specific packages, simple instructions, checksums/inventories and real release-link pages. Generated pages do not establish hosting.
- `approval_evidence.py`/`release_readiness.py` exclude Store approval/screenshots only from GitHub; they retain exact artifact bindings, licence/native-security review, identity/integrity and explicit publication decisions.
- `github_candidate.py` exports measured evidence without approvals or nested synthetic installation payloads, verifies its entire handoff inventory and restores exact assets for publication.
- `github_publication.py` verifies scoped review, exact public commit/blob/mode tree, draft assets and hashes, then stages/promotes without overwrite. Every public asset is anonymously hash-checked before download pages update.
- `github-candidate.yml` is read-only and version/branch scoped. `github-publication.yml` is the expressly authorised one-time 0.1.13 publisher, restricted to the exact repository, branch and review file. It does not publish future versions automatically.

A source-only export, passing build or generated URL is never reported as a hosted installer. The candidate readiness and publication receipt record what actually ran. No live installation, browser automation, AI inference or clean-machine acceptance is performed.

## Recorded policy decision

The audit did not establish general YouTube permission for arbitrary-video audio acquisition. GitHub hosting does not change that finding or establish that every use is prohibited. The publisher explicitly directed publication: "Yes, publish anyway". Only this GitHub download-policy decision may be recorded as `reviewed` with `authorizationEstablished: false`; licence/native-security checks cannot be waived by it. Historical audits remain intact. No YouTube or Google approval is claimed.

Public instructions stay concise: users must process content they are entitled to use and comply with applicable terms and law. No claim is made that this removes a publisher's responsibilities.

## Rebuild and publication

Use `packaging/bootstrap_public_cache.py --online` for exact pinned public inputs, `bootstrap_offline.py --official` for the build interpreter, then `prepare_windows.py --public-config packaging/github-identity.json` with fresh output and the documented caches. See the full preparation documentation for arguments.

The release target's complete tree must match the clean source archive. The publisher review is a separate non-source packet bound to the successful candidate run, source commit and all four artifact hashes. No build invents approval. The one-time publication job consumes that reviewed candidate with an ephemeral GitHub token, uploads required assets/notices/sources/checksums, refuses existing tags/releases, and updates the existing Pages branch only after anonymous verification.
