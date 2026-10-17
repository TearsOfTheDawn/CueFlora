# Windows/Chrome release execution

Updated 2026-10-17. The requested outcome is public Windows x64 / Chrome use with an existing compatible transcription/translation service. There is no publication or browser automation in the local verification workflow.

## What is actually ready

The frozen 0.1.9 candidate contains the Windows Setup, exact Store-bound helper, keyless Store ZIP, source archives, dependency notices, inventories and automated evidence. Its original source, runtime and archive hashes must not be rewritten after review. Source is public in `TearsOfTheDawn/CueFlora`; code availability is not installer availability.

Later changes improve privacy materials and add guarded helper prerelease staging. They do not change subtitle generation, provider configuration, audio tools, saved credentials, previous packages or the installed Substrata product. A new source-only export includes these release-engineering changes; it is not substituted for the frozen candidate's corresponding source.

The public privacy source now explicitly commits to Limited Use, sole subtitle-purpose use, no sale/advertising/creditworthiness use and no routine publisher access. Its generated footer derives the actual validated policy revision instead of retaining a stale hardcoded date. These data-use commitments are not a claim of Google's approval of audio downloading/challenge execution.

## Hosting before Store approval

`packaging/stage_release.py` separates reviewed helper hosting from final Store launch. Run it with the exact candidate directory, bound configuration, recorded decisions and public source commit. Planning is read-only; execution additionally needs `--execute --confirm-version 0.1.9` and a publisher-authenticated GitHub CLI. Do not put a token into a command, report or source file.

Staging retains engineering/source, actual dependency evidence, redistribution, native-security/download-policy and publication gates. Store approval, screenshots and the publisher's deferred functional tests are not prerequisites for helper hosting. The command does not create those decisions from test success or user intent.

Every inventory file is hash-checked. Six mandatory assets include Setup, Store ZIP, CueFlora source, third-party sources, consolidated notices and dependency ledger. Their public flat names are preserved. The exact public commit's complete file/blob/mode tree must match the candidate source ZIP. A conflicting tag/release or any GitHub response other than explicit absence is rejected. A draft is uploaded and its assets/checksums downloaded and verified before an atomic tag creation and public prerelease activation. No replacement upload, stable promotion, Store submission or automatic cleanup occurs. Uncertain failure requires inspecting the remote state; rerunning must not take over a partial draft/tag.

The current connected GitHub tools can manage source files and read release metadata, but expose no release-asset upload operation. GitHub CLI is not installed/authenticated here. Do not treat a source commit, generated URL, Actions artifact or local staging plan as an anonymously downloadable installer. Do not change the live download page until public assets really exist and have been independently downloaded/hash-checked.

## Remaining dependency review: precise scope

The frozen ledger names three review-required groups: rebuilt yt-dlp/native dependencies; Deno/Rust/V8; CPython/native dependencies. These are not three proven licence violations. A source-lock superset, unavailable bit-identical rebuild or lack of a lawyer's signature is not by itself a distribution ban. Permissive components do not automatically require corresponding source; GPL/LGPL components have their actual source/notice obligations. The existing source bundles, notices and recipes must be evaluated against actual terms, not replaced with a green flag.

For Deno, 51 source-superset root/declared-notice gaps remain outside the two repository/supplement catalogues. That is not 51 shipped violations: other-platform/build/test dependencies and overlapping V8 notices exist. The unresolved question is applicable notice coverage for the actual distributed binary. The exact official source asset and root MIT licence alone do not settle it. Supplemental original notices have not been retroactively inserted into Setup.

The actual Windows Python licence already contains Microsoft additional conditions, including downstream restrictions. Do not claim all Microsoft terms are missing or invent a mandatory Visual Studio purchase. The licence also requires downstream protective terms; whether the supplied notice/distribution route satisfies that requirement remains a concrete review item, not an automatic approval from Python's open-source status.

The dated Rust scan identified source/version matches, not confirmed application exploits. Maintenance warnings, permission-constrained networking and three inspected API preconditions have different dispositions. Untested advisory applicability is not patched status; conversely a scanner count is not proof of compromise. No confirmed production updater leak was reproduced. Do not replace tools or claim native-security clearance on those observations alone.

## What cannot be represented as completed

- Actual redistribution decisions cannot be manufactured from build success or broad publication intent. Resolve exact notice/terms gaps and rebuild only if required bytes change.
- Native downloading and YouTube challenge execution must be disclosed accurately. Their Store eligibility is not settled by the presence of a helper, a privacy statement or sandbox tests. Seek a separately approved remedy if Google requires an architecture change; do not conceal the behavior.
- No genuine current CueFlora screenshot or private dashboard state was inspected. The publisher declined a screenshot/testing request. An assumption may guide preparation, but cannot become a passed evidence record. Existing genuine draft images can be used if present; Google may still require listing changes.
- Uploading the new ZIP is not publication: listing/privacy/reviewer fields and Google review still apply. There is no Store-account automation or approval here.
- Clean-Windows/new-user Chrome tests remain deferred, not passed. No claim that every arbitrary AI provider works is made. Transcription and translation need the documented compatible APIs/model capabilities.

These are the actual boundary of the current implementation, not a request for routine manual testing. No binary or Store item may be described as public until its real availability is verified.
