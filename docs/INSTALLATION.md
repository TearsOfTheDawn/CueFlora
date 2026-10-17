# CueFlora private preview: install and remove

This guide is only for development-identity private previews. Public-identity candidates must use their own generated `START_HERE.md` and matching `Chrome-acceptance` folder; do not mix identities/helpers or treat an older package as updated by source changes. Public release remains gated by the current candidate's reports and [launch checklist](PUBLIC_LAUNCH_CHECKLIST.md).

Windows x64 / Google Chrome only. This is unsigned development software, not a published Chrome Web Store release. Installation/testing is optional; existing Substrata can remain installed unchanged.

## Install

1. Extract the complete `CueFlora-Windows-x64-Chrome-preview.zip`. Keep the extracted `Chrome-preview` folder in a stable location.
2. Open Chrome's Extensions page, enable Developer mode, choose **Load unpacked**, and select `Chrome-preview`. CueFlora settings open once on first installation. Its development ID must be `klnnagigpdlgchlablabnafceoldfalm`.
3. Run the single **CueFlora Setup.exe**, select Chrome, choose **Install / Upgrade**, and confirm. No administrator access, Python installation, PATH edits or manual manifests are needed. CueFlora will not silently install the browser extension, AI services or models.
4. In CueFlora settings, choose **Check helper connection**. Audio preparation needs yt-dlp, ffmpeg, ffprobe and Deno; saved keys also need the helper's Windows-protection capability. Use the matching Setup's Repair/Upgrade if missing. Configure your transcription and/or translation service, or postpone AI setup. Supply the service's API base address, key when required, and exact model name. Save explicitly. Advanced processing defaults can remain unchanged.
5. Choose languages and explicitly select native captions or configured AI for each stage (translation can be Off), then finish. Native captions depend on the video and may be unavailable in your chosen language. On YouTube, open the flower button and press **Run** when you want AI subtitles.

Unsigned files may trigger Windows/security warnings. Scanner behaviour for this CueFlora artifact has not been certified. Do not automatically bypass a security warning. Checksums detect accidental modification, not publisher authenticity.

The helper runs only on demand. Close Setup after installation. Chrome stores settings independently for this preview; remembered API keys use your Windows account's DPAPI protection, not plaintext storage. This is not protection against malware running as you. Hosted inference may incur your provider's charges. Local services must already be running.

Settings show **API key saved** without revealing the key. Choose Keep, Replace or Remove. Changing a service address requires a new key or explicit reuse confirmation. Upgrade the helper before migrating old keys; if migration/cleanup fails, the original is retained with a warning and **Retry protected key migration** is available. Caption-only/keyless services remain usable. See `SECURE_CREDENTIALS.md` for migration, privacy and older-helper boundaries. Store candidates require HTTPS for remote services; this preview retains acknowledged remote HTTP for compatibility, with an explicit data/credential exposure risk.

Transcription requires a compatible `/audio/transcriptions` API. Translation requires `/chat/completions` supporting structured JSON Schema output. GET `/models` success verifies metadata access only, not actual ASR/translation compatibility. If model listing is unsupported, enter the model manually. No ChatGPT-account sign-in is provided.

## If setup cannot save

Your edits remain available after a failed Save. Cancel restores successfully saved AI/Advanced settings. Label-only edits also require Save or Cancel before proceeding.

Use **Retry loading settings** after an initialization failure. **Reload saved state (keep edits)** rereads persisted state without discarding your visible edits; review them before saving, or Cancel to restore saved AI values. If another settings tab changed the providers, reload before trying again.

A settings request expires after 15 seconds (helper/model checks have a 10-second native limit). A timed-out write may still have completed: further saves are blocked until you explicitly reload saved state. CueFlora never blindly retries a write or inference. If languages saved but setup progress failed, the message says so; reload before finishing again.

Completed setup stays completed when revisited. Saved language selections refresh in idle YouTube tabs on focus or panel opening, without inference. Active Runs and appearance drafts remain unchanged.

## Repair, upgrade and roll back

Open **CueFlora Setup** from the Start Menu or run the downloaded installer again. The Start Menu entry points to a versioned maintenance copy that includes its matching payload.

- **Repair** reinstalls the payload matching the current installation's recorded identity/inventory binding. If using a different downloaded version, use the current Start Menu launcher or Install / Upgrade instead.
- **Install / Upgrade** requires explicit Chrome selection and confirmation, then activates a verified new runtime. It cannot change the recorded extension ID.
- **Roll back** restores the previous runtime, release binding and maintenance entry.

A rollback to a helper without Windows key protection cannot run saved-key AI requests; Upgrade again. Do not downgrade the extension after its v2 provider migration; older extension versions cannot read v2. Installation never converts encrypted keys to plaintext or changes an active Run's frozen configuration.

Conflicting registrations or modified/foreign Start Menu entries are refused, not taken over. Restart/retry Setup after an interrupted operation; the journal restores the previous owned state before continuing.

## Remove

Use **Uninstall** in CueFlora Setup and confirm. It removes only CueFlora-owned native registration and Start Menu entry. Runtime versions are moved into a recoverable `removed-...` folder under `%LOCALAPPDATA%\CueFlora`. Maintenance executables remain for recovery; removal intentionally does not reclaim all disk space. Browser settings and evidence remain untouched. Remove the CueFlora extension separately in Chrome if desired. Never delete or repair Substrata to remove CueFlora.

## Optional headless reports

These do not open a GUI, install or verify real browser registration. Use fresh report filenames:

```powershell
& '.\CueFlora Setup.exe' self-check --report '.\self-check.json'
& '.\CueFlora Setup.exe' validate-package --report '.\payload.json'
& '.\CueFlora Setup.exe' detect --report '.\browsers.json'
```

CLI mutations require `--apply`; install additionally requires explicit `--browser chrome`. Reports never overwrite existing files. Actual clean-machine/browser/GUI testing remains optional and deferred for this milestone.

Install and repair also require `--accept-third-party-terms`. Read them with `CueFlora Setup.exe terms`; in the GUI use **Third-party terms** before the existing confirmation. Original component licences remain authoritative. Keep `CueFlora-third-party-sources.zip` with binary redistribution, including the LGPL/GPL/MPL sources and recipes. This acknowledgement does not restrict open-source rights or require agreement to uninstall.

## Not a public distribution

The included keyless `CueFlora-Chrome-store-upload.zip` is a future-upload candidate. Do not load it instead of `Chrome-preview` for this installer: the preview key is intentionally absent. Final store ID, matching release package, store approvals, signing and third-party redistribution clearance remain separate work.
