# Final Windows/Chrome release status

Updated 2026-10-19. Published Windows/Chrome version **0.2.0**. This is a fixed completion boundary, not an expanding feature list.

## Implemented

The independent CueFlora project retains provider-neutral onboarding, protected credentials, explicit Run, appearance controls and the existing subtitle/audio pipeline. Windows Setup retains per-user installation, repair, upgrade, rollback, interruption recovery, conflict rejection and recoverable uninstall.

The GitHub-only channel now builds a keyed unpacked Chrome extension and matching helper, full Windows ZIP, original notices and sources. Public/development identities remain separate. Store approval, screenshots and Store-account actions are not part of this route. Exact identity/hash/source integrity, licensing and native-security checks remain required.

0.2.0 adds clearer setup, optional ChatGPT-plan translation, navigation/download reliability fixes and paired Setup/in-app updates. Its one-time publication was separately authorised by the publisher's "Publish" instruction; future versions are not automatically published. Fresh preparation reports record tests, two-build comparison, headless Setup, synthetic audio, restricted-PATH/Unicode PING, protected-credential and simulated lifecycle checks. A separate artifact-bound review is required before uploading; the build cannot approve itself.

## Publication completion

Completion requires a successful fresh candidate, scoped licence/native-security assessment, explicit publisher decisions, exact-source release tag, anonymously verified public binary/notices/source/checksum downloads and deployed matching download pages. The generated readiness report and publication receipt are authoritative for execution state. Source documentation describes the supported release path, not proof that future asset URLs already exist.

The 0.2.0 publication job [39336036237](https://github.com/TearsOfTheDawn/CueFlora/actions/runs/39336036237) succeeded. Its receipt records all ten assets anonymously downloaded and SHA-256 verified, including update metadata. The source tag is `8f5f078e7a65d48ca2b9ee2ba5e71c4d23e9f410`; it exactly matches the 411-file built source archive. Relative to the build commit, only `native/uv.lock` line endings differ (LF to CRLF, identical parsed TOML); no source-identity check was waived. The [release page](https://github.com/TearsOfTheDawn/CueFlora/releases/tag/v0.2.0) provides a single recommended Setup download. 0.1.13 remains unchanged.

Pages deployment [39336310804](https://github.com/TearsOfTheDawn/CueFlora/actions/runs/39336310804) succeeded; all six live page/style/marker files were independently fetched and matched deployment commit `f21fe61437bf2ff5f3856d68ea42d22f07253e6a` byte-for-byte. Home/download links select the actual 0.2.0 Setup. See [publication handoff](CUEFLORA_020_PUBLICATION.md) for exact evidence and remaining acceptance boundaries.

No new user information, Store screenshot, functional test, paid signing, lawyer signature or alternate-platform certification is required to execute this bounded GitHub milestone.

## Deferred, not passed

Clean-Windows and real Chrome/native Run acceptance were expressly deferred by the publisher. Genuine ChatGPT login and live Chrome updating remain unverified. Installer signing, Firefox/macOS/Linux certification and AI provisioning remain outside this release. Generic macOS CI has a symlinked-temporary-path test-fixture failure; Windows/Linux native checks and Windows release preparation passed. This is not macOS certification or an all-platform CI pass.

The audit did not establish general YouTube permission for the download method. The publisher explicitly said "Yes, publish anyway"; the GitHub policy record preserves that as reviewed, not permission granted. Licensing/native-security checks remain mandatory. Historical reports are retained; previous packages and Substrata remain unchanged.
