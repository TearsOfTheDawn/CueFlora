# Changelog

User-facing changes, newest first. Candidate entries are explicitly unpublished; release links and publication receipts establish actual availability.

## [0.2.3](https://github.com/TearsOfTheDawn/CueFlora/releases/tag/v0.2.3) — 2026-10-22

### Fixes and improvements

- Fixed translation recovery exhausting its eight-call budget solely because flagged cues were scattered across a batch. Only rejected positions are grouped into a single aligned repair request; already accepted translations are retained.
- Keep original cue positions correct through sparse repairs, retries, splits and optional evidence capture. Intervening subtitles remain reference-only context.
- Workflow console diagnostics now record validation reason codes, affected source indexes and the last recovery request without retaining subtitle text in those added fields. Persistent malformed output still fails within the existing eight-call limit; no extra model calls or paid fallback are introduced.

### Upgrade and limitations

Published under separate authority; see [publication verification](docs/CUEFLORA_023_PUBLICATION.md). Finish Runs, use the update flow or matching Setup, click **Restart CueFlora** or CueFlora **Reload** at `chrome://extensions`, then reload YouTube tabs. Keep existing settings, keys and the extension identity. Valid cached subtitles remain compatible. The reproduced scheduling failure is covered by synthetic production-code tests; the original model outputs were not available, and automated checks do not establish semantic translation or live-browser acceptance. See [implementation and verification scope](docs/CUEFLORA_023_IMPLEMENTATION.md).

## [0.2.2](https://github.com/TearsOfTheDawn/CueFlora/releases/tag/v0.2.2) — 2026-10-22

### Fixes and improvements

- Fixed the reproduced downloader startup failure when Chrome keeps its helper connection open. Tool processes no longer inherit CueFlora's native-message input.
- Detached the user-confirmed Setup launch from native-message streams; install confirmation and all update integrity checks remain.
- Reject failed audio splits even if FFmpeg leaves a nonempty partial file. Audio settings, timing, normalization and translation request limits are unchanged.
- Prevent optional evidence-version checks from blocking subtitle generation; incomplete evidence stays a warning in normal Runs.
- Keep update/account tasks cancellable after status failures, release settings correctly after sign-in status-refresh failure, and preserve the account store when its limit is reached.
- Added persistent multi-message packaged tests and shared full native-suite discovery to catch the condition missed by closed-input probes.

### Upgrade and limitations

Finish Runs, download 0.2.2's matching Setup, confirm Upgrade, click CueFlora **Reload** at `chrome://extensions`, then reload YouTube tabs. Do not reset keys/models or remove/reinstall the extension. Manual Setup remains the fallback for older versions, including a stalled 0.2.1 launcher. See [audit and boundaries](docs/CUEFLORA_022_AUDIT.md) and [publication verification](docs/CUEFLORA_022_PUBLICATION.md). Automated checks do not establish live-browser or semantic acceptance.

## [0.2.1](https://github.com/TearsOfTheDawn/CueFlora/releases/tag/v0.2.1) — 2026-10-21

### Fixes and improvements

- Updated the bundled HTTPS certificate store to certifi 2026.10.19, addressing GHSA-6q48-6c7w-9gw2. The helper, Setup and downloader use the fixed, hash-pinned upstream bundle; TLS verification remains enabled.
- Fixed GitHub update checks being rejected with HTTP 415: JSON metadata and binary downloads now use the correct separate request headers.
- Transcription and translation failures now retain privacy-safe stages, reason codes and HTTP status instead of treating every protected-key request failure as a key problem.
- Added user-triggered **Debugging & support → Collect debug report → Copy report**. Reports contain versions, tool health and at most 20 recent failure codes, never credentials, service addresses, models, video IDs, subtitle text or raw provider responses. Browser-session memory preserves history across worker sleep; extension reload/update or browser restart clears it. Failed retention is reported without failing subtitle generation.
- Settings open in a full browser tab, with responsive provider cards, simpler navigation and compact saved-key controls. Save/Cancel, drafts and explicit Run are retained.

### Upgrade and limitations

