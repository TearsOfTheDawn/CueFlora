# Final Windows/Chrome release status

Updated 2026-10-17. This is the current, bounded checklist. Older version handoffs and blocker tables are historical evidence, not additional requirements. Do not add new features or silently change the approved architecture to finish this list.

**Current direction: GitHub only.** The publisher abandoned Chrome Web Store publication. Store account actions, listing screenshots and Google approval are no longer prerequisites for the intended release. See [GitHub distribution](GITHUB_DISTRIBUTION.md). Existing executable/readiness checks remain unchanged until a tested channel-specific migration; this document does not grant approvals or bypass them.

## Implemented

- Separate CueFlora source, branding, flower controls and original MIT attribution; Substrata isolation.
- Provider-neutral onboarding, blank provider/model defaults, Save/Cancel, resumable setup and caption-only use.
- Explicit Run, preserved subtitle/audio pipeline, structured cue IDs and eight-request recovery bound.
- Protected Windows credentials, migration, HTTPS public profile, rejected provider redirects and validated message boundaries.
- Chrome Store identity `akcolbcdfnjcahhhodnpablekjagfadf`, separate development identity and exact-bound Windows installer.
- Per-user installation, maintenance launcher, locking, repair, upgrade, rollback, interrupted-operation recovery, conflict rejection and recoverable uninstall.
- Pinned offline builds, clean-source builds, notices/source inventories, archive/hash validation, regression CI and Store materials.
- Source 0.1.12 includes original ICU/V8 submodule notices, full Cargo source delivery, labelled upstream-declaration/attribution records, installer terms and frozen solver configuration isolation. Old installers are not rewritten. Only the fresh candidate's completed verification and exact-bound third-party assessment establish rebuild/review success. See [the dependency review](THIRD_PARTY_REVIEW.md).

## Fixed, no further publisher input needed

Publisher/repository, support channel, existing Chrome public keys/IDs and prelaunch privacy/help locations are already supplied. Unsigned Windows delivery is accepted. No Store account access, screenshot, Firefox identity, new repository, ChatGPT preset, paid signature, independent auditor's signature or mandatory prelaunch functional test is needed for this channel decision. The publisher explicitly defers clean-Windows/real-Chrome testing; record that as untested, not passed.

## Actual release blockers

1. **Exact-candidate third-party assessment.** Source 0.1.12 remedies the demonstrated notice/source gaps and records scoped advisory dispositions. The collector does not approve itself: use the fresh candidate's completed hash-bound assessment, not a historical pending template or a generic missing-filename count. The [review](THIRD_PARTY_REVIEW.md) explains the actual licence conditions, source delivery, configuration hardening and remaining ordinary risk limits. No mandatory lawyer signature, mathematical safety proof or bit-identical rebuild is invented as a new requirement.
2. **Actual helper hosting.** The installer must really be uploaded and anonymously downloadable with its required notices/sources before the normal-user route works. Public source and planned URLs are not installer hosting. The connected GitHub tools do not expose binary release-asset upload and no authenticated GitHub CLI is available. Conditional publisher authorization is already recorded; missing rights/security decisions cannot be replaced by that intent. The guarded staging command is implemented and refuses unsatisfied gates.
3. **GitHub package/channel migration.** Produce a keyed unpacked extension with a matching installer and manual-update instructions. Existing public activation/readiness assumes a Store release; introduce a tested GitHub-specific route rather than marking Store gates passed or handing users an incompatible keyless ZIP. Preserve exact inventories, protection, lifecycle/conflict checks and other applicable release safeguards.

The native audio download/challenge behavior remains disclosed. The completed assessment found no general published YouTube permission for the existing arbitrary-video acquisition method. Moving to GitHub does not resolve that separate permission question or itself establish that software distribution is prohibited. Do not invent permission, disguise behavior or silently change the architecture. [YouTube terms](https://www.youtube.com/t/terms), [GitHub policies](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies).

## Completion rule

No further UI, subtitle-quality, AI-service, cross-platform or optional polishing work is part of this release. Local engineering success closes its measured checklist, not third-party rights or actual download availability. Do not report the complete GitHub product as released until matching installable artifacts are hosted and the remaining applicable decisions are accurately recorded. Store approval is no longer part of that claim. This is the fixed release boundary, not an invitation to keep generating new requirements.
