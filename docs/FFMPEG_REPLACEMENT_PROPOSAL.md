# FFmpeg provenance finding and replacement proposal

No audio tools were replaced or upgraded in this milestone. This is a concrete future work proposal, not permission or public redistribution clearance.

## What was measured

Current FFmpeg/ffprobe report `N-125875-g5d4d3bdc61-20260731`, GPLv3-or-later and many statically enabled external libraries. The dated [BtbN release](https://github.com/BtbN/FFmpeg-Builds/releases/tag/autobuild-2026-07-31-14-10) has a matching version/revision and exact asset/checksum evidence, but **does not match the current executable hashes**:

| Executable | Preserved SHA-256 | Dated candidate SHA-256 |
|---|---|---|
| ffmpeg.exe | `851aa8ea5366b5af33c0681cc292d662829c7088e9ac96f6e9b37030e6835ba4` | `dcec5129f94a0e7338303a9bdb6548889d28238f57e1a2315884946c47fa1c40` |
| ffprobe.exe | `01dd9a776db5df93d0e3a9b8714a7a7500402e8e628cdc68608ed781454f8b71` | `ad3dd773bd94cd86906eb451d83112181bc884df7a5d57d15797bfad1f093da8` |

Both candidate files have the same sizes as their preserved counterparts (145,240,576 / 145,030,656 bytes). Each differs in 24 byte positions: PE file/export timestamps, checksum and four embedded external-library build-time strings. This is strong evidence of closely related builds, **not an exact-origin proof**. Header normalization alone does not explain every difference. Candidate binaries were inspected, not substituted or executed.

The matching release tag resolves to recipe commit `a99e8230eae00d1cee38f23076a7a1f55cd984e2`. Its archive and release checksums are hash-locked in `packaging/evidence-windows.lock.json`. Matching core FFmpeg source and candidate recipes are obtainable; the enabled libraries' exact source/build closure for the preserved bytes remains unestablished. [FFmpeg distribution guidance](https://ffmpeg.org/legal.html)

## Proposed separately approved replacement

1. Preserve the current tool bytes/evidence. Build a minimal Windows x64 audio-focused FFmpeg/ffprobe from full pinned core revision `5d4d3bdc61` (resolve/store its complete commit and source digest before building).
2. Pin compiler, MSYS/container/build recipe and every input hash. The candidate recipe's Opus dependency is commit `3da9f7a6db1c05c3996cb363a9d1931a978bf1be` from `https://github.com/xiph/opus.git`; obtain/verify that source and notices before reuse. Do not infer a release version from the commit.
3. Retain necessary audio demuxers/decoders, Ogg/Opus muxing, resampling and ffprobe. Omit optional video/GPL/nonfree libraries where unnecessary. Static or dynamic linking choices require an actual licence/relocation review, not an automatic LGPL claim.
4. Publish the exact recipes, sources and dependency notices required for the selected build. Audit combined obligations, including any required relinking arrangements, before distribution.
5. Compare the existing production commands on synthetic and preserved nonprivate matched audio: accepted input formats, Opus codec, 48 kHz mono, 24 kbps, duration, chunk boundaries, probe output, processing time and failures. Keep inference/normalization settings unchanged; perform separate controlled recognition acceptance before adoption.
6. Validate restricted-PATH/Unicode operation and lifecycle/inventories. Only then authorize a new versioned tool lock and runtime release. Rollback must retain the previous tool bytes.

Using the dated verified full BtbN archive would make its download origin explicit but still leaves a large corresponding-source closure. A minimal pinned build offers a smaller review surface; it must not be adopted without the above evidence and tests.
