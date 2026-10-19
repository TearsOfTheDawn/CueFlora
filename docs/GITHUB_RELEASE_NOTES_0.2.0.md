# CueFlora 0.2.0 — Windows & Chrome

## [Download CueFlora Setup.exe — the only required download](https://github.com/TearsOfTheDawn/CueFlora/releases/download/v0.2.0/CueFlora-0.2.0-Setup.exe)

Setup includes the matching Chrome extension, native helper and audio tools. AI services/models are separate. The installer is unsigned. Do not disable security software.

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

### New users

1. Run Setup, select Chrome, read the terms and confirm Install.
2. Open chrome://extensions, enable Developer mode and Load unpacked from the stable folder shown by Setup (normally %LOCALAPPDATA%\CueFlora\Chrome-extension). Keep this folder.
3. Open CueFlora settings, connect existing AI services or optionally ChatGPT for translation only, Save, choose languages and press Run on YouTube. No Python, administrator access or PATH edits are required.

### Optional files and help

[Complete Windows ZIP](https://github.com/TearsOfTheDawn/CueFlora/releases/download/v0.2.0/CueFlora-0.2.0-Windows-x64.zip) is an alternative, not another required download. Sources, original notices, dependency evidence, checksums and update metadata accompany this release.

[Full changelog](https://github.com/TearsOfTheDawn/CueFlora/blob/main/CHANGELOG.md) · [Installation help](https://tearsofthedawn.github.io/CueFlora/download.html) · [Report a problem](https://github.com/TearsOfTheDawn/CueFlora/issues)

Process only content you are entitled to use under applicable terms and law.
