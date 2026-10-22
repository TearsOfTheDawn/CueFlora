# CueFlora 0.2.3 — translation repair scheduling

The initial work was candidate preparation, not publication. The publisher subsequently authorised 0.2.3 with **publish**; [the separate publication handoff](CUEFLORA_023_PUBLICATION.md) records its actual verified release. This document retains the engineering scope. The published 0.2.2 release, live installation, Substrata and earlier packages are preserved. No browser automation or inference was used.

## Confirmed defect and narrow change

The reported `batch.repair-8 had 5 cues` error can be reproduced using the production recovery engine with a synthetic 30-cue batch. Twelve flagged positions form eight separate contiguous groups: seven single-cue groups and one five-cue group. The initial request plus seven successful repairs consumes eight calls, so the last five-cue repair is refused before dispatch. This does not prove the model failed eight times. The initial validation reasons in the user's actual Run are unknown because its responses/diagnostics were not supplied.

0.2.3 sends all rejected positions together in one repair request. Its explicit absolute-source-index map survives every retry/split and reassembles only those positions. Request-local structured IDs remain unchanged in the native contract. Gap cues and their accepted translations are context only; following context starts after the last requested source position. Evidence captures use the same sparse mapping.

The regression reproducing the reported scheduling failure now completes in two requests. Further tests cover nested sparse repairs, local-ID leakage, split/retry mappings, the hard eight-call ceiling, once-only adequacy repair and production API/capture/diagnostic alignment. Added workflow console fields contain indexes and reason codes only. They are not added to the settings session-debug export.

## Preserved behavior

No change to the eight-call limit, native retry ownership, model/provider selection, credentials, audio preparation, ASR normalization, English readability, explicit Run or successful cache identity. Persistent invalid output may still exhaust the bounded recovery path; hard label/ID safeguards are not relaxed. No phrase filters or semantic rewriting are added. Compatible successful caches are intentionally not invalidated, avoiding unnecessary regeneration.

## Verification and artifacts

Run focused Vitest regressions, then `packaging/verify_local.py --output <fresh-directory>`. Build from a frozen source export using `packaging/prepare_windows.py`, exact offline caches and the preserved hash-validated FFmpeg 9.0.2 build. Preparation verifies both extension builds, native/packaging suites, synthetic credential/auth checks, paired lifecycle recovery in temporary roots, headless Setup, restricted-PATH/Unicode native PING, source/notices and archive inventories. Actual outcomes and artifact hashes are recorded in the fresh candidate directory, not asserted by this document alone.

The final `IMPLEMENTATION_HANDOFF.md` and `COMPLETION.json` identify the exact candidate and measured results. Release review and publication require separate authority. No live installation, genuine authentication, browser interaction or semantic subtitle acceptance is claimed.
