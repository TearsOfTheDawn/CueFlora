# CueFlora 0.2.0 publication handoff

Published on 2026-10-19 for Windows x64 / Google Chrome through GitHub only. The publisher explicitly requested "Publish". No future release is authorised by this operation.

## User download

[Download CueFlora-0.2.0-Setup.exe](https://github.com/TearsOfTheDawn/CueFlora/releases/download/v0.2.0/CueFlora-0.2.0-Setup.exe) — the only required download. It contains the matching extension/helper, tools and notices. AI services are separate.

Setup SHA-256: `01fbdc4c9ddfa1f417c22f214a7a7dd32dc7bd64a440ac6e0d603068189dd536` (207,973,207 bytes). It is unsigned; do not disable security software. New users run Setup, then complete Chrome's initial Load unpacked step from the stable folder shown. 0.1.13 users download this first update manually, select their existing loaded extension folder, confirm adoption/Upgrade, and click Chrome Reload once. Do not remove/reinstall the extension or change its identity.

[Release notes](https://github.com/TearsOfTheDawn/CueFlora/releases/tag/v0.2.0) · [Installation guide](https://tearsofthedawn.github.io/CueFlora/download.html) · [Support](https://github.com/TearsOfTheDawn/CueFlora/issues)

## Traceable evidence

- [Clean Windows build 39332062218](https://github.com/TearsOfTheDawn/CueFlora/actions/runs/39332062218): full offline preparation, two-build comparison, source rebuild, inventories, original notices/sources and simulated lifecycle/DPAPI/packaged-runtime checks. Local final-source suites: 306 TypeScript, 127 native/setup (two privilege skips locally), 191 packaging and nine Node tests; typecheck, both browser builds, compilation and whitespace checks passed. Generic macOS native CI exposes a symlinked-temp-path test-fixture failure; Windows/Linux native checks passed. No macOS product certification is claimed.
- [Exact release source](https://github.com/TearsOfTheDawn/CueFlora/tree/8f5f078e7a65d48ca2b9ee2ba5e71c4d23e9f410): 411 files match the built source archive and Git blob modes. Source identity: `525965147094367c801b4bac4f10980d6c12f70d2ab6e0ce59350f72c49aded0`. Only `native/uv.lock` line endings distinguish release source from build commit `fb6e14e45ea657b7738abba48e69bc8c11a255a8`; the exact LF-to-CRLF transformation and identical parsed TOML were verified. The gate was not bypassed.
- [Bound publication review](https://github.com/TearsOfTheDawn/CueFlora/blob/91806a4954f2c28f931200e1f89721cc9b253e34/release/github-publication-020.json): exact source/run and all four artifact identities, scoped redistribution/security judgments, explicit policy direction, deferred manual checks. Review packet SHA-256: `610ba83edbb9700cc1d4bdba8fb73ad3b025e5d274905ff60bf8f77fa7ef6d5c`.
- [One-time publication 39336036237](https://github.com/TearsOfTheDawn/CueFlora/actions/runs/39336036237): successful exact-source staging/promotion and anonymous download/hash verification of all ten release assets, including the paired updater manifest, before modifying Pages. No existing tag/release was overwritten.
- [Pages deployment 39336310804](https://github.com/TearsOfTheDawn/CueFlora/actions/runs/39336310804): succeeded at commit `f21fe61437bf2ff5f3856d68ea42d22f07253e6a`. Six live page/style/marker files matched deployed bytes; home/download point to the verified Setup.

Local detailed evidence is retained under `artifacts/publication-020-001/`: full publication receipt, original review reports, final public verification, source-normalization proof and original-project preservation. Sensitive credential payloads and signed URLs are not part of the public evidence. Build/source inventories remain historical facts rather than being rewritten to manufacture approval.

## Preservation and boundaries

Substrata's 181 recorded original files and Git status were verified unchanged. Original MIT attribution is retained. Selected published 0.1.13 Setup/full-package/extension/source hashes are unchanged. Prior local packages/captures remain untouched. No live installation, browser automation or paid inference was performed.

Genuine ChatGPT account login/eligibility, live Chrome updating, clean-Windows/visual acceptance and semantic subtitle quality remain unverified. Automated success does not establish those results. Signing, Firefox/macOS/Linux certification and AI-service provisioning remain deferred. The audit did not establish general YouTube permission for the acquisition method; the publisher directed GitHub publication anyway. No YouTube, OpenAI or Chrome Store approval is claimed.

Post-publication source/documentation updates are prepared separately; moving the default main branch was blocked by a safety check pending explicit publisher approval. The public release, exact-source tag, assets and deployed installation page are already complete. The immutable release tag/source archive identify the actual built bytes. Future releases require a fresh candidate-bound review and explicit publication authorisation.
