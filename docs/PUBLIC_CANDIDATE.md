# CueFlora 0.1.3 public-release preparation

This is an unsigned Windows x64 / Chrome candidate, not a published or store-approved release. The fresh `readiness.json` and handoff record measured results. Earlier previews, Substrata and the subtitle pipeline remain preserved.

## Simple final installation flow

1. Install CueFlora from its Chrome Web Store listing.
2. Download the matching **CueFlora Setup.exe** from the publisher's HTTPS download page.
3. Run Setup, select Chrome and confirm Install. Windows may warn because it is unsigned. No administrator access, Python installation or PATH editing is needed.
4. In extension settings, check the helper, enter existing AI service addresses/optional keys/model names, Save and choose languages.
5. On YouTube, open the flower button and press Run. Available captions can be used without AI/helper. API use may cost money; models/services are not installed or chosen for you.

Public links and identity are deliberately unset until supplied by the publisher. The private candidate instead uses its matching unpacked Chrome-preview. Nothing silently installs the extension.

## Documented audio tools

FFmpeg/ffprobe 9.0.2 use official signature-verified source and hash-locked portable MSYS2/UCRT64 compiler packages. Opus 1.6.1 uses its official checksum. The actual FFmpeg binaries report LGPL 2.1-or-later; GPL/nonfree components and network protocols are disabled. Sources, build commands, dependency notices and exact executable/shared-library hashes accompany the build. This does not automatically settle every dependency/patent obligation.

Production preparation remains 48 kHz mono / 24 kbps Opus, with unchanged chunking/inference settings. Synthetic tests use the production compressor/chunker for WAV, AAC/M4A, MP3, FLAC, Vorbis/Ogg and Opus/WebM. PCM differences, sizes and times are measurements, not ASR/translation-quality scores. No inference runs during preparation.

## Build from public source

Developers need Node.js 22.12+ and Python 3.11+ for bootstrap. Packaging restores the exact official Python 3.13.15 archive and hash-locked wheels. Neither a private Python snapshot nor the former FFmpeg executables are needed to build the new candidate.

```powershell
python packaging/bootstrap_public_cache.py --cache artifacts/inputs --audio-cache artifacts/audio-inputs --evidence-cache artifacts/evidence --online
python packaging/bootstrap_offline.py --cache artifacts/inputs --output artifacts/build-python --official
node scripts/cache-npm.mjs artifacts/inputs/npm
python packaging/audio_build.py --cache artifacts/audio-inputs --output artifacts/compiler --bootstrap
artifacts/build-python/venv/Scripts/python.exe packaging/audio_build.py --cache artifacts/audio-inputs --toolchain artifacts/compiler/msys64 --output artifacts/audio-build --jobs 4
```

Versions, origins and hashes are fixed; offline repetition refuses missing/mismatched inputs. No runtime self-update, remote component download or latest-version substitution occurs. Native release adoption requires the included production-baseline compatibility evidence; independent builds must not forge that acceptance. Old/private tools are not publicly downloaded or redistributed as prerequisites.

The fully verified local preparation command adds `--audio-build <accepted-build>` to `npm run release:prepare`. `CUEFLORA_BUILD_PYTHON` can point to the official bootstrap's venv Python. Preparation compares two fresh runtime/Setup builds and exports audited source. Substrata preservation runs only where the private original-copy baseline exists; independent checkouts do not access Substrata.

The source-only archive excludes private captures/environments/build outputs. A separate `CueFlora-third-party-sources.zip` contains available matching audio sources and partial dependency evidence, independently inventory/hash-verified. It deliberately does not claim complete corresponding-source closure. Source/runtime/readiness records share a canonical source-inventory hash; the pretty JSON report has its own separate file hash.

## Identity and approval gates

Public installer mode requires the actual publisher, store-assigned Chrome ID, real HTTPS privacy/download/support locations, source/runtime hashes and explicit licence/security/policy/Windows/Chrome acceptance declarations. Credentials are forbidden in this configuration. Public runtimes enforce remote HTTPS even if a client requests preview policy.

External acceptance can happen before public authorization: build an HTTPS runtime and use Setup's `--private-chrome-id <actual-assigned-ID>`. That remains a private, unapproved, inventory-bound package. Uninstall the matching preview helper in the test environment first rather than taking over its registration; settings/evidence remain. Upgrade/repair/rollback preserve recorded identities.

`CUEFLORA_PUBLIC_CONFIG` supplies real installation/privacy/support links only to store-candidate extension builds. Preview builds reject public-helper links. No provider is selected and links do not perform automatic requests.

## What still blocks publication

- Review remaining yt-dlp/curl/BoringSSL, Deno/V8, Python/native and compiler-runtime source/licence obligations. Full file inventory is not legal clearance.
- Resolve native YouTube download/challenge-execution policy questions. A disclaimer is not a remedy; architectural changes require separate approval.
- Supply publisher/repository/contact, assigned store ID and hosted pages; obtain genuine screenshots and clean Windows/real Chrome acceptance.
- Obtain store approval and explicit publication authorization. Signing is optional for this first release, not a promise of warning-free installation.

No identity, account, screenshot, installation, live browser or semantic acceptance is fabricated. Build attestations establish origin, not safety. Publication aliases remain disabled.
