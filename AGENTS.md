# AGENTS.md — CueFlora Project Reference

> **Last updated:** 2026-10-17
>
> This document is the canonical AI agent onboarding reference for the independent CueFlora project.
> After making changes, use the update skill described at the bottom of this file.

---

## Project Overview

**CueFlora — AI Subtitles & Translation for YouTube** is an independent Windows x64 / Chrome release candidate derived from Substrata that provides advanced multilingual subtitles for YouTube. It combines three subtitle sources:

1. **YouTube's native caption tracks** — fetched via YouTube's JSON3/VTT APIs
2. **AI transcription** — audio downloaded via yt-dlp, compressed with ffmpeg, transcribed via Whisper-compatible APIs (OpenAI, Groq, etc.)
3. **AI translation** — source subtitles sent to LLM chat completions APIs (Gemini, GPT, etc.) for translation

The extension uses a **native messaging host** (Python) for audio download, compression, and API calls that cannot be made from the browser sandbox.

The source copy includes current uncommitted improvements, without Substrata Git history/remotes, captures, credentials, environments, backups or old outputs. Original MIT licence and attribution to jmviz are retained. Do not modify or install into Substrata. Computer Use and browser automation are prohibited. Only explicit Run generates AI subtitles.

---

## Technology Stack

| Layer | Technology | Notes |
|---|---|---|
| Extension framework | [WXT](https://wxt.dev/) 0.21.4 / Vite 8.3.4 | Manifest V3, Chrome and Firefox regression builds; no automatic browser launcher |
| Extension language | TypeScript (strict mode) | Source and Vitest tests use `.ts` |
| Type checking | TypeScript 6.0+ | `tsc --noEmit` via `npm run typecheck` |
| Testing | Vitest 4.1.12 + jsdom, Python unittest | 293 TypeScript tests; 98 native/setup tests (96 pass, 2 Windows symlink-privilege skips); 145 packaging tests; 8 Node profile/release tests; frozen 0.1.9 preparation had 95 native/setup and 135 packaging tests; fresh logs remain authoritative |
| Styling | Plain CSS | Injected into YouTube player |
| Native host | Python 3.10+ | Bundled in the preview; uv remains a developer option; PING reports tool health |
| HTTP client (Python) | httpx | For Whisper & LLM API calls |
| Audio download | yt-dlp (bundled CLI) | Sibling tools in frozen runtime, explicit developer overrides retained |
| Audio processing | FFmpeg/ffprobe 9.0.2 (shared source builds) | Signature-verified core; Opus 1.6.1; unchanged production preparation/chunking; older previews retained |
| Challenge runtime | Deno 2.9.7 (official Windows x64) | Explicit frozen path; local EJS verified; no remote components/self-updates |
| Chinese pinyin | pinyin-pro (npm) | Ruby annotations for Chinese subtitles |

---

## Directory Structure

```
cueflora/
├── wxt.config.ts              # WXT build config, manifest definition
├── tsconfig.json              # Extends .wxt/tsconfig.json (strict mode)
├── vitest.config.ts           # Vitest config with WxtVitest plugin
├── package.json               # npm scripts, dependencies
├── entrypoints/               # WXT entrypoints (extension code)
│   ├── background.ts          # Service worker — native messaging bridge
│   ├── bridge.content.ts      # MAIN world content script — YouTube player API access
│   ├── options/               # Resumable helper → AI → languages onboarding and settings
│   ├── __tests__/             # Background service worker tests
│   │   └── background.test.ts
│   └── youtube.content/       # ISOLATED world content script — main UI & logic
│       ├── index.ts            # Entry point: init, navigation handling, auto-load
│       ├── api.ts              # Subtitle fetching, LLM translation, Whisper transcription
│       ├── render.ts           # Overlay rendering plus explicit Run workflow orchestration
│       ├── ui.ts               # Settings panel, dropdowns, event handlers
│       ├── appearanceEditor.ts # Draft appearance editor, preview, geometry and migration lifecycle
│       ├── style.css           # All extension CSS (panel, overlay, controls)
│       └── __tests__/          # Content script tests
│           ├── render.test.ts
│           ├── api-batching.test.ts
│           ├── api-cache.test.ts
│           ├── translation-recovery.test.ts
│           ├── quality-capture.test.ts
│           ├── ui-logic.test.ts
│           └── data-contracts.test.ts
├── utils/                     # Shared utility modules
│   ├── types.ts                # Central type definitions (Cue, Word, Language, State, etc.)
│   ├── constants.ts            # Storage keys, API defaults, LANGUAGES array (70+ languages)
│   ├── state.ts                # Global mutable state singleton (typed as AppState)
│   ├── workflowState.ts        # Pure initial workflow-state factory
│   ├── workflow.ts             # Workflow transitions, job identity, progress, diagnostics
│   ├── translation.ts          # Pure contextual batching and bounded recovery engine
│   ├── translationPresentation.ts # Pure English CPS timing, extension, and cue merging
│   ├── cache.ts                # Cue fingerprint and versioned translation-cache metadata
│   ├── log.ts                  # Logging helper + getVideoId()
│   ├── parsers.ts              # JSON3 and VTT subtitle parsers
│   ├── ruby.ts                 # Ruby annotation system (pinyin provider registered here)
│   ├── providers.ts            # Validated private provider records and revision summaries
│   ├── credentials.ts          # Strict protected-credential contract and key actions
│   ├── releasePolicy.ts        # Compile-time preview/store-candidate transport policy
│   ├── publicLinks.ts          # Safe settings-only public installation/privacy/support links
│   ├── userRun.ts              # Browser-trusted Run input; page-generated clicks cannot invoke AI
│   ├── providerClient.ts       # Content-side provider summary and Run binding bridge
│   ├── navigation.ts           # Shared navigation-generation guards for async consumers
│   ├── nativeResponse.ts       # Native envelope validation and diagnostic redaction
│   ├── controlledEvidence.ts   # Evaluation-only final completeness gate
│   ├── requestValidation.ts    # Client shape/size/identity validation before native dispatch
│   ├── preferences.ts          # Background preference validation and migration service
│   ├── onboarding.ts           # Revision-validated Finish; combined language write, separate completion marker
│   ├── settingsRequest.ts      # 15-second settings deadlines, no automatic retries
│   ├── preferenceClient.ts     # Player preference mirror and background persistence
│   ├── cachePolicy.ts          # Central extension cache limits
│   ├── cacheRepository.ts      # Background-owned validated cache records
│   └── cacheClient.ts          # Content-side cache bridge
│   ├── appearance.ts           # Typed appearance defaults, validation, presets, CSS mapping and anchor math
│   └── __tests__/              # Utility tests
│       ├── parsers.test.ts
│       ├── constants.test.ts
│       ├── state.test.ts
│       ├── translationPresentation.test.ts
│       └── ruby.test.ts
├── native/                    # Python native messaging host
│   ├── pyproject.toml          # uv/pip project config
│   ├── install.sh              # Installs venv, links binaries, registers with Firefox
│   ├── cueflora_host.json     # Native messaging manifest template
│   └── cueflora_host/         # Python package
│       ├── __init__.py          # Main loop: read/send native messages, dispatch handlers
│       ├── download.py          # yt-dlp audio download with progress streaming
│       ├── whisper.py           # Whisper API client: compress, chunk, upload, merge, parse cues
│       ├── translate.py         # LLM translation via chat completions (structured output)
│       ├── evidence.py          # Opt-in append-only local capture and provenance
│       ├── provider_check.py    # Bounded GET /models checks; no inference
│       ├── credentials.py       # User-scoped Windows DPAPI, context binding and redaction
│       ├── provider_security.py # Normalized addresses and native HTTPS/loopback policy
│       ├── test_credentials.py  # Real synthetic-key DPAPI and mocked privacy/transport tests
│       ├── quality_cli.py       # Production handler bridge, exact upload and normalization replay
│       ├── quality_benchmark.py # Controlled decoded-PCM clip preparation and ASR comparisons
│       ├── quality_translation.py # Saved-request temperature experiment (not production)
│       ├── quality_summary.py   # Objective benchmark summaries without invented accuracy scores
│       ├── fixtures/            # Observed translation fabrication evaluation case
│       ├── test_evidence.py     # Capture privacy, path/job binding and byte preservation tests
│       ├── test_quality_benchmark.py # Reference scoring boundary tests
│       ├── test_quality_translation.py # Structural versus semantic validation boundary
│       ├── test_translate.py    # Single-request translation regression tests
│       ├── test_audio_preparation.py # Required-tool, encoding and prepared-output failures
│       ├── test_whisper_regressions.py # ASR sanitizer/readability regressions
│       └── test_whisper.py      # CLI test tool for Whisper API
├── native/cueflora_setup/      # Per-user lifecycle, locking, journals and maintenance shortcut
├── packaging/                 # Offline preparation/locks, onedir host, onefile Setup, evidence and verification
├── product.json               # Independent product and preview-only policy
├── preview-identity.json      # Stable public development key; no private key or release identity
├── scripts/preview-assets.mjs  # Five-petal SVG/PNG/ICO and initial development identity
├── scripts/build-profile.mjs   # Preview/keyless candidate profiles and per-entrypoint bundle inventory
├── scripts/cache-npm.mjs       # Exact lock-integrity tarball cache, including offline validation
├── docs/store/                 # Truthful drafts/promotional assets; genuine screenshots deferred
├── scripts/quality-run.mjs     # Explicitly configured inference harness; not onboarding
├── docs/QUALITY_EVALUATION.md  # Evidence/replay usage and acceptance limitations
├── artifacts/quality/          # Private local audio/text evidence (gitignored)
├── .output/                   # WXT build output (gitignored)
└── .wxt/                      # WXT generated types (gitignored)
```

---

## Architecture & Data Flow

### Content Script Worlds

The extension uses two content scripts injected into YouTube pages:

1. **`bridge.content.ts`** — runs in the **MAIN** world (same JS context as YouTube). This is necessary to access YouTube's internal player API (`movie_player.getAudioTrack().captionTracks`). It communicates with the isolated world via CustomEvents on `document`.

2. **`youtube.content/`** — runs in the **ISOLATED** world (standard extension sandbox). Handles all UI rendering, user interaction, and extension API access (`browser.runtime`, `browser.storage`). This is where the bulk of the logic lives.

### Message Flow

```
YouTube Page (MAIN world)          Isolated Content Script          Background SW          Native Host (Python)
        │                                   │                          │                        │
        │◄── CustomEvent ──────────────────►│                          │                        │
        │  CUEFLORA_GET_TRACKS              │                          │                        │
        │  CUEFLORA_TRACKS_DATA             │                          │                        │
        │                                   │── runtime.sendMessage ──►│                        │
        │                                   │  TRANSCRIBE_NATIVE       │── connectNative() ────►│
        │                                   │  TRANSLATE_NATIVE        │   (jobId + stdio JSON) │
        │                                   │  PING                    │                        │
        │                                   │                          │◄── progress updates ───│
        │                                   │◄── tabs.sendMessage ─────│   (type: "progress")   │
        │                                   │  NATIVE_PROGRESS         │                        │
        │                                   │                          │◄── final result ───────│
        │                                   │◄── response ─────────────│   (cues array)         │
```

### Native Messaging Protocol

The native host uses Firefox's length-prefixed JSON protocol:
- **Read:** 4-byte little-endian length prefix → JSON payload
- **Write:** 4-byte little-endian length prefix → JSON payload
- Progress updates are sent as intermediate messages before the final result
- Every transcription/translation request, progress update, result, and error carries the Run's `jobId`

Message types:
- `PING` → `{status: "PONG", version, tools, capabilities}`; yt-dlp/ffmpeg/ffprobe/Deno health and allowlisted `windows-dpapi-v1` protection capability. Browser projection marks older helpers lacking Deno with `helperUpgradeRequired`; no tool paths/errors are exposed to the player
- `CREDENTIAL_PROTECT` → `{requestId, credential}` or redacted error; settings-only new-key protection/rebinding with correlated response and 10-second native limit
- `PROVIDERS_CHECK` → `{requestId, status, reason, models}`; options-only GET `/models`, 10-second browser timeout, no inference
- `TRANSCRIBE_NATIVE` → downloads audio, compresses, transcribes → `{jobId, cues, diagnostics}`
- `TRANSLATE_NATIVE` → performs one LLM HTTP request → `{jobId, translations, requestCount}`
- `CAPTURE_PRESENTATION` → append final source/translation/display mapping to an enabled, job-bound capture; no inference

The TypeScript translation layer is the sole recovery owner. The native translation layer never retries or splits; therefore the per-logical-batch limit of 8 calls also bounds physical Ollama HTTP attempts.

Saved-key requests perform a capability PING on the same native port before metadata/inference dispatch. Missing/older/disconnected/timed-out preflight fails with Upgrade/Repair and zero model attempts. Once dispatched, uncertain transport failure remains conservatively one attempt. Preflight does not poll or invoke inference. Provider redirects are not followed; store-candidate requests require non-loopback HTTPS in background and native handlers, while preview retains acknowledged remote HTTP.

The background validates native envelopes, matching job IDs, transcription cue structure, progress fields and translation request accounting before forwarding. Malformed/stale replies terminate the connection with a generic protocol error. Configured keys/endpoints and URLs are redacted from native error/progress text without altering subtitle content. A translation transport failure is conservatively counted as one possible HTTP attempt, not proven zero; it remains a hard error with no additional recovery request.

`publicNativeResponse` projects only supported public fields. Arbitrary nested diagnostic fields, raw payloads and extra cue/word properties are not forwarded. Metrics must be finite nonnegative numbers; evidence accepts known stage names/statuses and marks malformed evidence incomplete. Cue/word text and prefixes remain literal. Non-string translation entries become null for the existing adequacy/structural recovery path.

---

## Key Data Structures

### Cue Object (subtitle entry)

```js
{
    startMs: 1234,       // Start time in milliseconds
    endMs: 5678,         // End time in milliseconds
    text: "Hello world", // Display text
    words: [             // Optional: word-level timing (for karaoke highlighting)
        { text: "Hello", startMs: 1234, endMs: 2000 },
        { text: "world", startMs: 2100, endMs: 3000 }
    ]
}
```

### State Singleton (`utils/state.ts`)

All mutable runtime state lives in a single exported object:

```js
{
    activeInterval,              // Render loop interval ID
    initInterval,                // Serialized initialization timeout ID (legacy field name)
    transcriptionCues: [],       // Primary (transcription language) subtitle cues
    translationCues: [],         // Secondary (translation language) subtitle cues
    availableTracks: [],         // YouTube caption tracks from bridge
    generatedTracks: {},         // AI-generated tracks keyed by language code
    subtitleCache: {},           // In-memory subtitle cache keyed by language code
    isPanelOpen: false,          // Settings panel visibility
    workflow,                    // Status, jobId, per-stage progress, diagnostics
    showTranscription: true,     // Toggle transcription subtitle display
    showTranslation: true,       // Toggle translation subtitle display
    highlightCurrentWord: true,  // Karaoke-style word highlighting
    overlayOffsetBottom: 60,     // Overlay Y position (draggable)
    subtitleBgOpacity: 75,       // Overlay background opacity (0-100)
}
```

### Language Entry (`utils/constants.ts` → `LANGUAGES` array)

```js
{
    name: "Chinese (Simplified)",
    iso: { code: "zh", whisper: true },     // ISO 639-1 code + Whisper support flag
    bcp47: "zh-CN",                          // IETF BCP 47 tag (YouTube/Google APIs)
    iso_default: true,                       // Default variant for shared ISO code
    whisper_variant_prompt: "以下内容为普通话..." // Optional prompt to steer Whisper
}
```

---

## Storage

### `localStorage` (per-origin, YouTube)

These inherited key names describe the former layout, not an import path. CueFlora never reads page-origin settings, credentials or caches, including Substrata data. `preferenceClient.ts` initializes the background with an empty legacy object. The compatibility validators remain tested; only extension-owned CueFlora data is used. Existing page data remains untouched.

| Key (after prefix) | Type | Description |
|---|---|---|
| `transcription_lang` | string | Last selected transcription language code |
| `translation_lang` | string | Last selected translation language code |
| `translation_url` | string | Translation API base URL |
| `translation_model` | string | Translation model name |
| `translation_batch_size` | number | Output cues per contextual request (default: 30; accepted range 10–60) |
| `translation_max_parallel` | number | Translation concurrency (fixed at 1 for finalized prior context) |
| `transcription_url` | string | Transcription API base URL |
| `transcription_model` | string | Transcription model name |
| `transcription_max_parallel` | number | Concurrent chunk uploads (default: 4) |
| `transcription_mb_per_req` | number | Max MB per upload chunk (default: 25) |
| `show_transcription` | "0"/"1" | Show transcription subtitles toggle |
| `show_translation` | "0"/"1" | Show translation subtitles toggle |
| `highlight_current_word` | "0"/"1" | Word highlighting toggle |
| `ruby_zh` | "0"/"1" | Chinese pinyin display |
| `sub_bg_opacity` | number | Subtitle background opacity (0-100) |
| `overlay_bottom` | number | Overlay bottom offset in pixels |
| `appearance_v1` | JSON | Versioned appearance settings; authoritative after one-time migration from legacy appearance keys |
| `cache_keys` | JSON array | LRU list of cache keys (max 20) |
| `cache_{videoId}_{langCode}` | JSON | Cached subtitle cues per video+language |
| `cache_{videoId}_translation_meta:{lang}` | JSON | Versioned source fingerprint, languages, model, and translation pipeline identity |
| `cache_{videoId}_transcription_meta:{lang}` | JSON | Normalization version, cue fingerprint, model and endpoint; old generated ASR caches are not restored |

### `browser.storage.local` (extension-scoped)

Used through background-owned services for private provider settings, preferences, and validated subtitle cache records. Remembered keys use user-scoped Windows DPAPI; plaintext is not persisted by new saves and protection never falls back to plaintext. Run snapshots live in `browser.storage.session`, containing opaque vault references rather than plaintext/ciphertext. This does not protect against malware running as the same Windows user.

| Key (after prefix) | Description |
|---|---|
| `private_providers_v2` | Schema 2 provider/vault record, revision, opaque stage references and DPAPI blobs; background-owned |
| `private_providers_v1` | Legacy CueFlora record; retained until verified protection/persistence and successful plaintext cleanup |
| `owned_preferences_v1` | Validated preference values plus successfully persisted migration marker |
| `owned_cache_v1:<key>` | Atomic cue/metadata/checksum/access-time record; 20 records and 8 MiB policy |
| `onboarding_v1` | Persisted step 1–3 and sticky completion flag; settings-only writes; no inference |

Production player consumers use the in-memory preference client backed by background messages. Appearance Apply awaits persistence before reporting success. Other preference writes provide immediate local feedback and a persistent warning on failure. Cache/evidence/preference warnings have a separate status region so workflow progress cannot overwrite them.

Options mutations and `SETTINGS_RECONCILE` share a background queue: reconciliation waits behind outstanding writes, including ones whose client deadline expired. `ONBOARDING_FINISH` is options-only, validates the displayed provider revision and both caption/AI language selections, merges both language keys into one preference-record write, then separately writes completion. A marker failure returns `languagesSaved: true` with an explicit partial-success error; this is not a transaction across both records. Existing storage keys/records remain compatible.

Settings requests have a 15-second client deadline; native health/model checks retain their 10-second limit. A timed-out write blocks further settings mutations until an explicit reconciled read succeeds. Reload keeps visible edits but updates saved rollback points; Cancel restores persisted AI/Advanced values. No automatic write or inference retries are introduced.

Settings show saved-key indicators and empty password inputs, with Keep/Replace/Remove. Address changes require replacement or explicit reuse consent; rebind/decrypt happen only inside the helper. `PROVIDERS_GET` migrates validated v1 keys and rereads v2 before deleting plaintext. Failure preserves the original and reports accurate protection/persistence/cleanup state. Settings-only `PROVIDERS_MIGRATE` retries explicitly; `SETTINGS_RECONCILE` is read-only. Active Runs retain their original refs while later saves replace/remove keys. Provider saves, Run binding/release and tab cleanup share a background queue to protect vault retention. Settings/player responses and diagnostics/evidence never carry saved-key payloads.

The background requests `TRUSTED_CONTEXTS` local-storage access when the browser exposes `setAccessLevel`; a failed restriction blocks background operations with an explicit error. On browsers without the API, callers remain background-mediated. Run binding is serialized; snapshots record the sender URL and optional document ID, are removed on tab closure, and expired snapshots are pruned on new bindings. Native transcription also verifies that the requested video matches the bound document URL. Cache writes remove invalid owned records to recover quota without touching other storage.

---

Provider summaries carry opaque SHA-256 endpoint/model cache identities, never raw endpoints or keys. Generated caches require matching identity alongside revision, language, source and pipeline checks. Older records without identity are not restored. Cache writes use the provider snapshot captured at stage entry; the quality harness uses the same identity function.

Cache keys store cues and metadata together. Failed replacement writes preserve the prior record. Eviction and insertion are separate operations: interruption after eviction may lose that evicted entry, while remaining records stay valid and inventory is reconstructed without an index. This is not whole-cache transaction atomicity.

`requestValidation.ts` checks bounded client fields and shapes before private configuration resolution/native dispatch. Detailed preference/provider validation remains in its owning service; adequacy validation remains in translation recovery.

Presentation capture additionally requires one translation per source cue and nonempty source-index groups covering every source position exactly once. Duplicate, missing and out-of-range positions are rejected before native dispatch; normal Runs retain subtitles and surface the existing evidence warning.

## Build & Development

### Windows/Chrome preview distribution

Source version 0.1.10 is prepublication and integrates three recovered original monorepo notice sets into the normal hash-bound packaging inputs. It retains 0.1.9's strict runtime-file attribution and the later guarded helper staging/privacy work. Assigned Store identity, audio/model settings and production subtitle-processing source remain unchanged. Earlier packages remain immutable; the latest fully verified candidate supersedes them for a future submission, not an automatic upload. `docs/RELEASE_COMPLETION.md` describes construction, evidence, publisher steps and promotion; the fresh candidate's readiness/handoff is authoritative verification. `docs/PUBLIC_LAUNCH_CHECKLIST.md` records the public-first route and deferred postlaunch live testing; neither is a passed test or licence/security/Store approval. Real publisher/Store identity and prelaunch locations are supplied. Unsigned installation is the accepted first-release choice.

`node-inputs.lock.json` pins official Node 24.19.0/npm 11.17.0, archive/executable hashes and all 1921 npm input files. `node_inputs.py` restores them into preparation output, rejects linked/unsafe members and verifies npm content; global modules are not build inputs. Complete preparation can restore the portable compiler and build audio using `--audio-cache`, without private old executables or Git history. `--audio-build` copies a preserved source build before reverification, never writes into it.

`audio-policy.json`, public synthetic fixtures and `verify_audio_conformance.py` separate recipe/functional conformance from the retained 0.1.3 adoption comparison. Six formats, production compression/chunks, malformed input, missing DLL and restricted-PATH/Unicode are checked without inference. Runtime adoption binds exact report/policy/fixture/input/compiler hashes. `verify_two_builds.py` fails on unexplained payload differences and independently checks embedded Setup bytes and bootloader normalization.

Schema 2 `public-identity.template.json` constructs an exact-bound HTTPS candidate with real publisher/Store identity, optional validated public SPKI and public URLs; it cannot grant approval. Acceptance builds use the matching public Store key, while submission ZIPs remain keyless. Schema 1 installation records remain compatible. Public activation/repair/rollback are validated again before mutation. `approval_evidence.py` and `release_readiness.py` require exact artifact bindings plus actual report hashes. Only explicit manual clean-Windows/Chrome waivers are permitted; licensing, policy/security, screenshots, hosting, Store approval and publication cannot be waived or inferred from a build. Approval sidecars stay outside frozen binaries.

`build_runtime.py` copies runtime/bootloader notices and records distribution entry/version/hash origins; build-only code is not thereby shipped. Audio builds retain notice origin paths. Extension builds emit original MIT and observed package notices inside the extension. `licence_attribution.py` covers known source/data/generated containers without declaring legal approval. `audit_bundled_tools.py` probes metadata with no media URL and inspects bytecode constants without execution. The earlier nine observed Python source distributions remain historical evidence; current candidates rebuild the same downloader source on Python 3.13.15/OpenSSL 3.5.7 with 13 exact upstream wheel/sdist pins. Deno/native transitive closure remains explicit; the old downloader's Python 3.10.11/OpenSSL 1.1.1t is no longer shipped by current preparation.

The full Windows workflow obtains exact public inputs and runs complete offline preparation. Public binary sharing requires explicit review-candidate authorization and complete licence evidence; build-only provenance is not safety or Store approval. `public_materials.py` prepares buildless GitHub Pages locally only after real values are supplied; unconfigured previews receive source/templates, not invented public pages. `release_assets.py` uses predictable immutable filenames. `promote_release.py` defaults to planning, validates hash-bound decisions and unchanged local/remote bytes, and requires exact-version execution confirmation. It promotes an existing prerelease only; no Store automation, replacement uploads, tags or implicit publication occurs.

`public_materials.py --prelaunch` separately prepares source/privacy/help only: real identity required, installer reports rejected, no binary/Store download links, visible unreleased status on every page and a `.nojekyll` marker. It does not loosen installer or release approval gates. User authorization on 2026-10-15 covers source and these pages only. `docs/PUBLIC_SOURCE_AND_PAGES.md` records the dedicated `codex/public-pages` root kit. The publisher enabled public visibility and Pages; deployment success and six exact live HTTPS response hashes are recorded in local release-binding evidence. The connected GitHub interface lacks visibility/Pages settings mutations; generation alone is not proof of live deployment. Existing commit email metadata is not silently erased.

`audio-inputs.lock.json` pins official FFmpeg 9.0.2 source/signature/key, Opus 1.6.1 and dated portable MSYS2. `audio-toolchain.lock.json` pins 22 compiler/build packages plus signatures. `audio_build.py` restores the toolchain offline, compares installed compiler/shell bytes to locked archives (excluding only a generated documentation index), verifies the FFmpeg fingerprint, builds shared non-GPL/nonfree audio tools and emits sources/notices/hashes. The rejected first build lacked raw-PCM muxing; corrected builds restore it. `verify_audio_tools.py` runs production preparation/chunking on six synthetic formats and checks malformed input plus restricted-PATH/Unicode/missing-DLL behavior. Signal differences are measured without inference or semantic acceptance.

Runtime adoption also checks the matching pre-build compiler audit, current source/compiler lock digests and every accepted audio file. The dependency ledger maps all runtime, extension and embedded Setup files; unknown attribution is explicit, never automatic licence clearance. Emitted extension inventories map packages per chunk. `RELEASE_CANDIDATE_SECURITY_AUDIT.md` records native/credential/temp/downloader boundaries. Downloader output must be nonempty and confined to its request's temporary directory; public frozen transport cannot be downgraded by a message.

Setup's PyInstaller isolation accepts shared audio DLLs only from the exact verified embedded-runtime root and inventory; it still rejects unrelated or changed libraries. Clean-source logs use ordinary portable filenames, including on Windows. Runtime/installer build evidence does not automatically grant redistribution approval.

`source_identity()` centralizes the canonical source hash for source export, runtime metadata and readiness; the pretty report's file hash stays separate. `bundle_sources.py` builds and independently verifies the available third-party source/evidence ZIP, excluding historical unmatched FFmpeg experiments and refusing executable/media inputs. Partial source evidence keeps redistribution approval unset.

`bootstrap_public_cache.py` fetches exact published inputs. Official bootstrap restores 2256 upstream Python payload files plus two known locked metadata files, without a private snapshot. Source-built preparation skips the former opaque FFmpeg executables. `source_export.py` exports actual allowlisted source/untracked improvements, refuses private/media/generated/secret-pattern/path flags and independently verifies its ZIP; this is not exhaustive security clearance. `verify_source_checkout.py` runs real suites/builds from that export without Git history/private source inputs.

Schema 1 public records retain their earlier declaration validation; schema 2 separates candidate identity/binding from mutable external approval as described above. Development IDs and credential fields are rejected. `--private-chrome-id` remains a private HTTPS acceptance option. Frozen public transport cannot be downgraded by a message. Store/acceptance configuration projects only public links into settings; previews reject public-helper links.

CI actions are pinned to verified commits. Manual Chrome builds attest the exact uploaded candidate ZIP where supported; no submission/tags/installer publication occurs. The audio workflow obtains documented inputs and uploads reports only, without inventing preserved-baseline acceptance. Automated success does not establish browser registration, clean-machine acceptance, semantic accuracy or legal/store approval.

The audited source was initially uploaded privately to `TearsOfTheDawn/CueFlora`, then made public by the publisher under separate source/pages authorization; binary hosting and software launch remain unperformed pending the release gates. The publisher subsequently chose public Store release with live testing deferred until afterward. Initial commit `93b6ff1adf4821a2f67b8f26f288779f11a86122` has 302 exact archive-matching source files. Its remote extension tests/builds passed; native jobs exposed a unit test that mocked audio/download resolvers but not Deno. `test_native_protocol.py` now mocks all four resolvers, verifies calls and covers missing/raising resolvers independently of the runner's PATH. Follow-up Windows CI passed; Unix runners exposed the signature-command unit test's unmocked Windows-only MSYS2 path adapter. `test_audio_build.py` now isolates that adapter while retaining command/fingerprint assertions. Actual bundled-tool health and signature/build behavior remain separately verified by framed PING and preserved Windows build evidence; unit success is not cross-platform installer certification. Upload/CI evidence stays in local artifacts; previous packaged candidates and their source/hash bindings remain immutable.

The stable unpacked Chrome identity is `klnnagigpdlgchlablabnafceoldfalm`, explicitly development-only and derived from the retained public key. The user-supplied Store draft ID `akcolbcdfnjcahhhodnpablekjagfadf` matches its public key independently; GitHub Issues is the chosen public support channel. Their release draft/evidence stays in artifacts, not provider storage or published runtime approvals. Live prelaunch hosting is verified; fresh Store-bound candidate construction and artifact-bound release acceptance remain separate. Firefox builds are regression checks, not packaging/certification; no default Firefox identity is assigned.

`build_runtime.py` builds an onedir host with pinned tools, Python/package notices, interpreter notice inventory and hash-bound tool build/license evidence. `build_preview.py` embeds it, Chrome-only private configuration and notices into one windowed self-extracting `CueFlora Setup.exe`. Self-extraction is for Setup only; the installed runtime remains one-folder.

`build_isolation.py` removes inherited PATH/Python/library injection for PyInstaller, retaining the locked interpreter/DLL directory and Windows system directory. Every collected native dependency is checked against the interpreter hash lock; the final dependency ledger also rejects unmatched shipped DLLs/pyds. A follow-up audit found incidental Codex PATH DLLs in `security-hardening-001`, which remains preserved/superseded. Only the later corrected readiness/handoff is current acceptance evidence. This provenance fix changes no audio-tool bytes or subtitle settings.

Private policy binds product, browser ID and runtime inventory SHA-256 without granting publication/redistribution approval. Unconfigured prototypes stay blocked. Upgrade retains browser identities, repair requires matching payload, rollback restores prior release and maintenance launcher.

`runtime_tools.download_process_environment` removes inherited `DENO_PERMISSION_BROKER_PATH` only for frozen download subprocesses; production `download_audio` passes that explicit environment to yt-dlp. Deno's permission broker replaces CLI permission decisions, so an ambient browser setting must not retune the packaged solver. A synthetic absent-pipe probe reproduced the configuration-dependent failure, without secret access or an exploit. Tests cover the subprocess wiring, case-insensitive key handling, preserved tool overrides/proxy/certificate fields and unchanged unfrozen developer behavior. This is configuration isolation, not an OS sandbox, a library patch or global native-security clearance.

Setup writes only per-user `CueFlora` files and `cueflora_host` registration. Activation and owned Start Menu entry changes share OS/thread locking, ownership preflight, journal and recovery. Setup copies are versioned under `maintenance/<version>/`. Foreign/modified registrations and shortcuts are refused. Uninstall removes owned registration/shortcut and quarantines runtime versions; maintenance copies, settings and evidence remain.

Quarantine/recovery directory renames retry Windows error 5/32/33 for at most 10 seconds under the existing lock, revalidating owned paths and absent destinations each time. Persistent/unrelated errors still fail and recover registration/state. This is not a retry of installation, user settings writes or inference. Production tests cover transient success, bounded permanent failure, foreign destinations and nontransient errors.

Frozen GUI/CLI Repair supplies its matching verified Setup executable as a new maintenance copy, restoring a missing/corrupt launcher without adopting foreign shortcuts. Empty optional API keys omit Authorization entirely for metadata, transcription and translation; no empty Bearer credential is fabricated.

`smoke_setup.py --release ... --launcher ...` tests actual payload/Setup lifecycle using simulated registration/shortcuts and restricted-PATH framed PING in Unicode/spaced temporary roots. `verify_installer.py` tests headless extraction, Tcl, detection, embedded hashes and malformed-payload reports without windows/installation.

`assemble_preview.py` delivers Setup, the matching unpacked Chrome profile, keyless store-upload candidate, available notices, dependency inventory and checksums. `installation_guide.py` generates `START_HERE.md` from the actual configured identity/version: private packages use `Chrome-preview`, public-key acceptance uses `Chrome-acceptance`, and packages without an unpacked acceptance extension do not suggest loading a keyless ZIP. The guide never dumps provider/configuration payloads. The candidate is not Store-approved. `verify_archive.py` independently streams the complete final ZIP inventory/hashes.

Full preparation also runs `verify_source_checkout.py` on its final audited source export and requires the archive hash to match the candidate. That checkout has no Git/private baseline; inherited Python/Node import hooks, provider/capture configuration and developer tool overrides are removed from child commands, with user-site packages disabled. A failed command keeps the check failed and stops later steps. Tests cover guide profiles/privacy/malformed inputs, the real exporter and command/environment/failure orchestration, plus agreement of actual extension/npm/native editable-project version metadata. The guide warns against running two different CueFlora identities together; Substrata remains untouched.

`verify_local.py` retains logs for TypeScript/native/packaging/release-config tests, typecheck, both browser builds, Python compilation and staged/unstaged/new-file whitespace validation. `check_new_whitespace.py` checks untracked sources without modifying the index. `verify_isolation.py` verifies original source hashes/Git status, intact licence, copied source accounting and operational namespace separation. Source baseline is `artifacts/source-baseline.json`; private artifacts are ignored. The latest security work is in `docs/SECURITY_HARDENING_HANDOFF.md`; earlier handoffs remain historical.

Build packages use an independently created `.packaging-venv`. `packaging/inputs-windows.lock.json` and `requirements-windows-hashed.lock` are authoritative preparation inputs; the earlier three-tool lock is retained as a historical baseline, not the four-tool build contract. Frozen hosts resolve sibling tools after explicit developer overrides and fail closed if missing. Publication aliases refuse non-dry work without reading credentials; CI builds/checks only, including the private repository's push-triggered regression checks. Full preparation evidence/input caches stay local.

`npm run release:prepare -- --output <fresh-directory> --cache artifacts/input-cache-v1 --evidence-cache artifacts/redistribution-evidence-v2` runs offline input validation, disposable interpreter/wheel/npm restoration, full suites, both browser regression builds, independent preview/keyless Chrome profiles, two fresh host/Setup builds, output comparison, source/licence collection, restricted-PATH/Unicode and missing-Deno health checks, frozen synthetic-key DPAPI, simulated lifecycle, headless installer checks, isolation and final ZIP verification. Source file hashes work without commits/remotes. The report distinguishes `engineeringPassed` from permanently false `publicReleaseReady` in this milestone. `--online` fetches missing primary pinned URL inputs only; supplemental evidence stays offline and bad hashes never fall back to latest. Node/npm availability is required and effective versions/hash recorded.

Tcl core-8-6-12 notice is supplied only when the interpreter actually reports 8.6.12 and owns its Tcl library. Exact yt-dlp notices/metadata and solver hashes are separate from source notices. Runtime Python modules derive from PyInstaller Analysis; build-only distributions and emitted JavaScript are distinguished. Historical opaque-FFmpeg experiments are preserved but no longer required to rebuild or collect current audio evidence. Current 0.1.8 retains source-built 9.0.2 tools and measured conformance; source signatures, source archives and known PE/ZIP differences are evidence, not complete licence/Store clearance. Preview identity and subtitle inference/audio settings remain unchanged.

See `docs/DISTRIBUTION.md`, `docs/INSTALLATION.md` and `docs/IMPLEMENTATION_HANDOFF.md` for exact artifacts, commands, license obligations and deferred acceptance gates.

`build_downloader.py` rebuilds the unchanged yt-dlp 2026.08.19 tag using pinned Python 3.13.15 and 13 wheel/source pairs. Schema 2 `downloader-inputs.lock.json` explicitly replaces the upstream urllib3 2.7.0 pin with patched 2.8.0; the other upstream pins/hashes remain checked against the exact source archive. `downloader_security.py` validates the original baseline, same-major upgrade, primary advisory URLs and immutable original PyPI metadata under `packaging/source-metadata/`. Overrides must not claim an original upstream wheel hash. Builds retain metadata/source/recipe evidence and require the exact patched version in actual executable metadata; schema 1 original-pin records remain readable. PyPI metadata is captured once and replayed from source, not refetched as a mutable build input. It preserves the extractor list, optional request handlers and exact local EJS bytes, records the Python-version-selected websockets dependency change, and rejects unpinned native inputs. Preparation builds this downloader instead of embedding the preserved Python 3.10/OpenSSL 1.1.1 executable. `collect_curl_sources.py` verifies the exact DLL against upstream Windows curl-impersonate 2.0.0 bytes and its eight recipe source pins; notices/sources enter the dependency ledger and source bundle without granting legal clearance. `verify_installer.py` compares the full expected private/public configuration, not a hardcoded preview identity. The older source-only full compiler/audio build remains preserved proof; each new candidate must pass its own full checks.

The delivered 0.1.7 candidate predates this security override and is preserved, not silently patched. A complete 0.1.8 candidate requires its own matching runtime/Setup/store/source inventories and fresh preparation results; an isolated patched downloader is not enough. `docs/DEPENDENCY_SECURITY_REVIEW.md` distinguishes engineering evidence from final release decisions. No security or licensing approval follows from a passing advisory query or decoder test.

WXT 0.21.4 makes Vite explicit and browser launching optional. CueFlora pins Vite 8.3.4/Vitest 4.1.12 and omits unused `web-ext`/`web-ext-run` launcher trees, retaining both production builds. Developer servers no longer open browsers automatically. `@wxt-dev/browser` 0.1.39, `@wxt-dev/storage` 1.2.8 and pinyin-pro 3.28.0 retain their previous exact lock entries. The new fake-browser API uses complete synthetic tabs, explicit response callbacks and mocked storage-access capability; the real fail-closed storage restriction has a regression test. `tsconfig.json` includes owned entrypoints/utils/configuration plus generated WXT declarations, excludes artifacts and explicitly preserves the previous strict compiler contract rather than inheriting new optional WXT flags.

WXT's exact 0.21.4 npm tarball omits its licence. `npm-notices.lock.json` binds its original release-tag MIT notice to package version, npm integrity and SHA-256. `scripts/npm-notices.mjs` and `packaging/npm_notices.py` retain those bytes in emitted extension notices and the dependency ledger; mismatches fail. `prepare_windows.copy_extension_sources` includes the exact public notice lock/directory in the isolated build workspace; real-source tests verify those bytes and exclusion of artifacts/environments. This is not a generic licence substitute. Tests cover missing identities, altered bytes and unsafe paths. CI separately runs full npm advisory checks, including build/test dependencies; offline preparation does not silently contact advisory services.

`licence_attribution.augment` also verifies copied supplemental notice bytes against source pins, inventory and actual runtime files, recording notice-only ownership rather than native extension-code shipment. Unknown files do not get guessed owners. `dependency_ledger.require_file_attribution` recomputes every runtime-file row/hash relationship and checks persisted coverage/flags; full preparation fails before acceptance/assembly on incomplete or inconsistent attribution. Five regressions cover changed bytes, fabricated green flags, missing coverage and unknown notices. This does not resolve the three substantive native dependency-review groups or grant redistribution approval. A read-only replay can assess prior payloads into a fresh report directory without rewriting their inventories/packages.

`collect_v8_notices.py` restores original V8/binding notices omitted by the pinned crate's `LICENSE*` exclusion. `v8-notice-inputs.lock.json` binds two fixed upstream source archives; collector checks Deno bytes, Cargo/crate checksum, declared VCS commit and matching source/crate/runtime versions. Dirty crate VCS metadata remains recorded. Runtime/Setup carry 26 exact notice files and their hash/origin evidence; source archives enter the separate source bundle, not the installed runtime. Unit tests reject mismatched versions/commits, unsafe locks, missing offline inputs, changed notices and false approval/closure flags. Complete Rust/V8 transitive notice coverage is still a separate unresolved review, not inferred from these core notices.

`interpreter_component_notices.py` parses the pinned standalone `DOWNLOADS` dictionary using literal AST evaluation only, and retains ten original notices for eleven Windows interpreter component families (Tcl/Tk share terms). Actual locked-interpreter probes verify OpenSSL, SQLite, zlib, Expat and decimal versions. Windows Expat is matched to CPython's bundled source/COPYING, not the Unix-only standalone Expat input; Windows decimal uses the external pinned mpdecimal source. Recipe/version declarations remain distinct from actual binary-source identity. Runtime/Setup ship the notices and origin hashes; the ledger retains Microsoft redistribution eligibility and unproven native version/source linkage as separate gates. Tests reject executable manifest expressions, changed/extra notices, missing families and invented approval/closure claims.

`verify_audio_rebuild.py` compiles two independent audio builds at the same visible experimental path, preserves both outputs under exact validated local targets, and compares source/compiler/configuration equality plus every file hash. Only explicitly measured PE timestamps/checksum are normalized; residual differences fail. It does not adopt new audio bytes, invoke inference, touch previous packages or promise reproducibility before the actual experiment passes.

The controlled experiment under `artifacts/audio-rebuild-control-9.0.2-001` passed and was revalidated against the strict production recipe: no unexplained differences under identical visible paths/commands. Earlier different-root builds have different effective configure paths; do not call their remaining byte differences metadata-only or promise byte equality across paths. Existing accepted audio bytes remain unchanged.

`cargo_notice_evidence.py` replays all 1046 exact source-Cargo registry pins under `deno-cargo-policy.json`, checking archive bytes and retaining original notices. Root/declared notices are distinguished from nested test notices; neither implies actual Windows binary inclusion. `repository-notice-inputs.lock.json` separately binds fixed-commit source archives or notice-only blobs; `repository_notice_evidence.py` links them to exact crate VCS metadata. Source 0.1.10 selects 123 source rows and restores notices for 71 packages (81 files), leaving 52 unresolved lookup rows. The three added origins are libffi-sys, objc2-foundation and opentelemetry-proto; four original notice files now enter normal preparation instead of remaining an isolated investigation. Preserved 0.1.5/0.1.9 artifacts retain their original evidence unchanged. Notice-only assets require exact HTTPS commit/path, SHA-256, Git blob hash and byte count, at most 1 MiB plus one detection byte, a 30-second metadata deadline, no redirects, no cache replacement and no offline fallback. They are not full corresponding-source archives or licence clearance. Preparation/bootstrap need no private experiments or moving branches. Tests cover the actual added production pins, original/archive/blob bytes, malformed/mixed origins, stale reports, bounded downloads, changed/missing cache files, symlinks, path/commit tampering and invented approval. Exact applicability, V8 submodule coverage and binary closure remain unapproved.

`notice_names.py` centralizes Python notice filename discovery, including LICENSE/LICENCE and UNLICENSE, with Cargo's strict basename matching kept separate from aggregate/prefixed notice discovery. Original bytes, path/size checks and root/nested scope remain with the collectors. The extension bundler uses the same spelling coverage and production-plugin tests. Exact offline replay now retains 1672 Cargo notice files (13 more than 0.1.6) and reduces missing root/declared notices from 125 to 122. The separate historical repository lookup catalog remains 68/77/52; it must not be mistaken for current combined missing-notice counts or actual Windows shipment. Licence/source closure remains false.

`redistribution_assessment.py` verifies a later recorded licence-review assessment against the exact canonical dependency ledger, all candidate hashes, every known review-required issue and actual candidate-relative evidence-file hashes. Review judgments are not waivers; missing mandatory FFmpeg/source notices or unassigned files remain blockers. Evidence/reviewer declarations are not authenticated legal opinions. Preparation emits a pending template only; no assessment or approval is generated from test success. `release_readiness.py` and guarded promotion can consume a complete verified review instead of permanently hardcoding review-required ambiguity as impossible to clear. Tests cover missing/changed references, old ledgers/bytes, incomplete/duplicate findings, absent scope evidence and attempts to waive or review away mandatory missing sources.

`dependency_ledger.py` retains complete notice/source evidence once in `rows`; each file's component `ledgerRow` is a zero-based reference into that list, with its ID/version/licence summary. This avoids quadratic report growth when thousands of files share a notice set, without deleting original evidence or granting approval. Hash mismatches fail, repeated component IDs retain distinct row references, and unknown files remain unresolved. `release_assets.py` includes and hashes the pending licence-assessment template when present; older candidates without that template remain compatible.

`release_readiness.py` also reports separate `helperDownloadReady`/`helperRemaining` gates. Reviewed helper prerelease hosting requires source/engineering integrity, dependency evidence, redistribution/security-policy decisions and publication authorization, not prior Store approval or an assumed screenshot. `stage_release.py` plans by default; exact-version execution uses authenticated GitHub CLI, verifies all local inventory hashes and the public commit's complete source/blob/mode tree, uploads six mandatory assets/checksums as a draft, downloads/verifies them, atomically creates the exact source tag and activates only a prerelease. Existing tags/releases, ambiguous authorization failures and changed/missing notice/source bytes are refused. Failures can leave an unpublished draft/tag; no automatic takeover/deletion or Store submission is implemented. Anonymous public downloads remain a separate verification step. Existing `promote_release.py` still requires all final-release gates.

The 2026-10-17 privacy source includes an explicit Limited Use data-handling commitment, without claiming Store approval or provider retention guarantees. `public_materials.privacy_revision` requires one valid policy date and supplies every generated footer from it. `docs/RELEASE_EXECUTION.md` records current staging limits and concrete unresolved licence/security/policy items. The publisher declined prelaunch testing/screenshot work: no image, live test or private dashboard state is invented. These later release-engineering/docs changes do not rewrite or silently rebuild the frozen 0.1.9 candidate.

### Prerequisites

- For development: Node.js 22.12+ or a compatible newer release
- npm
- For source development: Python 3.10+; Windows packaging uses independently created Python 3.13.15 environment
- Packaging requires explicitly supplied hash-pinned tool binaries
- Normal preview users need no Python, PATH edits or manual tool installation

### Commands

```bash
# Install dependencies
npm install

# Development (hot reload)
npm run dev              # Chrome (default)
npm run dev:chrome       # Chrome

# Run tests
npm test                 # 293 unit tests via Vitest

# Run native regression tests
cd native
python -m unittest cueflora_host.test_translate cueflora_host.test_whisper_regressions cueflora_host.test_evidence cueflora_host.test_quality_benchmark cueflora_host.test_quality_translation cueflora_host.test_native_protocol cueflora_host.test_audio_preparation cueflora_host.test_controlled_evidence

# Type checking
npm run typecheck        # tsc --noEmit

# Production build
npm run build            # Chrome
npm run build:chrome     # Chrome

# Package for distribution
npm run zip              # Chrome
npm run zip:chrome       # Chrome

# Offline Windows preparation (fresh output, no live installation/publication)
npm run release:prepare -- --output artifacts/distribution/new-preparation --cache artifacts/input-cache-019 --evidence-cache artifacts/redistribution-evidence-014 --audio-cache artifacts/audio-tool-inputs-9.0.2 --downloader-cache artifacts/downloader-security-cache-018

# Windows preview: run CueFlora Setup.exe; never use Substrata install scripts
# Headless checks: self-check --report self-check.json; validate-package --report payload.json
```

### How WXT Works Here

WXT auto-discovers entrypoints from the `entrypoints/` directory:
- `background.ts` → background service worker
- `bridge.content.ts` → content script (MAIN world, based on `defineContentScript()` config)
- `youtube.content/index.ts` → content script (ISOLATED world, directory-based entrypoint with CSS)

The `wxt.config.ts` extends the manifest with permissions, host_permissions, and browser-specific settings. WXT provides global `defineBackground()`, `defineContentScript()`, and `browser` (webextension-polyfill) at build time.

---

## Key Implementation Details

### Subtitle Fetching (`api.ts`)

1. YouTube tracks are fetched via their `baseUrl` with `fmt=json3` (preferred) or `fmt=vtt` (fallback)
2. JSON3 is parsed into cues with word-level timing from segment offsets
3. Cues are cached in-memory (`state.subtitleCache`) and in background-owned extension storage (validated records, 20-record / 8 MiB internal policy)

### AI Translation (`api.ts` → `utils/translation.ts` → `native/translate.py`)

1. Source cues are split into serial contextual output batches (target 30 cues, 2400 source characters)
2. Each request receives up to 8 preceding cues/finalized translations and 4 following source cues as read-only context
3. Model input is `{"cues":[{"id":0,"text":"..."}]}` and structured output is `{"translations":[{"id":0,"text":"..."}]}`
4. The native host performs exactly one chat-completions HTTP request, rejects duplicate/missing/noninteger/out-of-range IDs, reorders valid objects by ID, and returns the existing positional string array
5. TypeScript owns malformed-output retry, split depth, positional salvage, and repair of only bad/missing runs
6. Recovery is limited to 8 physical model requests per original logical batch and split depth 2
7. Empty/truncated/label-leaking outputs are rejected; conservative extreme English under-translation gets one targeted repair, then remains usable with an unresolved-quality diagnostic if the structurally valid repair is still suspicious
8. Overlong output is treated as ambiguous and never positionally guessed
9. The strict JSON prompt includes title/description context; automatic glossary promotion remains disabled
10. Requests to the conventional local Ollama endpoint (`127.0.0.1:11434`/`localhost:11434`) explicitly set `reasoning_effort: "none"`; this prevents thinking-capable models from spending the output budget before emitting translation JSON while leaving other providers unchanged

Translation progress is based on finalized cue positions, not only completed top-level batches. Per-run diagnostics retain the last request's output-token budget, reasoning setting, finish reason, duration, and available prompt/completion/total/reasoning token usage, plus truncation, quality-flag, targeted-quality-repair, and unresolved-quality counts. Diagnostics contain indexes and reason codes, never subtitle text.

After an English translation is fully resolved, `translationPresentation.ts` normalizes whitespace and applies a fixed best-effort 20 CPS policy: extend into available silence first, then merge only adjacent English cues when the merge improves the worst CPS and the combined span stays within 7 seconds. Starts never move, cues keep a 1 ms gap, Chinese timing and word highlighting remain unchanged, and impossible fast cues are retained and reported. The adjusted English cues and timing diagnostics are committed before cache writes.

### AI Transcription (`api.ts` → `native/whisper.py`)

1. yt-dlp downloads the cheapest audio-only stream
2. ffmpeg compresses to mono Opus at 24kbps (dramatic size reduction)
3. If compressed file exceeds upload limit, it's split into overlapping chunks
4. Chunks are uploaded in parallel to the Whisper API
5. Results are merged: segments and words are time-shifted and overlap-trimmed
6. Cues are normalized: split oversized segments, deduplicate chunk-boundary artifacts, resolve timing overlaps
7. Word-level timestamps are preserved through all transformations

Preparation fails closed: required ffmpeg/ffprobe tools, encoding success and nonempty output are checked. A bounded ffprobe call verifies one Opus stream, 48 kHz, mono and finite positive duration before upload. Encoding settings are unchanged. This detects invalid preparation metadata, not semantic recognition quality or complete audio decoding integrity.

Normalization version `asr-v2-punctuation-ownership` groups standalone closing punctuation with preceding lexical tokens and opening punctuation with following tokens before cue splitting. Original word timestamps are retained. Fresh native results must report the matching version; generated cache restoration also checks version, fingerprint, model and endpoint. Translation pipeline `contextual-v5-asr-normalization` invalidates translations based on older normalization.

### Local Quality Evidence and Replay

Production handlers use `RunCapture`, a best-effort wrapper around append-only `Capture`. File failures return stage-level completeness diagnostics without subtitle text or filesystem error details, and do not repeat inference. Translation completeness accumulates across requests; presentation transport failures also preserve valid translations. The controlled `quality_cli message` path rejects missing/incomplete evidence after processing while retaining the physical request count. Direct `Capture` replay/benchmark operations remain strict.

The CLI dispatches through `handle_controlled_message`, invoking production handlers once before evidence acceptance. The headless TypeScript harness additionally calls `assertControlledEvidence` before completion; transcription, translation and a successful presentation acknowledgment are required. Ordinary browser Runs do not use this final gate. Tests exercise a production translation handler with disk capture failure and mocked HTTP: exactly one HTTP call, usable translation retained, controlled evaluation rejected.

Native framing loops until exact input lengths are read, bounds incoming messages at 8 MiB and outgoing messages at 1 MiB, and substitutes a compact correlated error for oversized results. Direct framed PING testing is not proof of browser registration.

Set `CUEFLORA_EVIDENCE_DIR` in the native host environment to explicitly enable local capture. Browser messages cannot enable capture or select a directory. UUID records under video/run IDs retain actual source/upload bytes and SHA-256 hashes, tool/settings data, raw ASR responses, normalizer source snapshots, normalized cues, translation requests/responses and presentation source-index mappings. Credentials and signed URL queries are excluded; captures still contain private audio/subtitle text and are not ordinary diagnostics. Existing records are never overwritten. Legacy raw ASR debugging is also off by default.

`scripts/quality-run.mjs` requires an explicit private provider file via `CUEFLORA_PROVIDER_CONFIG` and opt-in capture before it exercises the real TypeScript API/recovery and native handlers with stubbed UI and isolated settings; it is not browser acceptance. `quality_cli replay` sends preserved uploads without re-encoding. `quality_cli normalize` compares saved raw responses through the saved and current normalizer. Controlled benchmarks decode sources fully into native-rate/channel float PCM before seeking: raw AAC can have a `.mp4` suffix and inaccurate bitrate-based seek/duration estimates. The controlled intermediate is not the original production upload.

English presentation results include contributing `sourceIndexes` separately from display cues. Evidence records preserve these mappings; the fixed English readability policy and Chinese timing are unchanged. Accuracy/meaning/coverage scoring requires audio-reviewed references; no benchmark automatically promotes a production audio or translation setting. See `docs/QUALITY_EVALUATION.md`.

### Rendering (`render.ts`)

- A 100ms `setInterval` loop checks `video.currentTime` against cue arrays, including while paused so seeks refresh the display
- Matching cues are rendered into an absolutely-positioned overlay div
- Word highlighting applies an `.active` CSS class based on per-word timing
- Subtitle and word-prefix content is inserted with DOM/text nodes, never parsed as HTML. `createRubyNodes` uses structured pinyin tokens; the legacy string-provider API is not used by production display callers
- Unchanged content preserves DOM nodes; word timing updates only active classes, preserving text selection. Content/appearance changes rebuild the display and apply layout
- Appearance styling is applied through shared CSS variables without changing cue text or timing
- Source and translation are separate flex blocks; the gap disappears when only one is visible
- The combined block has a stable bottom-edge anchor, clamped to a 12 px top / 48 px bottom safe area
- Typography scales with player height: `clamp(height / 720, 0.75, 2)`
- A dedicated vertical drag handle appears only during appearance editing; subtitle text remains selectable

### UI Panel (`ui.ts`)

Provider editing is in `entrypoints/options/main.ts` with resumable helper → AI → languages setup. Hosted/local choices are equal and initially unselected. Each stage stays unconfigured until saved; no provider/model/endpoint fallback exists. GET model discovery is user-triggered and manual entry remains available. Save/Cancel is explicit; partial Advanced persistence is reported accurately. Stale checks are rejected after edits. Finishing languages selects only independently configured AI stages, without inference. Toolbar opens settings; first install opens setup once, updates do not. Tests use production UI/background code in jsdom, not installed-browser acceptance.

Navigation/Save/Finish/reload share one busy guard and snapshot submitted values. Dirty detection includes every provider input, label, enable checkbox and connection choice. Completed setup remains complete on revisit. Language mode selectors preserve native/AI selection and translation Off; Finish uses the settings-only background message, not two independent language saves. Failure focuses the status region; successful navigation focuses the step heading. Retry initialization does not duplicate handlers/options. Helper reachability is distinguished from all-tools-ready; model discovery errors use redacted actionable messages.

Idle player focus/panel opening refreshes provider summaries and language preferences through background messages. Navigation guards, refresh sequences, per-key write versions and pending-write protection reject stale replies/newer local edits. Active Runs and open appearance drafts are never refreshed; changed idle language selections clear obsolete display only, without fetching or inference. Appearance preferences are not overwritten by this language-only refresh.

Advanced defaults remain 4 parallel uploads / 25 MiB / 30 cues, serial translation and eight-call recovery. Run binding snapshots providers and processing controls; subsequent edits cannot retune or redirect an active Run. Caption-only use needs no AI configuration/helper. Player DOM, CSS variables/classes, bridge events and evidence environment are independently namespaced.

- Injected as an accessible monochrome five-petal flower button in YouTube's `.ytp-right-controls`
- Panel has three views: **Subtitles**, **Appearance**, and **AI settings**, with a preferred 360 px width constrained to the player
- Dropdowns populate from YouTube tracks + AI options (transcription/translation)
- Visibility toggles save immediately; AI/Advanced settings use explicit Save/Cancel; Appearance retains its isolated Apply/Cancel draft
- Keyboard events are stopped from propagating to YouTube's player
- The flower button and panel are created as an atomic pair only after both YouTube anchors exist
- Dropdown changes only save pending selections; explicit Run is the sole AI generation trigger
- Run accepts browser-trusted input only; page-generated `.click()`/dispatches cannot start AI. Unit contract checks do not pretend to create genuine browser events.

Appearance presets are Classic, Clean outline, High contrast and Language learning. Source/translation typography is independent; background, outline, layout and position are shared. Presets preserve position and existing learning-aid toggles except Language learning explicitly enables highlighting and pinyin. Reset changes the draft only. Closing, Back, Escape or navigation discards unapplied edits; Apply reports storage failures without discarding the draft.

Apply is disabled while its write is pending. An edit revision prevents completion from replacing newer preview changes or recreating a cancelled draft. Cancel does not revoke an Apply already submitted: successful persistence updates the saved rollback point while leaving the editor closed. Initial appearance migration also prevents overlapping writes.

Appearance enum fields use union types; validation rejects color strings in numeric/boolean/version fields. Provider editing is on the extension options page; the player displays provider labels and models only. Revision binding precedes clearing existing subtitles or invalidating caches. `safe-render.test.ts` exercises production rendering for literal markup, pinyin, paused seeks, and selection-preserving highlighting.

`appearance_v1` migrates legacy opacity, highlighting, pinyin and vertical offset only after two stable visible player-layout frames. Legacy keys remain intact. `ResizeObserver` handles player/block geometry and is disconnected during UI cleanup. The in-panel sample is presentation-only and never enters cue state. `scripts/appearance-preview.ts` is a local visual QA harness using the real UI/renderer with inference disabled, not a full extension integration test.

### Workflow (`render.ts` + `utils/workflow.ts`)

Provider-client request sequences reject out-of-order summary/binding responses. Pending bindings are invalidated on release and checked against navigation generation, including same-video navigation. These guards prevent old responses replacing a newer Current/Next Run summary; production callers still release background snapshots in their workflow finalizer.

Production Run IDs are `videoId:unique-suffix`; validators permit the colon separator and underscores in YouTube IDs. A background integration regression uses `beginWorkflow` itself rather than a simplified test ID. Display restoration tests exercise the real bridge/request orchestration: source and translation commit together, navigation invalidates pending results, and a newer restoration wins without triggering AI.

- `runSubtitleWorkflow()` owns the serial Run sequence: fresh transcription, then fresh translation
- `state.workflow` is the single source of truth for status, Run-button state, progress, errors, and per-run diagnostics
- YouTube navigation cancels/resets the active workflow; stale progress/results are ignored by `jobId` and video ID
- Startup/navigation may restore valid cached tracks but never generate missing AI work
- Each completed, failed, or cancelled Run emits one local structured console diagnostic record

---

## External Dependencies & System Requirements

### Runtime Dependencies (Native Host)

| Tool | Purpose | Resolution Order |
|---|---|---|
| yt-dlp | YouTube audio download | `YT_DLP_PATH` env → venv symlink → `/opt/homebrew/bin` → `/usr/local/bin` → PATH → `/usr/bin` |
| ffmpeg | Audio compression & chunking | venv symlink → Homebrew → PATH → `/usr/bin` |
| ffprobe | Audio metadata (bitrate, duration) | Same as ffmpeg |
| Deno | yt-dlp JavaScript challenge execution | `DENO_PATH` absolute developer override → sibling bundled binary when frozen; PATH only in unfrozen development. Minimum 2.3.0; preview pins 2.9.7 |

`install.sh` symlinks these into the venv's `bin/` directory so the native host can find them regardless of the browser's restricted PATH.

Frozen downloads additionally ignore unrelated yt-dlp user configuration/plugins, disable remote EJS component downloads, clear implicit JavaScript runtimes and select the explicit bundled Deno path. `worstaudio`, Opus encoding, chunking and inference remain unchanged. Four-tool health does not validate recognition/translation quality or prove current YouTube challenge success.

### API Compatibility

**Transcription (Whisper):**
- A user-selected compatible `/audio/transcriptions` service; word timing depends on response format
- No hosted preset, local endpoint or preselected model; local services must already be running

**Translation (Chat Completions):**
- A user-selected `/chat/completions` service with JSON Schema `response_format` support
- No provider/model defaults; metadata success does not prove generation compatibility

---

## Coding Conventions

- **TypeScript strict mode** — all extension source files are `.ts` with `strict: true`
- **Shared types in `utils/types.ts`** — `Cue`, `Word`, `Language`, `AppState`, message types, etc.
- **No frameworks** — vanilla TS with imperative DOM manipulation
- **`const`/`let`** — no `var` (migrated from legacy `var` style)
- **Arrow functions** preferred; named `function` kept for complex logic needing stack traces
- **Template literals** preferred over string concatenation
- **DOM element casting** — `document.getElementById(...)` results cast to `HTMLSelectElement`, `HTMLInputElement`, etc.
- **Test files use `.test.ts`** — same TypeScript as the source they test
- **Python** follows standard conventions (type hints optional, used sparingly)
- **Logging** uses `[cueflora]` prefix in extension, `[cueflora translate]` etc. in Python
- **Error handling** — errors bubble up as `RuntimeError` in Python, displayed in status panel in extension

---

## Common Modification Scenarios

### Adding a new language
1. Add entry to `LANGUAGES` array in `utils/constants.ts`
2. Include `iso.code`, `iso.whisper` flag, `bcp47` tag, and `name`
3. For regional variants, add `whisper_variant_prompt` to steer Whisper output

### Adding a new settings field
1. Add default constant in `utils/constants.ts`
2. Add state field if needed in `utils/state.ts` (update `AppState` interface in `utils/types.ts`)
3. Add DOM controls in the owning module; never interpolate untrusted HTML
4. Validate/persist through background services with explicit Save/Cancel or Apply/Cancel
5. Update tests and Run snapshots for processing/provider fields; never add hidden AI defaults

### Changing the translation system prompt
The prompt is constructed dynamically in `api.ts` `translateSubtitles()`. It includes source/target language names, video title, and description.

### Modifying native host behavior
1. Edit the relevant Python module in `native/cueflora_host/`
2. Re-run `cd native && uv sync` if dependencies changed
3. Rebuild affected frozen artifacts; the host is spawned per connection

### Testing the native host independently
```bash
cd native
# Test Whisper transcription
python -m cueflora_host.test_whisper path/to/audio.m4a --base-url YOUR_API_BASE --model YOUR_MODEL

# Optional authentication: --api-key YOUR_KEY (avoid recording credentials in shell history)
```

---

## Gotchas & Pitfalls

1. **MAIN world access is required** for YouTube's internal player API. The bridge content script must use `world: 'MAIN'` — this cannot be done from the isolated world.

2. **Native host PATH is restricted** — Firefox/Chrome launch native hosts with minimal environment. All external binaries (yt-dlp, ffmpeg) must be resolved explicitly. Frozen Windows runtimes use bundled tools after explicit developer overrides. The inherited Unix developer script is not preview certification.

3. **WXT global APIs** — `defineBackground()`, `defineContentScript()`, and `browser` are injected by WXT at build time. They are not imported — they appear as undefined in static analysis but work at runtime. Type declarations are provided by `.wxt/types/imports.d.ts` (generated by `wxt prepare`).

4. **`browser.storage.local`** is used for private provider settings and validated cache records. Legacy `localStorage` settings/caches are not trusted for generated-track restoration.

5. **Translation recovery ownership** — keep batching/recovery in `utils/translation.ts`. `native/translate.py` must remain a single-attempt transport layer or the 8-call physical request bound becomes false.

6. **Whisper chunk overlap** — 10 seconds of audio overlap between chunks prevents word loss at boundaries. The merge logic uses keep-from/keep-to windows and word-overlap deduplication.

7. **Video navigation** — YouTube is an SPA. The `yt-navigate-finish` event invalidates both the active `jobId` and shared navigation generation, removes the UI, resets state and cancels the prior navigation timer. Initialization schedules a new timeout only after its previous async attempt completes. Cache restores, native-caption fetches and UI initialization guard async boundaries, including same-video navigation. Display restoration commits source/translation together only while current, and explicit Run supersedes pending display restoration. These regressions do not constitute live-browser lifecycle acceptance.

8. **Structured output** — Translation uses JSON Schema `response_format` with explicit integer cue IDs. Native parsing must validate a complete unique in-range ID set, reorder by ID, and return positional strings; it must never guess alignment or retry. TypeScript validates content quality and owns recovery.

9. **English presentation timing** — Keep the fixed 20 CPS / 1500 ms minimum / 7000 ms maximum / 1 ms gap policy in the pure presentation module. Apply it only after successful English translation and before state/cache assignment; never retime Chinese cues or add settings for this policy.

10. **Ollama thinking defaults** — Thinking-capable Ollama models can consume the entire `max_tokens` budget in the reasoning channel and return empty/truncated JSON. Keep the local Ollama `reasoning_effort: "none"` request control and its regression test unless the UI gains an explicit reasoning setting.

11. **TypeScript + WXT tsconfig** — The root `tsconfig.json` extends `.wxt/tsconfig.json` which includes type declarations for all WXT globals, auto-imports, and `Browser` namespace types. Run `wxt prepare` to regenerate `.wxt/` types if they're missing.

12. **Type-checking vs build** — `npm run typecheck` (tsc) catches type errors that the Vite/WXT build pipeline may silently ignore. Always run both when making changes.

---

## Updating This Document

CueFlora's current release preparation is described by `docs/RELEASE_COMPLETION.md` plus the fresh preparation directory's `readiness.json` and `IMPLEMENTATION_HANDOFF.md`; earlier security/implementation/polish handoffs remain historical evidence. Substrata historical handoffs were not imported as CueFlora acceptance evidence. Original preservation is recorded by `verify_isolation.py`; private captures were not copied. Automated success is not live browser, GUI, clean-machine, semantic or public-distribution acceptance. Computer Use and browser automation remain prohibited.

After making significant changes to the project, use the `update-agents-md` skill (`.agents/skills/update-agents-md/SKILL.md`). In VS Code Copilot or any compatible agent, type `/update-agents-md`. It will scan the source files and update this document in place.
