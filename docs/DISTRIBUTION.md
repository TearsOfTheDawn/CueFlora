# CueFlora Windows/Chrome preview distribution

Current source version is 0.1.4, a prepublication candidate. [RELEASE_COMPLETION.md](RELEASE_COMPLETION.md) documents complete public-source preparation, signature-verified FFmpeg/ffprobe 9.0.2 shared builds, the supported-Python same-version downloader rebuild, exact dependency notice/source evidence, public-identity construction and separate approval gates. Earlier artifacts and historical evidence remain preserved. Public publisher/identity/hosting, external acceptance and remaining licence/policy questions are not automatically cleared.

Independent project at `C:\AI\CueFlora`, copied from current modified Substrata source. Fresh local Git repository; no inherited commits/remotes, credentials, private captures, dependency environments, backups or previous outputs. Original MIT copyright/licence retained. All recorded original hashes and Git status remain unchanged.

## Implemented package

The delivery is created in a fresh directory by `release:prepare`; its `readiness.json` and implementation handoff are the measured ledger. Windows-protected credentials, store-only HTTPS, neutral provider setup and subtitle processing are preserved. Tool origins, compiler inputs, interpreter/native notices, extension notice coverage and source bundles are recorded independently from approval. The stable development identity is unchanged; current source-built audio and modern-runtime downloader replace earlier opaque/aging binaries only in newly verified packages. Earlier handoffs and binary hashes remain historical, not current release clearance.

An unsigned onefile **CueFlora Setup.exe** self-extracts Setup and an immutable embedded bundle. The installed native runtime is onedir. The bundle includes Python, host, yt-dlp, ffmpeg, ffprobe, Deno, notices, exact inventory and Chrome-only private configuration.

Development identity: `klnnagigpdlgchlablabnafceoldfalm`, derived from the retained public key in `preview-identity.json`. No private key is retained. The preview configuration binds `product: cueflora`, that ID and the runtime inventory SHA-256. `publicReleaseAuthorized` and `redistributionApproved` remain false. Final public identities/owner are not assigned.

Installation is per-user, explicit Chrome selection/confirmation, no administrator access, persistent companion, PATH modification or AI provisioning. Native registration name is `cueflora_host`; installation root is `%LOCALAPPDATA%\CueFlora`. State, cache, DOM, CSS, bridge events and evidence names are separate from Substrata.

Lifecycle retains ownership checks, locks, version activation, matching-identity repair, prior-version/release/launcher rollback, journaling and recoverable uninstall. Start Menu changes are part of the same transaction; foreign/modified entries are refused. Maintenance Setup copies are versioned. Uninstall removes the owned shortcut/registration and quarantines runtime versions, while retaining maintenance copies, settings and evidence.

## Reproduce locally

Use the hash-locked build environment and exact offline input cache. The preparation command selects all four explicit tool paths, verifies local EJS, builds/compares fresh pairs and retains evidence. No model is downloaded and no inference occurs. Each output directory must be fresh. Earlier three-tool commands/lock are historical, not the current portable contract.

```powershell
npm run release:prepare -- --output artifacts/distribution/new-preparation --cache artifacts/input-cache-0.1.4 --evidence-cache artifacts/redistribution-evidence-014 --audio-cache artifacts/audio-tool-inputs-9.0.2
```

Do not delete/regenerate `preview-identity.json` during rebuilds; this would break identity continuity. Its key is public development metadata, not a signing credential. Final public builds need a separately assigned identity and matching installer; non-dry publication is deliberately blocked in the inherited release script.

The delivery includes a full private preview ZIP, the standalone Setup, unpacked Chrome preview, keyless store-upload candidate, SHA256SUMS, exact runtime inventory, available third-party notices and dependency inventory. The npm inventory lists all locked build/runtime dependencies, not a proof of bundled-code licence closure.

## Automated verification

`packaging/verify_local.py --output <fresh-directory>` runs typecheck, all Vitest tests, Firefox/Chrome builds, native/setup tests, packaging tests, Node release-config tests, Python compilation and staged/unstaged/new-file whitespace checks. New files are checked without staging or committing them. Text attributes prevent mixed Windows line endings from appearing as trailing whitespace.

`verify_isolation.py --report <fresh-file>` checks the original 181 recorded file hashes and Git status, unchanged MIT licence, complete accounting of 136 copied source files, fresh history/remotes and active namespace separation. It does not hash every ignored original capture, which was never accessed/copied or modified.

`smoke_setup.py --payload <runtime> --release <release.json> --launcher <Setup.exe> --output <fresh-directory>` exercises actual payload install/upgrade/rollback/repair/uninstall in a Unicode/spaced disposable root, with fake registration and fake Start Menu writes. No prototype override is used. Framed PING uses restricted PATH, matching host version and all bundled tools.

`verify_installer.py --setup <Setup.exe> --runtime <runtime> --output <fresh-directory>` runs only headless commands: extraction, Tcl load, embedded full inventory validation, detection, malformed-payload failure reports. It creates no windows and does not install/register anything.

`verify_archive.py <preview.zip>` independently verifies exact membership and every streamed SHA-256 without extraction/execution. Hashes are integrity evidence, not authenticity/signing.

`verify_credentials.py` exercises real DPAPI through the actual frozen host using synthetic keys, restricted PATH, context/tamper failures and no HTTP/inference. `dependency_ledger.py` records runtime and onefile Setup entry hashes, source/notice matches, actual interpreter-native payload matches, observed emitted JavaScript and build-only dependencies separately. Supplemental evidence inputs have their own lock/cache. PE debug timestamps are measured explicitly; actual payload changes remain visible.

PyInstaller receives an isolated PATH containing the pinned interpreter/DLL directory and Windows System32, never Codex's unrelated tool paths. Builders hash-check every collected native input against the interpreter lock; the final ledger rejects unmatched shipped DLLs/pyds as well. `security-hardening-001` passed functional gates but was superseded after a follow-up audit found incidental PATH DLLs. It remains evidence, not the final delivery. `security-hardening-002` stopped on Windows environment-key casing, corrected with a regression test. The corrected delivery uses a fresh `security-hardening-003` directory.

See `IMPLEMENTATION_HANDOFF.md` for final artifact and evidence paths. Two Windows symlink tests are skipped because the environment lacks symlink privilege. CI definitions are retained/extended, but remote CI has not run; both browser builds do not imply live browser or cross-platform acceptance.

## Deferred gates

No additional user input/testing is required for the private-preview engineering milestone. Installing/testing remains optional. Before broader distribution, separately resolve:

- Real clean-Windows installation, repair/upgrade/rollback/uninstall, scanner behaviour and GUI acceptance.
- Actual Chrome → native host → explicit subtitle Run and semantic quality acceptance.
- Final repository/owner/download hosting, store identity and matching host binding.
- Complete dependency notices/corresponding-source review; see `REDISTRIBUTION_CHECKLIST.md`.
- Signing, store credentials/approval, publication authorization.
- Real macOS/Linux packaging/validation and Firefox certification; no such suitability claim is made.

ChatGPT sign-in and AI-service provisioning remain excluded. Source/audio/normalization/readability/structured IDs and TypeScript-owned eight-request recovery are preserved.
