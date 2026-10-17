# CueFlora

AI Subtitles & Translation for YouTube — Windows x64 / Google Chrome.

![Five-petal CueFlora flower](public/icon/flower.svg)

Use available YouTube captions, or your own compatible AI services for transcription and translation. The flower button opens subtitle controls and appearance settings. AI generation starts only when you press **Run**.

## Install from GitHub

1. Open [Releases](https://github.com/TearsOfTheDawn/CueFlora/releases/latest) and download the complete **CueFlora-0.1.13-Windows-x64.zip**. Extract it to a permanent folder.
2. Open `chrome://extensions`, enable **Developer mode**, select **Load unpacked**, and choose `CueFlora Setup/Chrome-extension` from the extracted package. Keep this folder.
3. Run the included **CueFlora Setup.exe**, select Chrome, read Third-party terms, and confirm **Install**.
4. Open CueFlora settings: check the helper, connect your existing AI services, save, and choose languages. On YouTube, open the flower button and press **Run**.

The installer bundles Python, yt-dlp, FFmpeg/ffprobe and Deno. It needs no administrator access, separate Python installation or PATH changes. The helper runs on demand; it is not a continuously running companion. Setup does not install the extension or AI services.

Transcription requires a compatible `/audio/transcriptions` API; translation requires `/chat/completions` with structured JSON Schema output. Supply your API address, optional key and exact model name for each stage. Neither a provider nor a model is preselected. Local services must already be running. ChatGPT/other website subscriptions are not necessarily API access. Available captions can be used without AI configuration.

Release links become usable only after the corresponding assets are published. The [download page](https://tearsofthedawn.github.io/CueFlora/download.html) provides the current hosted version and hashes. Chrome Web Store publication is not planned. This is Chrome's manual Developer-mode installation route.

## Updates and removal

Keep the same extension folder and key/ID. Replace its files with the new release and click **Reload** in Chrome's Extensions page, then reload YouTube tabs. Do not remove/reinstall the extension just to update it. Run the matching Setup for helper upgrades. Settings remain associated with the same Chrome ID.

The Start Menu maintenance launcher offers **Repair**, **Roll back** and recoverable **Uninstall**. Uninstall preserves settings/evidence and quarantines runtime files; remove the browser extension separately if desired. Older development previews have a different identity: do not mix their helpers or promise that settings transfer between IDs. CueFlora does not modify Substrata.

## Privacy and limitations

Remembered API keys use user-scoped Windows DPAPI; existing plaintext keys are never returned by settings. This does not protect against malware running as you. Remote services require HTTPS; exact loopback HTTP exceptions support existing local services. Provider redirects are rejected. Audio/text and relevant metadata are sent to the services you choose. Optional local evidence capture is off unless enabled. See [Privacy](https://tearsofthedawn.github.io/CueFlora/privacy.html) and [credential details](docs/SECURE_CREDENTIALS.md).

The installer is unsigned. Do not disable antivirus or automatically bypass warnings. Checksums establish file identity, not guaranteed safety. Hosted AI can cost money; subtitles can be wrong. Use content you are entitled to process and comply with applicable terms and law.

Automated tests are not clean-machine or actual Chrome/native Run acceptance; those checks remain deferred. Firefox/macOS/Linux are not certified. There is no automatic extension update, ChatGPT sign-in, model installation or AI-service provisioning.

## Source and verification

All application source, build scripts, pinned dependency inputs, inventories, notices and corresponding third-party sources are reviewable. Windows packaging runs offline after obtaining exact public, hash-locked inputs. Two fresh builds distinguish measured metadata differences from actual payload changes. Build provenance is not a guarantee that software is harmless.

For development: `npm ci`, `npm test`, `npm run typecheck`, `npm run build:chrome`, `npm run build:firefox`. Release Node/npm and Python/tool versions are pinned by the packaging locks. [GitHub distribution](docs/GITHUB_DISTRIBUTION.md) documents the complete build/review/publication path; [current status](docs/FINAL_RELEASE_STATUS.md) distinguishes engineering from live publication. Never run installation tests against live registrations.

Report problems through [GitHub Issues](https://github.com/TearsOfTheDawn/CueFlora/issues). Include versions, failing step and redacted reason codes; never post API keys, protected credential payloads, signed URLs or private captures.

## Attribution and licence

CueFlora is a renamed derivative of [Substrata by jmviz](https://github.com/jmviz/substrata), incorporating subsequent local improvements. The original [MIT licence and copyright](LICENSE.md) are retained unchanged. No upstream affiliation or endorsement is implied.

Bundled components keep their own licences. Release assets include original notices, corresponding sources, build recipes and a file-by-file dependency ledger. See [third-party review](docs/THIRD_PARTY_REVIEW.md). The application MIT licence does not replace those obligations.
