# Final Windows/Chrome release status

Updated 2026-10-17. This is the current, bounded checklist. Older version handoffs and blocker tables are historical evidence, not additional requirements. Do not add new features or silently change the approved architecture to finish this list.

## Implemented

- Separate CueFlora source, branding, flower controls and original MIT attribution; Substrata isolation.
- Provider-neutral onboarding, blank provider/model defaults, Save/Cancel, resumable setup and caption-only use.
- Explicit Run, preserved subtitle/audio pipeline, structured cue IDs and eight-request recovery bound.
- Protected Windows credentials, migration, HTTPS public profile, rejected provider redirects and validated message boundaries.
- Chrome Store identity `akcolbcdfnjcahhhodnpablekjagfadf`, separate development identity and exact-bound Windows installer.
- Per-user installation, maintenance launcher, locking, repair, upgrade, rollback, interrupted-operation recovery, conflict rejection and recoverable uninstall.
- Pinned offline builds, clean-source builds, notices/source inventories, archive/hash validation, regression CI and Store materials.
- Source 0.1.11 includes the original ICU notice, exact data lineage and regression-tested collector. It retains the 0.1.10 Deno environment-isolation fix. Old installers are not rewritten. Only the fresh candidate's completed reports establish rebuild success.

## Fixed, no further publisher input needed

Publisher/repository, support channel, Store ID/public key and prelaunch privacy/help locations are already supplied. Unsigned Windows delivery is accepted. No Firefox identity, new GitHub repository, ChatGPT preset, paid signature, independent auditor's signature or prelaunch functional test is invented as a new prerequisite. The publisher explicitly defers clean-Windows/real-Chrome testing; record that as untested, not passed. Do not request a screenshot again: use an existing genuine draft image if actually present; dashboard state remains unverified.

## Actual release blockers

1. **Third-party obligations and remaining native findings.** The ledger identifies three unresolved assessment groups: Deno/Rust/V8, rebuilt yt-dlp/native dependencies and CPython/native terms. Exact ICU evidence now ships, but unavailable original source-commit notices and remaining advisory applicability must not be rubber-stamped. Source-lock scanner matches are not automatically shipped vulnerabilities, and permissive code does not universally require full corresponding source or a bit-identical rebuild. This is an evidence/rights question, not a request for another UI feature or a mandatory lawyer signature.
2. **Actual helper hosting.** The installer must really be uploaded and anonymously downloadable with its required notices/sources before the normal-user route works. Public source and planned URLs are not installer hosting. The connected GitHub tools do not expose binary release-asset upload and no authenticated GitHub CLI is available. Conditional publisher authorization is already recorded; missing rights/security decisions cannot be replaced by that intent. The guarded staging command is implemented and refuses unsatisfied gates.
3. **Chrome Store account and review.** A code change cannot complete the private developer dashboard or grant Google's approval. Upload the final higher-version ZIP to the existing item, provide accurate listing/privacy/reviewer information, choose Public and complete review/publication. Genuine listing imagery is Google's requirement if the draft lacks it, not a fabricated test result. No private Store access or approval is assumed.

The native audio download/challenge behavior is disclosed. Current [Store policies](https://developer.chrome.com/docs/webstore/program-policies/policies) and [MV3 requirements](https://developer.chrome.com/docs/webstore/program-policies/mv3-requirements) do not allow us to declare this architecture approved merely because the helper is separate. Google can require changes; if so, obtain a separately approved remedy. No architecture change is silently made in this sweep.

## Completion rule

No further UI, subtitle-quality, AI-service, cross-platform or optional polishing work is part of this release. Local engineering success closes its measured checklist, not third-party rights, actual download availability or a Store decision. Do not report the full public product as completed until those three blockers have real outcomes. This is the fixed release boundary, not an invitation to keep generating more plans or versions.
