# CueFlora implementation handoff

Date: 2026-10-11. Independent Windows x64 / Chrome private preview. No live installation, Computer Use, browser automation, inference or API-credit-spending acceptance run was performed.

Latest delivery: `artifacts/distribution/preview-polish-001`. See `PRIVATE_PREVIEW_POLISH_HANDOFF.md` for the subsequent onboarding reliability changes, rebuilt artifacts and current verification. The original `preview-001` evidence below remains historical and is not overwritten.

## Implemented

- Copied 136 actual current source/config/test files, including uncommitted improvements. Fresh local Git with no commits/remotes; source is staged but not committed. Excluded original `.git`, secrets, captures, environments, backups and prior outputs. Baseline covers 181 original recorded files and Git status. MIT licence/copyright unchanged, upstream attribution explicit.
- Rebranded active extension/settings/player/native host/Setup. Five-petal violet/yellow application icons and accessible monochrome player flower. Full player/appearance ID, class, CSS-variable, storage, bridge and evidence isolation. Host registration `cueflora_host`, dedicated per-user `CueFlora` root. No Substrata settings or credential migration.
- Stable public development key/Chrome ID `klnnagigpdlgchlablabnafceoldfalm`; private installer binds this exact ID/product/runtime inventory. No private key or final public identity invented. Firefox identities unset and package selection unavailable.
- Resumable helper → AI → language setup; first-install-only opening and toolbar settings action. Neither hosted nor local is selected initially; independent blank/unconfigured stages, manual address/key/model, optional model discovery, explicit Save/Cancel and visible persistence failures. Additional processing/transport controls are under Advanced. Partial persistence is reported without claiming full success.
- Settings-only validated correlated metadata checks: bounded GET `/models`, no inference, no redirects, strict safe model identifiers, bounded payload and redacted reason codes. Unsupported discovery leaves manual entry available; connection success explicitly does not certify generation compatibility. Only selected unconfigured AI stages are blocked. Caption-only operation needs neither configured AI nor helper.
- Immutable provider and processing snapshots per Run; later edits cannot redirect or retune active requests. Preserved pipeline, Opus settings/normalization, appearance Apply/Cancel, cue IDs, English timing and TypeScript-owned eight-request recovery. No phrase filters or subtitle substitutions added.
- One unsigned self-extracting `CueFlora Setup.exe` containing the onedir host, Python/tools, configuration and notices. Per-user explicit Chrome selection/confirmation; no admin/PATH/service/model/extension installation. Versioned maintenance copies and owned Start Menu shortcut share existing lifecycle locks/journal/recovery. Repair/upgrade/rollback/conflict rejection/recoverable uninstall retained.
- Non-graphical self-check/detection/package validation with exclusive file reports; malformed payloads fail without GUI exception dialogs. Bootloader-owned Windows 8.3 temporary paths are canonicalized without weakening user payload link rejection.
- Private assembly with unpacked Chrome, keyless store-upload candidate, notices, inventories and exact ZIP checksums. Public publication deliberately blocked. Documentation updated with `update-agents-md`.

## Automated verification

The final local gate report is `artifacts/verification-004/verification.json` and its per-command logs. Final counts: 237 Vitest tests in 32 files; 76 native/setup tests (74 passed, two Windows symlink-privilege skips); five packaging tests; one Node release-config test. Typecheck, both browser builds, Python compilation and staged whitespace validation are included. All must pass before delivery.

`artifacts/installer-verification-003/installer-verification.json` records the final Setup's restricted-PATH Unicode/spaces self-extraction, Tcl 8.6.12 self-check, exact embedded inventory/binding, read-only browser detection and malformed-payload failure report. No GUI opened.

`artifacts/setup-smoke-003/smoke-report.json` records actual final runtime/Setup temporary-root install/upgrade/rollback/repair/uninstall with simulated browser registration/Start Menu writes, no prototype override, and actual framed restricted-PATH PING. All three bundled tools and host 0.1.0 are checked. Unit tests additionally cover registration/shortcut conflicts, malformed state/journals, interruptions and recovery.

`artifacts/isolation-report-final.json` verifies all 181 recorded original hashes, unchanged original Git status/licence, accounting of 136 copied files, no inherited history/remotes and operational namespace separation. Ignored original captures were never copied or accessed for this task; no claim is made that every ignored original file was hashed.

Final ZIP verification is retained in `artifacts/distribution/preview-001/artifact-report.json`. It independently streams exact inventory membership/hashes. A checksum is not publisher authentication.

## Artifacts

Recommended delivery directory: `artifacts/distribution/preview-001`.

- `CueFlora-Windows-x64-Chrome-preview.zip` — complete private preview.
- `CueFlora Setup/CueFlora Setup.exe` — single-file installer; embedded runtime, not a separate helper download.
- `CueFlora Setup/Chrome-preview/` — unpacked development extension matching the installer.
- `CueFlora Setup/CueFlora-Chrome-store-upload.zip` — keyless future upload candidate; not store-approved and not identity-compatible with this preview installer after store assignment.
- `CueFlora Setup/SHA256SUMS.json`, runtime inventory, dependency inventory, release configuration, notices and short installation/removal instructions.

Source runtime: `artifacts/distribution/runtime-002/dist/cueflora-host`. Final Setup build: `artifacts/distribution/setup-005/dist/CueFlora Setup.exe`. Earlier numbered builds/checks are retained as development evidence, not recommended artifacts.

## Migration and removal

CueFlora starts with independent empty provider/preferences storage. Nothing is imported from Substrata or page-origin caches. Original APIs/services and registrations remain untouched. Generated CueFlora caches retain existing version/model/source validation under the new namespace.

Uninstall removes owned CueFlora native registration and Start Menu shortcut, quarantines runtime versions under `removed-...`, and leaves versioned maintenance executables. Settings/evidence remain; disk space is not fully reclaimed. Repair uses the payload matching the installed private binding, normally from the active Start Menu launcher. Rollback restores the matching older launcher/payload. Modified/foreign entries are never silently reclaimed.

Final edge-case checks added truly keyless ASR/translation headers (no empty Bearer token) and Repair from a matching downloaded package when the installed maintenance executable is missing. Both have regression coverage; inference-header tests use mocks and spend no API credits.

## Deferred gates and user involvement

No further input or manual testing is required to complete this engineering milestone. Installing/testing remains optional; follow `INSTALLATION.md` when ready. The original working Substrata is not replaced.

Unverified: clean-machine installation/lifecycle, actual Chrome-native Run, GUI/scanner acceptance, semantic subtitle quality, remote CI and skipped symlink execution. Deferred: final repository/owner/public hosting/store identity, matching public installer, signing/notarization, store credentials/approvals/publication, complete redistribution clearance, Firefox certification and macOS/Linux packaging. ChatGPT sign-in and AI provisioning are excluded.

The included GPL-enabled FFmpeg/ffprobe and missing standalone Tcl notice remain concrete redistribution review work. See `REDISTRIBUTION_CHECKLIST.md`; neither private installation permission nor successful tests grant public-distribution clearance.
