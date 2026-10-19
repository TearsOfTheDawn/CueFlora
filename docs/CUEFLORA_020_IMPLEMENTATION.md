# CueFlora 0.2.0 implementation and handoff

Unpublished Windows x64 / Chrome candidate. Work is confined to CueFlora; Substrata, existing installations, settings/evidence and all prior packages/releases are preserved. No live installation, browser automation, genuine login, inference or publication is part of the implementation checks.

## Implemented surfaces

- Current-tab/document/generation Run binding and stale-result rejection; full-Run/native-job installation exclusion.
- Explicit downloader progress, concurrent bounded streams, separate final-path markers, cancellation/watchdogs and owned process trees. Production audio/normalization/subtitle timing and eight-request TS recovery are retained.
- Plain-language provider fields, compact key actions, caption/AI selection, stage-specific OpenRouter discovery, 4 MiB/500-model partial lists and manual API model entry.
- Optional official ChatGPT subscription translation: loopback PKCE, signed identity/scope checks, native-only DPAPI accounts, serialized refresh, revocation, explicit eligible model selection and one streamed structured Responses request. No transcription or automatic paid fallback.
- One Setup embedding the matched extension/helper, stable extension folder, explicit exact-0.1.13 adoption, recoverable pair journaling/rollback/repair/uninstall, active-job refusal and incompatible-downgrade rejection.
- User-triggered GitHub stable-release checks, frozen manifest/asset selection, owned staging and SHA verification, confirmed Setup launch and checked extension restart. No arbitrary page URLs/paths, continuous updater or publication automation.

## Use and migration

New users run Setup, select Chrome and Install, then manually Load unpacked from the stable directory shown by Setup. Configure existing transcription/translation services or explicitly connect ChatGPT for translation only; choose languages and press Run on YouTube. No provider/model is preselected.

Existing 0.1.13 users manually download this first package, select their currently loaded CueFlora extension folder in Setup, confirm adoption and Upgrade. Exact known file hashes and identity are required; modified folders are refused without overwriting them. Click Chrome Reload once, then reload YouTube tabs. Do not remove/reinstall the extension or change its ID. Later compatible public releases support settings → Check for updates → Download → Install update → confirm Setup → Check installation → Restart CueFlora.

Settings, API-key vault records, languages, appearance and evidence are not rewritten by Setup. API provider schema-2 records remain readable. New ChatGPT provider records add an opaque account reference/backend; OAuth tokens never enter browser storage. First-use scope/identity validation and protection must succeed before credentials commit. Failed saves keep drafts; uncertain writes require reconciliation. Returning accounts reuse their issued client/host identity; disconnect clears tokens, retaining the registration mapping. Windows protection does not defend against same-user malware.

Repair requires matching payload bytes. Failed/interrupted activation restores the previous extension/helper pair from its journal and backup. Runtime/extension/maintenance recovery copies are retained. Rollback to 0.1.x is refused because older extensions cannot safely read new account records. Uninstall preserves settings/accounts/evidence and quarantines owned runtime/extension files; remove the Chrome extension separately if desired. No Chrome profiles or Substrata registrations are inspected/modified.

## Build and verification

Use pinned Windows inputs and the exact cached wheels/sources in `packaging/inputs-windows.lock.json` and `requirements-windows-hashed.lock`. `oauth_inputs.py` restores the new exact OAuth dependency inputs; `uv.lock` also records the source-development dependencies. No moving “latest” substitution is allowed.

`packaging/verify_local.py --output <fresh-directory>` runs TypeScript/native/packaging/Node tests, typecheck, both browser builds, Python compilation and whitespace validation. `prepare_windows.py` additionally builds two fresh runtimes/Setups, compares measured differences, verifies frozen synthetic JWT/DPAPI and protected credentials, temporary-root lifecycle/rollback, headless Setup extraction, restricted-PATH/Unicode PING, complete ZIP/source/notices inventories, clean-source checks and original-project preservation. `extension_payload.py` and `update_manifest.py` bind exact paired bytes. `update_payload.py` reads bounded embedded JSON inventories without executing Setup; mismatched runtime, extension, identity, source or version bindings are rejected before installation is offered. No test spends AI credits.

Fresh `readiness.json`, per-command logs, independent archive checks and generated artifact handoff establish the actual completed verification status. A failed or partial preparation directory is not a deliverable. Original 0.1.13 source/assets and prior candidates are not replaced.

New dependencies: PyJWT 2.15.1, cryptography 50.0.2, cffi 2.1.1, pycparser 3.11. Exact wheels, corresponding project sources, notices and native member hashes are retained; binary-source linkage/redistribution review is distinct from file integrity. Audio tools remain the existing pinned FFmpeg/ffprobe 9.0.2, Opus 1.6.1, yt-dlp 2026.08.19 and Deno 2.9.7.

The publication follow-up retains 34 exact authentication-native source/notice components: the upstream-declared Rust source-lock superset, wheel-declared OpenSSL and cffi's vendored x64 libffi sources with original copyright/permission blocks. These are embedded in the helper/Setup and corresponding-source bundle, not inferred from CueFlora's MIT licence. Source/binary linkage and allowed licence choices remain explicit review judgments. The release uploader now requires the update JSON and its actual embedded pair bindings and generates the correct single-Setup/bootstrap release notes. Earlier candidate packages are retained unchanged; use only the final publication receipt to identify published bytes.

## Acceptance/release boundaries

Genuine ChatGPT account login/plan eligibility, actual structured-output model compatibility, live Chrome update/reload, visual acceptance, clean-Windows behaviour and semantic subtitle quality are unverified by automated mocks/probes. Signing and other platforms remain outside this candidate. Updates/checksums do not protect against a compromised publisher account. Publication of 0.2 requires new explicit authorization and a candidate-bound review; the one-time 0.1.13 authorization does not carry forward. Nothing here promises OpenAI/YouTube/Store approval.

Official authentication/inference contracts: [sign-in](https://developers.openai.com/siwc/token-sharing-open-source/sign-in), [sessions](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions), [Responses](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference), [limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations).
