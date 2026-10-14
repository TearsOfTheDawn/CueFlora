# CueFlora private preview polish handoff

Date: 2026-10-11. Windows x64 / Chrome private preview; no live installation, browser automation, Computer Use or inference.

## Changes

- Serialized setup navigation, Save, Finish and reload. Submitted provider/Advanced/language values are snapshotted; late metadata replies are ignored after edits, Cancel or navigation. Every editable provider field participates in dirty detection, including labels and stage/connection choices.
- Completed setup stays complete when revisited. Explicit caption/AI mode controls preserve existing choices and translation Off instead of silently switching a configured stage to AI.
- Added typed, options-only `ONBOARDING_FINISH`. Both languages are validated against the displayed provider revision and saved in one merged preference record. Completion remains a separate write: its failure explicitly reports that languages saved but progress did not.
- Added options-only `SETTINGS_RECONCILE`, queued behind outstanding settings writes. Settings deadlines are 15 seconds; existing native checks remain bounded at 10 seconds. A timed-out mutation blocks further writes until a user-triggered reread succeeds. Reads/reloads never blindly retry writes or inference.
- Retry recovers initialization failure without duplicate handlers/options. Reload retains drafts and refreshes persisted rollback points; Cancel restores saved AI/Advanced values. Persistence failures retain drafts and focus the status region; navigation focuses the step heading.
- Clearer service-information guidance and credential-redacted connection errors. Helper connected and helper ready are separate states; missing tools recommend CueFlora Repair. Metadata access never claims subtitle-generation compatibility; manual model entry remains available.
- Idle player focus/panel opening refreshes provider summaries and languages through background messages. Navigation/sequence/per-key write guards protect newer edits; active Runs and appearance drafts are untouched. Changed selections clear obsolete display without fetching or inference.

## Compatibility and preserved behavior

Existing CueFlora keys and records are retained; no data migration or Substrata import. Stable development Chrome identity remains `klnnagigpdlgchlablabnafceoldfalm`; application/host version remains 0.1.0. No endpoint/model presets, provider substitution, phrase filters, AI provisioning or account sign-in added. Subtitle algorithms, production audio preparation, normalization, English timing, cue IDs, cache safeguards and eight-request recovery are unchanged.

Original preservation covers all 181 recorded source hashes, original Git status and MIT licence; 136 copied files remain accounted for. Ignored original private captures were not accessed or copied. The new source remains in its fresh local repository without commits/remotes.

## Verification and artifacts

Current gate logs: `artifacts/verification-polish-001/verification.json` (`passed: true`). Extension suite: 267 passed tests in 36 files. Native/setup suite: 76 tests (74 passed, two Windows symlink-privilege skips); five packaging tests and one Node release-config test passed. Typecheck, both extension builds, Python compilation and staged/unstaged whitespace checks passed.

Additional evidence:

- `artifacts/isolation-report-polish-001.json`: original preservation and namespace isolation.
- `artifacts/installer-verification-polish-001`: actual final Setup headless self-extraction, Tcl self-check, embedded inventory/binding, read-only detection and malformed-payload report under restricted PATH/Unicode/spaced paths.
- `artifacts/setup-smoke-polish-001`: actual final runtime/Setup temporary-root install, upgrade, rollback, repair and recoverable uninstall using simulated browser registration and Start Menu writes; actual framed bundled PING.
- `artifacts/distribution/preview-polish-001/artifact-report.json`: final ZIP inventory and streamed SHA-256 validation.

Recommended delivery: `artifacts/distribution/preview-polish-001/CueFlora-Windows-x64-Chrome-preview.zip`. Contains `CueFlora Setup.exe`, unpacked `Chrome-preview`, keyless store-upload candidate, notices, inventories, checksums and instructions. Fresh source builds are `runtime-polish-001` and `setup-polish-001`; earlier artifacts remain untouched. Public-release/redistribution approvals remain false.

## User involvement and deferred gates

Nothing is required from the user. Installing or checking the preview remains optional; use `INSTALLATION.md` when ready. No live registrations or installations were changed.

Automated tests do not establish visual, clean-machine, real Chrome-native Run or semantic acceptance. Those checks, skipped symlink execution, scanner behavior, remote CI, signing, licensing clearance, public identities/hosting/store publication and Firefox/macOS/Linux certification remain unverified or deferred. The existing GPL-enabled FFmpeg/ffprobe and standalone Tcl-notice obligations are unchanged. Documentation updated using `update-agents-md`.
