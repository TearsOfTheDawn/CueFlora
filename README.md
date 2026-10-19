# CueFlora

AI Subtitles & Translation for YouTube — Windows x64 / Google Chrome.

**Current release: 0.2.0.** Clearer setup, optional ChatGPT-plan translation and a matching extension/helper installer. See [implementation and acceptance boundaries](docs/CUEFLORA_020_IMPLEMENTATION.md). Earlier packages, including 0.1.13, remain available.

![Five-petal CueFlora flower](public/icon/flower.svg)

Use available YouTube captions, or your own compatible AI services for transcription and translation. The flower button opens subtitle controls and appearance settings. AI generation starts only when you press **Run**.

## Install from GitHub

### [Download CueFlora Setup.exe — the only required download](https://github.com/TearsOfTheDawn/CueFlora/releases/download/v0.2.0/CueFlora-0.2.0-Setup.exe)

Setup contains the matching Chrome extension, helper and audio tools. You do not need the other files under Assets for normal installation. AI services and models are separate.

1. Download and run Setup. Select Chrome, read Third-party terms, and confirm **Install**.
2. Open `chrome://extensions`, enable **Developer mode**, select **Load unpacked**, and choose the stable extension folder shown by Setup (normally `%LOCALAPPDATA%\CueFlora\Chrome-extension`). Keep this folder.
3. Open CueFlora settings: check the helper, connect existing AI services or explicitly choose ChatGPT for translation only, save, and choose languages.
4. On YouTube, open the flower button and press **Run**.

The installer bundles Python, yt-dlp, FFmpeg/ffprobe and Deno. It needs no administrator access, separate Python installation or PATH changes. The helper runs on demand; it is not a continuously running companion. Setup supplies the extension folder, but Chrome's initial Load unpacked step remains manual. It does not install AI services.

Transcription requires a compatible `/audio/transcriptions` API. Translation uses either your `/chat/completions` service with structured JSON Schema output or optional **Continue with ChatGPT**. Supply your service's API address, optional access key and exact model ID; no provider/model is preselected. Local services must already be running. The ChatGPT route uses eligible plan models/limits and does not cover transcription or silently switch to a paid API. Available captions can be used without AI configuration.

The [download page](https://tearsofthedawn.github.io/CueFlora/download.html) has the same installation steps, optional technical files and hashes. Chrome Web Store publication is not planned. This is Chrome's manual Developer-mode installation route.

## Updates and removal

**Upgrading from 0.1.13:** finish all Runs, download this Setup manually, select the currently loaded CueFlora extension folder, and confirm adoption/Upgrade. Only recognized, unmodified files are accepted; a recoverable backup is kept. Click **Reload** once in Chrome's Extensions page, then reload YouTube tabs. Do not remove/reinstall the extension; its ID and settings must stay unchanged.

**Later compatible releases:** in settings choose **Check for updates → Download update → Install update**, confirm Setup, then **Check installation → Restart CueFlora** and reload YouTube tabs. There is no silent installation, resident updater or scheduled task. Matching Setup plus manual Chrome Reload remains the fallback.

The Start Menu maintenance launcher offers **Repair**, **Roll back** and recoverable **Uninstall**. Uninstall preserves settings/evidence and quarantines runtime files; remove the browser extension separately if desired. Older development previews have a different identity: do not mix their helpers or promise that settings transfer between IDs. CueFlora does not modify Substrata.

## Privacy and limitations

Remembered API keys use user-scoped Windows DPAPI; existing plaintext keys are never returned by settings. ChatGPT tokens remain exclusively in the helper's protected native account store. This does not protect against malware running as you. Remote services require HTTPS; exact loopback HTTP exceptions support existing local services. Provider redirects are rejected. Audio/text and relevant metadata are sent to the services you choose. Optional local evidence capture is off unless enabled. See [Privacy](https://tearsofthedawn.github.io/CueFlora/privacy.html) and [credential details](docs/SECURE_CREDENTIALS.md).

The installer is unsigned. Do not disable antivirus or automatically bypass warnings. Checksums establish file identity, not guaranteed safety. Hosted AI can cost money; subtitles can be wrong. Use content you are entitled to process and comply with applicable terms and law.

Genuine ChatGPT login, live Chrome updating, clean-machine acceptance and semantic subtitle quality remain unverified; automated checks are not those tests. Firefox/macOS/Linux are not certified. There is no unattended update, model installation or AI-service provisioning.

## For developers and verification — optional

All application source, build scripts, pinned dependency inputs, inventories, notices and corresponding third-party sources are reviewable. Windows packaging runs offline after obtaining exact public, hash-locked inputs. Two fresh builds distinguish measured metadata differences from actual payload changes. Build provenance is not a guarantee that software is harmless.

For development: `npm ci`, `npm test`, `npm run typecheck`, `npm run build:chrome`, `npm run build:firefox`. Release Node/npm and Python/tool versions are pinned by the packaging locks. [GitHub distribution](docs/GITHUB_DISTRIBUTION.md) documents the complete build/review/publication path; [current status](docs/FINAL_RELEASE_STATUS.md) distinguishes engineering from live publication. Never run installation tests against live registrations.

Report problems through [GitHub Issues](https://github.com/TearsOfTheDawn/CueFlora/issues). Include versions, failing step and redacted reason codes; never post API keys, protected credential payloads, signed URLs or private captures.

## Attribution and licence

CueFlora is a renamed derivative of [Substrata by jmviz](https://github.com/jmviz/substrata), incorporating subsequent local improvements. The original [MIT licence and copyright](LICENSE.md) are retained unchanged. No upstream affiliation or endorsement is implied.

Bundled components keep their own licences. Release assets include original notices, corresponding sources, build recipes and a file-by-file dependency ledger. See [third-party review](docs/THIRD_PARTY_REVIEW.md). The application MIT licence does not replace those obligations.