0.2.0's broken update check cannot fetch this first repair automatically. Download 0.2.1's matching Setup manually, confirm Install / Upgrade, then click CueFlora **Reload** at `chrome://extensions` and reload YouTube tabs. Do not remove/reinstall the extension. Existing 0.1.13 users still follow the one-time folder-adoption steps below.

This patch improves diagnosis; it does not claim to resolve the original, still-unrecovered provider transcription failure or change subtitle/audio processing. No paid AI request or live installation is part of its automated verification. Visual and live-browser acceptance remain separate. The release URL and publication receipt, not this dated entry alone, establish publication.

## [0.2.0](https://github.com/TearsOfTheDawn/CueFlora/releases/tag/v0.2.0) — 2026-10-19

### New features

- Clearer AI setup: separate transcription and translation sections, plain-language field guidance and simpler saved-key controls.
- Optional **Continue with ChatGPT** for translation using eligible ChatGPT-plan models. This does not cover audio transcription or automatically switch to a paid API.
- One Setup download containing the matching Chrome extension, helper and audio tools.
- User-triggered in-app updates for later compatible releases, with verified downloads, explicit installation confirmation and an extension restart action. No silent installation or background updater.

### Fixes and improvements

- More reliable video/document checks when navigating between YouTube videos, while continuing to reject stale Runs and results.
- Audio-download progress and clearer processing stages, with cancellation and stalled-download timeouts.
- Stage-specific OpenRouter model discovery, bounded partial model lists and manual model entry when discovery is unavailable.
- Paired extension/helper repair, upgrade and rollback safeguards, plus recoverable adoption of a recognized existing extension folder.

### Upgrading from 0.1.13

**After Setup finishes, you must click CueFlora's Reload button at `chrome://extensions`, then reload your YouTube tabs. Otherwise Chrome can continue running the old extension.**

1. Finish all subtitle Runs and download **CueFlora-0.2.0-Setup.exe** from this release.
2. In Setup, select Chrome and click **Optional: select existing CueFlora extension folder…**. For this first upgrade, select the folder Chrome currently loads, containing `manifest.json`.
3. Choose **Install / Upgrade**, confirm adoption and the installation prompts, and wait for **Install complete**.
4. At `chrome://extensions`, enable Developer mode if needed and click CueFlora's circular-arrow **Reload** button. Reopen CueFlora settings and reload YouTube tabs. Both extension and helper should report **0.2.0**.

Keep the existing extension identity; do not remove/reinstall the extension or delete its folder. Settings, keys and evidence are preserved. Modified or foreign extension folders are refused rather than overwritten. This first upgrade is manual; the new in-app update flow is for later compatible releases.

### Known limitations

- Windows x64 / Google Chrome only. New installations still require Chrome's initial **Load unpacked** step.
- The installer is unsigned. Do not disable security software or automatically bypass warnings.
- Genuine ChatGPT login/plan eligibility, live in-app Chrome updating and clean-Windows acceptance remain unverified by automated checks.
- AI services/models are not installed or supplied. API services may charge, ChatGPT-plan limits apply to that optional route, and generated subtitles can be inaccurate. Only explicit **Run** starts subtitle generation.

## [0.1.13](https://github.com/TearsOfTheDawn/CueFlora/releases/tag/v0.1.13) — 2026-10-17

### Initial public GitHub release

- Windows x64 / Chrome package with the unpacked extension, on-demand native helper and bundled audio tools.
- User-supplied transcription and translation services, available YouTube captions, explicit Run and subtitle appearance controls.
- Windows-protected remembered API keys, provider-neutral setup and per-user helper installation/maintenance.
- Original third-party notices, corresponding sources, dependency evidence and checksums supplied with the release.

### Installation and limitations

This release used the complete Windows ZIP, manual **Load unpacked**, and separate confirmation of helper installation. It did not include ChatGPT sign-in or the 0.2.0 in-app update flow. Its unsigned-installer warning and deferred clean-machine/real-browser acceptance are retained in the historical release notes. Use the 0.2.0 instructions above when upgrading it.
