# CueFlora 0.2.1 publication handoff

Published on 2026-10-21 for Windows x64 / Chrome through GitHub only. The publisher explicitly authorised fixing the certificate issue and publishing 0.2.1. No future release is authorised.

## Download and upgrade

[Download CueFlora-0.2.1-Setup.exe](https://github.com/TearsOfTheDawn/CueFlora/releases/download/v0.2.1/CueFlora-0.2.1-Setup.exe) — the only required download. It contains the matching extension, helper, audio tools and notices. AI services are separate. The installer is unsigned; do not disable security software.

**From 0.2.0:** its update checker is broken. Download this Setup manually, finish all Runs, confirm Upgrade, click CueFlora **Reload** at `chrome://extensions`, then reload YouTube tabs. Do not remove/reinstall the extension. Existing settings and identity are retained. 0.1.13 additionally requires explicit recognized-folder adoption. New users run Setup and complete Chrome's initial Load unpacked step from the stable folder shown.

[Release notes and dated changelog](https://github.com/TearsOfTheDawn/CueFlora/releases/tag/v0.2.1) · [Installation guide](https://tearsofthedawn.github.io/CueFlora/download.html) · [Support](https://github.com/TearsOfTheDawn/CueFlora/issues)

## Fixed and preserved

- Correct GitHub JSON metadata negotiation fixes the confirmed HTTP 415 updater defect. Binary headers, identity/pair/hash validation and explicit installation confirmation remain.
- Settings open in a full responsive tab with compact saved-key controls. Recent debugging reports contain bounded allowlisted stage/code/HTTP metadata, never keys/ciphertext, endpoints, models, video/subtitle content or raw responses.
- certifi 2026.10.19 replaces the affected trust bundle in the host, Setup and rebuilt downloader. Exact official wheel/source/metadata hashes and original MPL terms are pinned. Both actual embedded CA bundles match upstream SHA-256 `50f79f98dac192b20dbf73f35c56f0b0c557ab267ff5199d1117cc1180b70785`. TLS verification is not disabled; certificates are not manually filtered.
- Audio tool versions/settings, normalization, explicit Run, structured cue IDs, TypeScript recovery and its eight-request ceiling are unchanged. The original transcription failure is not claimed resolved: its suppressed provider response was unavailable and no paid inference was performed. The new diagnostics make a future failure actionable.

## Traceable evidence

- [Windows clean build 39684774078](https://github.com/TearsOfTheDawn/CueFlora/actions/runs/39684774078): full offline pinned preparation; 315 TypeScript, 131 native/setup, 193 packaging and nine Node tests; typecheck, both browser regression builds, compilation and whitespace checks passed. Headless Setup/payload rejection, real synthetic-key DPAPI, temporary-root simulated lifecycle, restricted-PATH/Unicode runtime PING and two-build comparison passed. No unexplained differences were accepted; executables are not byte-identical across builds.
- [Independent inspection 39687927662](https://github.com/TearsOfTheDawn/CueFlora/actions/runs/39687927662): verified all 72 candidate files and actual frozen host/downloader certificate bytes without executing Setup. Complete source comparison found only `native/uv.lock` LF-to-CRLF formatting; parsed TOML and normalized bytes match. All 424 source Git blob hashes and modes match [exact release source](https://github.com/TearsOfTheDawn/CueFlora/tree/abaf8e19411ab496cafdca33a2c6fad03ababca2). Original build commit: `1c6e0f8fb52bb20b7e89007ff1789de13f20692c`. The source gate was not waived.
- [Exact publication review](https://github.com/TearsOfTheDawn/CueFlora/blob/4bffd7c723528af30673c7ba0c4119eaf57ce7f6/release/github-publication-021.json): scoped licence/security evidence and publisher decisions, separate from built source. Packet SHA-256: `7edce0d574914e9b764f5e4beaae874af8f7e86e844a10156d5ec72a58b65458`.
- [One-time publication 39688641300](https://github.com/TearsOfTheDawn/CueFlora/actions/runs/39688641300): exact-source staging, promotion and anonymous download/hash verification of all ten assets before Pages updates. Dated security changelog and prominent manual 0.2.0 bootstrap instructions were verified. No existing release/tag was replaced.
- [Pages deployment 39688826032](https://github.com/TearsOfTheDawn/CueFlora/actions/runs/39688826032): succeeded at `b13157eb7c515c0aa7ed345cbf1b28289749fb6a`. All six live page/style/marker files matched deployed bytes. Home/download links select 0.2.1 Setup. Every 0.2.0 asset hash and the four previously recorded 0.1.13 hashes remain unchanged.

Local evidence is retained under `artifacts/publication-021-002/`: actual metadata, frozen certificate proof, fresh advisory snapshots/dispositions, solver permission probes, exact-source proof, bound review, publication receipt and independent final verification. Earlier blocked candidates stay preserved; their old certifi bytes are not relabelled fixed.

| Identity | SHA-256 |
|---|---|
| Setup (207,986,117 bytes) | `e22409884f908fa7a4909c14e4e16f70b023b718cc29aefc5d377dc823383b1e` |
| Extension ZIP | `ccc0ff5aad73fe1dcab29e69130777ca1b5ccf995f2690a75658321040f74aba` |
| Runtime inventory | `db6560d18106ddb285191f0b37006dc0a0dd7678ed872522aa859faed6535cbd` |
| Source inventory | `9202eeb27427ef28f8c95719f3249533ac752a6b4a50d8a83d10905cd146481f` |
| Source ZIP | `7cdd3e208599de852e9c4609990eb36547e0afa9a0d783bc67f0fd3e3ebc54ed` |

## Boundaries

Fresh Python/authentication dependency queries and the full npm audit had no matches after the certificate fix. Deno source-superset and low-severity interpreter findings retain explicit call-path/permission assessments and residual risk, not blanket claims that libraries are patched or unreachable. Real solver probes denied network, file, environment and process access in both configured modes; this is not an OS sandbox or proof of all interpreter behavior. Original sources/notices and file attribution are retained. The scoped engineering review is not legal advice or a zero-vulnerability guarantee.

Substrata, captured evidence, earlier local packages and installed CueFlora were not changed. Genuine ChatGPT login, live Chrome updating, visual/clean-Windows acceptance and semantic subtitle quality remain unverified. Signing, other-platform/browser certification and AI provisioning remain deferred. General YouTube permission for the acquisition method was not established; the publisher directed GitHub publication anyway. No YouTube, OpenAI or Chrome Store approval is claimed.

Default-branch documentation is updated separately from the immutable release tag/source archive. Future releases require fresh artifact-bound review and explicit publication authorisation.
