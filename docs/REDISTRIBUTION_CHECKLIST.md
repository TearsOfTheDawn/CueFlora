# CueFlora third-party redistribution ledger

0.1.4 current preparation: signature-verified FFmpeg/ffprobe 9.0.2 shared builds report LGPL 2.1-or-later and retain pinned core/Opus sources, recipe, notices and exact DLL/executable hashes. The unchanged yt-dlp tag is rebuilt on pinned Python 3.13.15/OpenSSL 3.5.7, with exact upstream wheel/source pins and byte-matched curl recipe evidence. Original V8/binding notices and Windows interpreter component notices are collected separately. See RELEASE_COMPLETION.md and each fresh candidate's generated ledger; notices and source evidence do not automatically grant redistribution approval.

This records unresolved obligations, not legal clearance. The generated private preview is not approved for public redistribution. CueFlora application source retains Substrata's original MIT licence/copyright unchanged; renaming the application does not remove attribution or third-party obligations.

Runtime/Setup include collected Python/package/interpreter notices and hash-bound tool evidence. Python and Tk notices come from the build interpreter. The absent standalone Tcl notice is now supplied from official core-8-6-12 only for an actually matching interpreter; its provenance is recorded. This resolves that notice gap, not every binary/dependency obligation. See `PUBLIC_RELEASE_BLOCKERS.md` and the generated licence-evidence report.

## Historical preserved-binary audit (not current shipment)

The following table and old hashes describe earlier opaque GPL audio tools and official downloader bytes, which remain preserved but are not substituted into current builds. Current actual hashes/configuration/licence output come from `runtime-manifest.json`, `licenses/*-binary-evidence.json` and `release-ledger/dependency-ledger.json` of the selected candidate. Do not use historical hashes to verify a newly compiled package.

| Component | Included evidence | Still required before public redistribution |
|---|---|---|
| Substrata-derived application | Unchanged MIT licence/copyright and README attribution | Keep notices with source/binary distributions |
| Python/httpx and dependencies | Exact environment inventory and collected notices | Confirm applicable licences against actual shipped runtime files |
| PyInstaller | Pinned version and available package notices | Review bootloader exception and attribution for actual artifacts |
| Tcl/Tk in Setup | Headless Tcl 8.6.12 load, official matching Tcl notice and interpreter notice inventory | Verify Tk/Tcl binary provenance and all shipped native-library notices |
| yt-dlp executable | Exact hash/version, binary evidence | Review bundled binary dependency licences/notices and applicable source obligations |
| Deno | Official 2.9.7 Windows asset hash, source, MIT notice and Cargo.lock inventory | Verify actual binary third-party closure; root MIT notice alone is not comprehensive |
| FFmpeg/ffprobe | Exact hashes, build flags and licence output | Obtain matching upstream source revision, build scripts, enabled-library notices and applicable GPL/LGPL corresponding source; reject incompatible builds |
| npm extension/build dependencies | Full lock-based version/integrity/notice inventory | Identify the actual bundled-code closure and collect any missing applicable notices; build-only inclusion is not shipment evidence |

Preserved audio inputs still match their prior hashes; yt-dlp additionally matches the official pinned checksum. Python wheels, interpreter files/snapshot, tool downloads and source/notice evidence are hash-locked in `inputs-windows.lock.json`; pip uses `requirements-windows-hashed.lock`. Source matching and notices are collected separately from legal clearance. Some tools may need a simpler reviewed replacement before public release, but no such replacement is automatic.

0.1.2 adds `release-ledger/dependency-ledger.json`, consolidated notices, source-notice hashes and separately locked supplemental evidence. Runtime file hashes, Setup archive entry hashes (including Tcl/Tk/native DLLs), actual interpreter matches, observed yt-dlp metadata, emitted JavaScript and build-only Python are distinct evidence scopes. curl_cffi/websockets source archives and Deno's pinned V8-binding crate do not automatically cover their embedded curl/BoringSSL/V8 native sources. The tested dated FFmpeg archive is not byte-identical to the preserved tools; see `FFMPEG_REPLACEMENT_PROPOSAL.md`. No ledger row automatically grants clearance.

Final owner/public browser IDs remain blank in `packaging/release.template.json`. The development key and private permission do not provide public-release approval. Signing, scanner results, browser-store approval, credentials and publication authorization are separate gates.

Historical preserved tool SHA-256 inputs:

- yt-dlp: `66674953fe251b89f4d08c5f0e35e0728679bd67ab3d7d05c0562af101dd3e7a`
- ffmpeg: `851aa8ea5366b5af33c0681cc292d662829c7088e9ac96f6e9b37030e6835ba4`
- ffprobe: `01dd9a776db5df93d0e3a9b8714a7a7500402e8e628cdc68608ed781454f8b71`
