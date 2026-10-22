# CueFlora 0.2.2 — wider audit and repair scope

Date: 2026-10-22. Windows x64 / Chrome candidate, not published or installed.

## Confirmed findings and implemented repairs

| Finding | Evidence and repair |
|---|---|
| Downloader startup stalls on Chrome's open native connection | Installed 0.2.1 reproduced the exact health failure in 8.19 seconds with input left open. The unchanged source reproduced it in 8.43 seconds; isolating child stdin passed in 1.25 seconds. `tool_process_options` now disconnects production tool health/version, download and audio-preparation processes from native control input. The native connection remains open. The exact blocked OS/interpreter call was not stack-traced. |
| Updater Setup inherited native protocol streams | The verified-launch path also inherited stdin/stdout/stderr. It now explicitly detaches all three; no arbitrary executable/URL, shell launch, silent install or security-warning bypass was introduced. |
| A failed split could upload a partial audio file | `_split_into_chunks` checked file existence/size but ignored FFmpeg's exit status. A synthetic failing process leaving nonempty output reproduced acceptance. Nonzero exits now fail closed. Nonfinite/nonpositive duration probes are also rejected. Codec, bitrate, sample rate, chunk boundaries and upload retries are unchanged. |
| Optional evidence could block/fail a normal Run | The FFmpeg-version subprocess had no deadline and payload evaluation happened outside the best-effort capture guard. It now has a ten-second bound and lazy guarded capture; failure marks evidence incomplete without blocking or repeating upload/inference. Controlled evaluations remain strict. |
| Failed status polling could orphan settings tasks | Update and account polling discarded the task ID while native work could still be active. References remain cancellable, conflicting starts stay disabled, stale polling errors are ignored, and failed account metadata operations cancel before releasing ownership. A failed account-list refresh after completed sign-in now releases busy state accurately. |
| A ninth saved account could make the store unreadable | Reads reject more than eight accounts, but writes previously accepted nine. Writes now enforce the same limit before replacing the encrypted record. A regression verifies byte-for-byte preservation and readability of the existing store. |
| Closed-input tests missed the real transport condition | Packaged health/capability/lifecycle gates now send two framed PINGs and receive both before closing stdin. The bounded probe checks truncated/oversized/missing responses, restricted PATH and Unicode paths. Local, clean-source and CI native suites now share discovery so clean-source verification does not omit tests. |

These are narrow reliability/data-preservation fixes, not provider presets, new model behavior or a subtitle-pipeline redesign. New code is standard-library-only; third-party dependency/tool pins and the 0.2.1 certificate correction remain unchanged.

## Wider review boundaries

Reviewed native framing/dispatch and cancellation, child ownership and watchdogs, downloader output/path validation, preparation/chunking/capture, update manifest/download/payload/launch checks, protected account writes and settings task polling. Also inspected provider metadata requests, credential boundaries, subscription streaming, settings deadlines and install lifecycle interfaces. Existing renderer/cache/navigation/translation regressions remain mandatory.

This is not a claim that every project bug or security issue has been eliminated. Existing dependency/licence/policy assessments remain separately recorded; a fresh candidate does not inherit publication approval. Arbitrary hostile same-user processes remain outside DPAPI's protection boundary. No runtime phrase filter, semantic subtitle rewrite or extra AI retry was added.

The original suppressed provider transcription error remains a separate unproven cause; this patch resolves the subsequently reproduced downloader failure. Metadata reachability is not generation compatibility.

## Verification and preservation

Production-code native/TypeScript regressions cover the findings above. Full candidate preparation must additionally verify the frozen persistent port, source identity, complete inventories/archives, two fresh builds, synthetic DPAPI/auth, temporary-root paired lifecycle and headless Setup. Exact reports, not this source document, establish which checks passed.

Substrata, installed CueFlora, settings/keys/evidence, published 0.2.1/0.2.0/0.1.13 and earlier local packages are preserved. No browser automation, live installation, paid inference or publication is part of this task. Genuine browser/GUI/ChatGPT/clean-machine/semantic acceptance remains unverified.
