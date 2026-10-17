# CueFlora

AI Subtitles & Translation for YouTube — independent Windows x64 / Chrome release candidate.

![Five-petal CueFlora flower](public/icon/flower.svg)

CueFlora combines available YouTube captions, optional AI transcription and optional AI translation. The flower button opens subtitle controls and the existing appearance editor. AI work starts only when you press Run.

## Pre-release status

Use the [final bounded release checklist](docs/FINAL_RELEASE_STATUS.md) for current status. Older handoffs are historical, not an expanding list of new requirements.

Source/privacy/help publication is separate from a software release. There is **no public installer or Chrome Store extension available yet**. Existing private previews remain preserved; they are not public downloads or redistribution approval. You can inspect the source and documented builds, but the ordinary-user installation path awaits the remaining release gates.

The source repository is public, and the prelaunch [privacy](https://tearsofthedawn.github.io/CueFlora/privacy.html), [release status](https://tearsofthedawn.github.io/CueFlora/download.html) and [help](https://tearsofthedawn.github.io/CueFlora/support.html) pages are live. Their response hashes were verified against the uploaded files on 2026-10-15. [Source/Pages preparation](docs/PUBLIC_SOURCE_AND_PAGES.md) documents the deployment. [GitHub Issues](https://github.com/TearsOfTheDawn/CueFlora/issues) is the selected public support channel; do not post credentials or private captures.

## Install the private preview

Extract the complete preview ZIP. Load its `Chrome-preview` folder through Chrome's Developer mode → Load unpacked. Run `CueFlora Setup.exe`, explicitly select Chrome and confirm Install. The installer includes Python and audio tools, requires no administrator access or PATH edits, and runs no persistent companion.

The settings page guides you through helper connection → AI connections → languages. Hosted and existing local services are equally supported; neither is preselected. Supply your service address, optional API key and model name independently for transcription/translation. Model checks request metadata only; they do not test subtitle generation. You can postpone AI setup and use available YouTube captions.

The polished preview preserves caption/AI choices, completion and failed-save drafts. Retry/Reload keeps edits and reconciles uncertain writes; helper readiness is separate from connectivity. Idle YouTube tabs refresh saved selections without generating subtitles. See [the polish handoff](docs/PRIVATE_PREVIEW_POLISH_HANDOFF.md).

See [installation/removal instructions](docs/INSTALLATION.md) and [implementation handoff](docs/IMPLEMENTATION_HANDOFF.md).

## Public installation after launch

Install the Chrome Store extension → download and run the matching Windows Setup → connect your existing AI services → choose languages → press Run. No Python, administrator access, PATH edits or persistent companion are required. Transcription needs a compatible `/audio/transcriptions` service; translation needs `/chat/completions` with structured JSON output. A website subscription or ChatGPT login is not necessarily API access. Service pricing/availability and output accuracy are outside CueFlora's control. Captions-only use can skip AI setup when the video provides suitable tracks.

The Store item and public installer downloads are not live yet. The Store draft identity/public key and prelaunch help locations are established; final artifacts and external release reviews remain separate. GitHub Releases will host matching binaries/sources, GitHub Pages privacy/install information, and GitHub Issues support. Do not use a keyless submission ZIP as an unpacked preview expecting it to match the development helper.

The intended first Store release is **public**, not a private testing release. Use the latest fully verified ZIP in the existing Store item when preparing the final submission rather than creating another item or uploading every intermediate build. Live installation/Run testing is deferred until after launch at the publisher's choice, not reported as passed. Genuine Store screenshots and the remaining licence, security/policy, download and Google review gates still apply. See [the public-launch checklist](docs/PUBLIC_LAUNCH_CHECKLIST.md).

Source 0.1.12 includes the original V8 submodule notices, full hash-locked Rust source delivery, labelled upstream-declaration/source-attribution records, explicit installer third-party terms and frozen solver configuration isolation. It retains the ICU correction, urllib3 patch, audited build tooling and per-file inventories. Subtitle processing and production audio-tool bytes do not change. The fresh candidate's verification and exact-bound assessment establish what was rebuilt and reviewed; earlier packages remain immutable. See [third-party review](docs/THIRD_PARTY_REVIEW.md). This is not an absolute security guarantee or Google approval.

## Status and boundaries

Version 0.1.12 retains corrected licence discovery and exact source/notice evidence. Historical missing-filename/lookup counts are not counts of shipped licence violations: original package declarations, supplied attribution, existing notices and actual source delivery are reviewed together. Store identity, clean-source/offline builds, synthetic audio checks and exact-bound review sidecars remain intact. See [third-party review](docs/THIRD_PARTY_REVIEW.md) and the [final checklist](docs/FINAL_RELEASE_STATUS.md). Software is not yet publicly released or Store-approved. The first installer is unsigned.

Windows/Chrome public-release preparation now includes bundled Deno, local EJS checks, hash-locked offline inputs, separate preview/keyless candidates and build-only automation. Use [the preparation command](docs/PUBLIC_RELEASE_PREPARATION.md), [handoff](docs/PUBLIC_RELEASE_HANDOFF.md) and [explicit release blockers](docs/PUBLIC_RELEASE_BLOCKERS.md). This is not public-release clearance; nothing is submitted automatically.

The previous 0.1.2 milestone introduced [Windows-protected remembered keys](docs/SECURE_CREDENTIALS.md), Keep/Replace/Remove, safe migration and store-candidate HTTPS. See its [historical security handoff](docs/SECURITY_HARDENING_HANDOFF.md). Subtitle processing remains unchanged; only the 0.1.3 candidate adopts the documented new audio tools after compatibility checks.

The preview is unsigned, not a public release. Stable development Chrome ID: `klnnagigpdlgchlablabnafceoldfalm`. It is separate from Substrata's extension, registration, settings, files and evidence. No settings or credentials are imported. No live installation or browser automation was performed during implementation.

Clean-machine and actual Chrome/native Run are deferred until after launch; GUI/scanner acceptance, signing, Store publication, redistribution clearance and macOS/Linux/Firefox certification remain unverified or separate future work. The keyless store-upload ZIP is a candidate, not approval to publish; the matching installer is bound to the supplied Store identity. ChatGPT sign-in and AI-service/model provisioning are not implemented.

## Development

Release builds pin official Node.js 24.19.0/npm 11.17.0; preparation restores and verifies them without system-wide installation. Source development needs Node 22.12+ or a compatible newer release. Install dependencies with `npm ci`. Run `npm test`, `npm run typecheck`, `npm run build:chrome` and `npm run build:firefox`. Chrome is the default for `dev`, `build` and `zip`. WXT 0.21.4 uses explicit Vite 8.3.4 and Vitest 4.1.12. Development servers do not launch browsers automatically; manually load the generated unpacked development extension if desired. `web-ext` is not required for either production build. Typechecking explicitly includes owned source/tests/configuration, not historical artifact trees, and retains the previous strict compiler contract.

Native development uses Python 3.10+ and httpx. Windows packaging uses Python 3.13.15, `packaging/requirements-windows-hashed.lock` and `packaging/inputs-windows.lock.json` in its own build environment. Exact wheel/tool/npm inputs are cached for offline rebuilding. [Distribution engineering](docs/DISTRIBUTION.md) records builds, automated evidence and outstanding gates. Do not run tests against live registrations.

Generated artifacts, environments, private configurations and captures are ignored. The source-copy baseline and original-preservation audit are under `artifacts/`; no original Git history or remote was copied. This is a fresh local repository without commits or remotes.

## Attribution and licence

CueFlora is a renamed derivative of [Substrata by jmviz](https://github.com/jmviz/substrata), incorporating subsequent local improvements. The original [MIT licence and copyright](LICENSE.md) are retained unchanged. No affiliation or upstream endorsement is implied.

The application licence does not establish clearance for all bundled third-party binaries. Available notices and inventories are included; unresolved obligations are documented in [the redistribution checklist](docs/REDISTRIBUTION_CHECKLIST.md). Do not publicly redistribute the generated package until that review is complete.
