# CueFlora Windows/Chrome release candidate

This is an unsigned Windows x64 / Chrome candidate, not a published or store-approved release. The fresh `readiness.json` and handoff record measured results. Earlier previews, Substrata and the subtitle pipeline remain preserved.

## Simple final installation flow

1. Install CueFlora from its Chrome Web Store listing.
2. Download the matching **CueFlora Setup.exe** from the publisher's HTTPS download page.
3. Run Setup, select Chrome and confirm Install. Windows may warn because it is unsigned. No administrator access, Python installation or PATH editing is needed.
4. In extension settings, check the helper, enter existing AI service addresses/optional keys/model names, Save and choose languages.
5. On YouTube, open the flower button and press Run. Available captions can be used without AI/helper. API use may cost money; models/services are not installed or chosen for you.

This flow is for after launch; the Store item and public installer are not released yet. Source and prelaunch privacy/help pages are public. The publisher's Store draft ID/public key and support locations are established, but construction does not grant release approval. Nothing silently installs the extension.

For optional local use, follow the delivered `START_HERE.md`: private packages include `Chrome-preview`; a public-identity test package includes `Chrome-acceptance` only when the actual matching Store key is available. The keyless submission ZIP is not an unpacked preview. Setup refuses a different installed CueFlora identity; remove that helper through its own Setup first if choosing to replace it. Never change Substrata.

## Documented audio tools

FFmpeg/ffprobe 9.0.2 use official signature-verified source and hash-locked portable MSYS2/UCRT64 compiler packages. Opus 1.6.1 uses its official checksum. The actual FFmpeg binaries report LGPL 2.1-or-later; GPL/nonfree components and network protocols are disabled. Sources, build commands, dependency notices and exact executable/shared-library hashes accompany the build. This does not automatically settle every dependency/patent obligation.

Production preparation remains 48 kHz mono / 24 kbps Opus, with unchanged chunking/inference settings. Synthetic tests use the production compressor/chunker for WAV, AAC/M4A, MP3, FLAC, Vorbis/Ogg and Opus/WebM. PCM differences, sizes and times are measurements, not ASR/translation-quality scores. No inference runs during preparation.

## Build from public source

Developers need Python 3.11+ for bootstrap. Packaging restores the exact official Python 3.13.15 archive, hash-locked wheels and pinned Node/npm; a global Node installation is not required by the Python preparation command. Ordinary users need none of these build tools. Neither a private Python snapshot nor the former FFmpeg executables are needed to build the candidate.

```powershell
python packaging/bootstrap_public_cache.py --cache artifacts/inputs --audio-cache artifacts/audio-inputs --evidence-cache artifacts/evidence --online
python packaging/bootstrap_offline.py --cache artifacts/inputs --output artifacts/build-python --official
artifacts/build-python/venv/Scripts/python.exe packaging/prepare_windows.py --output artifacts/fresh-candidate --cache artifacts/inputs --evidence-cache artifacts/evidence --audio-cache artifacts/audio-inputs --online
```

Versions, origins and hashes are fixed. The first preparation allows only exact locked downloads, including filling the npm cache. For offline repetition choose a fresh output and omit `--online`; missing/mismatched inputs fail. No runtime self-update, remote component download or latest-version substitution occurs. Source builds use the public synthetic audio policy/fixtures; the historical private adoption comparison is not a prerequisite and must not be fabricated. Old/private tools are not publicly downloaded or redistributed as prerequisites.

Preparation restores the portable compiler and builds audio when using `--audio-cache`. Alternatively `--audio-build <accepted-build>` copies/reverifies a preserved source build without modifying it. The npm wrapper can use `CUEFLORA_BUILD_PYTHON` to select the official bootstrap's venv Python. Preparation compares two fresh runtime/Setup builds, exports audited source and runs suites/builds again from that exact clean export with import/capture overrides removed. Substrata preservation runs only where the private original-copy baseline exists; independent checkouts do not access Substrata.

The source-only archive excludes private captures/environments/build outputs. A separate `CueFlora-third-party-sources.zip` contains available matching audio sources and partial dependency evidence, independently inventory/hash-verified. It deliberately does not claim complete corresponding-source closure. Source/runtime/readiness records share a canonical source-inventory hash; the pretty JSON report has its own separate file hash.

## Identity and approval gates

Schema 2 `--public-config` constructs an exact-bound candidate using actual publisher, Store-assigned Chrome ID/public key and HTTPS privacy/download/support locations. Keep release/redistribution flags false; external decisions remain separately hash-bound and pending. Candidate construction is not declaration or approval of licensing, security, policy, Windows/Chrome acceptance or publication. Credentials are forbidden in this configuration. Public runtimes enforce remote HTTPS even if a client requests preview policy. Schema 1 installation records remain compatible.

External acceptance can happen before public authorization: build an HTTPS runtime and use Setup's `--private-chrome-id <actual-assigned-ID>`. That remains a private, unapproved, inventory-bound package. Uninstall the matching preview helper in the test environment first rather than taking over its registration; settings/evidence remain. Upgrade/repair/rollback preserve recorded identities.

The preparation command sets `CUEFLORA_PUBLIC_CONFIG` for matching `acceptance` and keyless `store-candidate` extension builds. Preview builds reject public-helper links. No provider is selected and links do not perform automatic requests.

## What still blocks publication

- Review remaining yt-dlp/curl/BoringSSL, Deno/V8, Python/native and compiler-runtime source/licence obligations. Full file inventory is not legal clearance.
- Resolve native YouTube download/challenge-execution policy questions. A disclaimer is not a remedy; architectural changes require separate approval.
- Actual publisher/Store identity, GitHub Issues support and prelaunch help locations are established. Final downloadable-artifact hosting, genuine screenshots and clean Windows/real Chrome acceptance remain separate gates.
- Obtain store approval and explicit publication authorization. Signing is optional for this first release, not a promise of warning-free installation.

No identity, account, screenshot, installation, live browser or semantic acceptance is fabricated. Build attestations establish origin, not safety. Publication aliases remain disabled.
