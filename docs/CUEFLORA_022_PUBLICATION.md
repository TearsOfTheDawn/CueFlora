# CueFlora 0.2.2 — verified GitHub publication

Published 2026-10-22 for Windows x64 / Google Chrome. The publisher explicitly authorised this version with "Ok, publish". No future release is authorised.

## Download and update

[Download CueFlora 0.2.2 Setup.exe — the only required download](https://github.com/TearsOfTheDawn/CueFlora/releases/download/v0.2.2/CueFlora-0.2.2-Setup.exe).

New users run Setup and Load unpacked from its stable extension folder. Existing users finish Runs, confirm Upgrade, click CueFlora **Reload** at `chrome://extensions`, then reload YouTube tabs. Use manual Setup if a 0.2.0/0.2.1 updater fails or stalls. Do not remove/reinstall the extension or reset keys/models. Existing 0.1.13 installations retain their one-time recognized-folder adoption step. The installer is unsigned; never disable security software to install it.

## Changes

- Fixed the reproduced downloader startup failure with Chrome's native input kept open. Child tools use null input; confirmed Setup launches also detach output/error streams.
- Reject failed audio splits even when partial files exist, and reject invalid duration probes.
- Keep optional preparation evidence bounded/nonfatal without extra upload/inference.
- Preserve cancellable settings task ownership after status failures; avoid permanently busy post-sign-in refresh state.
- Reject a ninth saved account before replacing readable protected data.
- Verify multiple native replies before closing input; use shared complete native test discovery.

Audio preparation, ASR normalization, English timing, structured cue IDs, TypeScript-owned recovery/eight-request ceiling, identities and third-party pins remain unchanged. The earlier generic provider transcription failure remains a separate unproven cause; the repaired download failure was independently reproduced. No paid inference or live installation was performed.

## Exact evidence

- [Clean Windows build 39813901477](https://github.com/TearsOfTheDawn/CueFlora/actions/runs/39813901477): full pinned-source preparation, 319 TypeScript / 138 native / 196 packaging / 9 Node tests, typecheck, both browser regression builds, Python/whitespace checks, two-build comparison, persistent-port health, actual synthetic DPAPI/auth, headless Setup and temporary-root paired lifecycle passed. The fresh Windows runner had no native skips; the earlier local run had two symlink-privilege skips.
- [Independent inspection 39814457546](https://github.com/TearsOfTheDawn/CueFlora/actions/runs/39814457546): all 72 candidate handoff files verified; actual Setup host/downloader certificate bundles match the unchanged fixed upstream certifi bytes. Persistent-port and clean-source results were checked without executing Setup.
- Exact source tag [2089edaa8d92e416e8daa3dccc61bdf55bacf7a5](https://github.com/TearsOfTheDawn/CueFlora/tree/2089edaa8d92e416e8daa3dccc61bdf55bacf7a5) matches all 433 source archive files and modes, without a newline normalization exception. Public source ZIP SHA-256 is `17d0a7d36154923d5e088da89c5172ab421dd72a88ad1469c2fc53c62da1bc69`.
- [Bound review](https://github.com/TearsOfTheDawn/CueFlora/blob/004e0678f1919026a0ea7cef49959db53ff6527b/release/github-publication-022.json): packet SHA-256 `77beb5aefaa1d327908a3aaeeca3ee4415c2311785797de2e7650aac58da551a`; separate from built source. Licence/native-security decisions use exact fresh evidence, not inherited artifact approvals. Public OSV version queries and advisory modification metadata showed no change from 0.2.1; full npm audit was clear. Original notices, matching sources and known residual-risk assessments remain included.
- [One-time publication 39817378009](https://github.com/TearsOfTheDawn/CueFlora/actions/runs/39817378009) succeeded, anonymously downloading and SHA-256 verifying all ten assets before updating public download links. The dated changelog and single-download/Chrome Reload instructions are in the [release notes](https://github.com/TearsOfTheDawn/CueFlora/releases/tag/v0.2.2).
- All six live Pages files match deployed commit `adcd1e5716ba0e765dab5c70dc175975bd8e120b`; live update metadata matches the exact Setup/pair/source bindings. Previous 0.2.1 (ten), 0.2.0 (ten) and 0.1.13 (nine) asset hashes/sizes are unchanged.
- [Generic CI rerun 39815553615](https://github.com/TearsOfTheDawn/CueFlora/actions/runs/39815553615) passed extension and Windows/Linux/macOS Intel/Apple Silicon checks. The initial macOS failures were a new fixture using the standard symlinked temporary path. Resolving that CI environment path preserves production rejection of unsafe links. The correction is in current main/operations CI, not a covert mutation of the immutable packaged source. These jobs do not certify macOS/Linux installers.

| Published identity | SHA-256 |
|---|---|
| Source inventory | `79ce7502d210b310b78b7631fe1785e467c896c60be29a33ce2baf84c5593aa8` |
| Runtime inventory | `53cb0aa7635813a48b1e6e4f00af69cf5a6bb66972dae745ae8cec4f67b12b8d` |
| Setup | `b9ed20335437d2fb12981f4b30ec9110e23647a70693b7b502c0d8399cf29d41` |
| Chrome extension ZIP | `9bd18e198b010f27eb26ba31c8fe71ddfbdb710c8d0f22ca8e7192f7654ba553` |

The public binaries are the clean-runner build above. Earlier local candidates and prior packages are preserved separately; the source bytes match, but executable/build-path metadata and bindings must not be assumed identical. Local receipts, fresh advisory snapshots, original-preservation results and independent final verification are retained in `artifacts/publication-022-001/` and are not credential/evidence uploads.

## Acceptance boundaries

Original Substrata, installed CueFlora, settings/keys and captured evidence were not changed. Clean-machine/real-Chrome acceptance, genuine ChatGPT login, visual acceptance and semantic subtitle quality remain unverified, not passed by automation. Signing, alternate-platform/browser certification and AI provisioning remain deferred. The source audit and licence/security judgment do not guarantee absence of vulnerabilities or establish every upstream title.

General YouTube permission for the unchanged download method was not established; the publisher previously directed GitHub publication anyway. No YouTube, OpenAI or Chrome Store approval, or absence of publisher responsibility, is claimed. This one-time job cannot automatically publish future versions.
