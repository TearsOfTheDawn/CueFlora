# CueFlora 0.1.12: source updated, public launch on hold

Reviewed 2026-10-17. This versioned release record supersedes pending-review statements in older handoffs. It does not change the tested application source or authorize public binary release.

## Completed

- Windows/Chrome application, provider-neutral setup, explicit Run, appearance controls and installer lifecycle engineering.
- Candidate-bound third-party licensing and known native-security assessments; missing original notices/full dependency sources are supplied. These are scoped engineering judgments, not a universal safety certificate or legal opinion.
- All 28 preparation checks, 293 TypeScript tests, 165 packaging tests, 8 release-config tests, and 105 native tests (103 pass, two existing Windows symlink-privilege skips). Both regression browser builds passed. Real-browser/clean-machine use is deferred, not passed.
- Exact source export, unsigned Setup, keyless Store ZIP, corresponding-source bundle, checksums, installation/removal instructions and copy-ready Store/reviewer materials.

The final published source projection matches the verified 0.1.12 archive; release documents are separate metadata. Substrata, installed registrations, previous packages and private evidence are unchanged. No inference, browser automation or live installation was used for this handoff.

## Actual blocker, not more polishing

The policy assessment is finished: the current automatic YouTube audio-download route is **not cleared for general public release**. Its required authorisation is not established by the available evidence. Native script isolation is not permission to download content, and a Store approval would not automatically supply that permission. See [the assessment](POLICY_ASSESSMENT.md).

Do not publish the installer or submit the current full-feature candidate as if that issue were resolved. Either establish the relevant permission for the existing route, or approve a separately designed authorised audio-input route. No feature restriction, alternative architecture or checkbox disclaimer has silently been implemented.

## Prepared handoff

- [Minimal remaining actions](YOUR_ACTIONS.md)
- [Store listing text](STORE_LISTING.txt)
- [Privacy/permission dashboard fields](DASHBOARD_FIELDS.md)
- [Reviewer notes](REVIEWER_NOTES.md)
- [GitHub release instructions](GITHUB_RELEASE.md)
- `RELEASE_MANIFEST.json`: exact artifacts, versions, hashes and hold status.

The existing Store item is `akcolbcdfnjcahhhodnpablekjagfadf`. No new publisher identity, credentials or account is needed to prepare this kit. Only the publisher can operate the private Store dashboard; no dashboard state or genuine screenshot has been assumed. Installation testing remains optional/deferred as requested.

Public source and help pages may be inspected now. There is no hosted installer or approved Store release yet.
