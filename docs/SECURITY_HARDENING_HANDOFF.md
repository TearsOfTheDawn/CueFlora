# CueFlora 0.1.2 security hardening handoff

Scope: Windows x64 / Chrome private preview, without live installation, browser automation, inference or publication. Substrata, previous artifacts, preview identity and subtitle/audio processing remain preserved. The measured final report is `artifacts/distribution/security-hardening-003/readiness.json`; an unsuccessful or superseded directory is not an accepted artifact. A final measured `IMPLEMENTATION_HANDOFF.md` beside the delivery records actual tests/hashes.

## Implemented

- User-scoped, non-interactive DPAPI; stage/address binding, round-trip verification and strict versioned encrypted records. No machine-wide protection/plaintext fallback.
- Background-owned v2 provider vault; opaque frozen Run references; no saved plaintext or ciphertext in settings/player responses or new Run snapshots. Retired refs are pruned safely.
- Keep/Replace/Remove, explicit address-reuse consent, verified legacy migration with safe retry and accurate partial failures. Read-only uncertain-write reconciliation; existing Save/Cancel/draft/revision guarantees preserved.
- Same-port capability preflight for saved keys, with Upgrade/Repair and zero model attempts on missing/old/disconnected/timed-out preflight. Keyless/caption-only use remains available.
- Store-candidate HTTPS enforcement plus exact loopback exceptions and rejected redirects. Preview acknowledgement compatibility retained. Diagnostic/capture credential exclusion.
- Runtime/Setup/emitted-JavaScript shipment evidence, exact native DLL/interpreter matches, source/notice inventories, supplemental locks and consolidated notices. Candidate FFmpeg archive/recipes investigated but preserved tool bytes not changed.
- Two-build comparison now measures PE debug timestamps while still detecting actual payload changes. CI inspection dependencies/credential checks and new-file whitespace coverage updated; remote CI remains unrun.
- Final provenance audit found incidental Windows runtime DLLs collected from Codex's unrelated PATH in `security-hardening-001`. That artifact is preserved but superseded. Builders now isolate PATH/Python environment and reject every native dependency not matching the locked interpreter bytes; the fresh delivery must pass this check.
- `security-hardening-002` stopped before PyInstaller when Windows environment key casing exposed `SYSTEMROOT` rather than `SystemRoot`. Case-insensitive normalization and a regression test correct this; the failed directory remains evidence, not a delivery.

## Verification and output contract

Preparation must pass full TypeScript/typecheck, both browser regression builds, native/setup and packaging/release tests, Python compilation, all whitespace checks, fresh offline Python/npm restoration, two runtime/Setup builds, actual frozen synthetic-key DPAPI, capability checks, temporary-root lifecycle, headless Setup, restricted-PATH/Unicode PING, original preservation and complete independent ZIP verification.

Fresh output contains Setup, unpacked Chrome preview, keyless store-upload ZIP, checksums, exact inventories/notices, dependency ledger and source evidence. `engineeringPassed` is distinct from `publicReleaseReady`/`redistributionApproved`, which remain false. Two Windows symlink-privilege tests are expected environment skips, not passes. No automated result establishes clean-machine registration, visual/live browser acceptance or semantic accuracy.

## Remaining obligations

The current FFmpeg files do not exactly match the tested dated archive; see `FFMPEG_REPLACEMENT_PROPOSAL.md`. Source closures for enabled FFmpeg libraries, yt-dlp native/bundled dependencies, Deno/V8 and interpreter native libraries remain review gates despite added evidence. The ledger never infers complete licences from application MIT, source Cargo.lock or a package name.

See `SECURE_CREDENTIALS.md`, `STORE_POLICY_ASSESSMENT.md` and `PUBLIC_RELEASE_BLOCKERS.md`. Public publisher/store identity/hosting/signing/screenshots, external browser/clean-system acceptance and platform certification remain separate. No action or mandatory manual test is requested from the user for this milestone. Optional installation/testing uses the complete matching preview package, never Substrata.
