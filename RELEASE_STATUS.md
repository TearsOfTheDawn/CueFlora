# CueFlora release status

Updated 2026-10-17: the publisher abandoned Chrome Web Store distribution in favour of GitHub only. No Store submission, screenshot, developer account action or Google approval is part of the intended route.

See [the current GitHub route](docs/GITHUB_DISTRIBUTION.md) and [finite release status](docs/FINAL_RELEASE_STATUS.md). This commit changes documentation and build-only CI; it does not rebuild or publish an installer, migrate Store-specific activation/readiness checks, or establish YouTube permission. Existing 0.1.12 packages and their exact-bound assessments remain immutable historical evidence under `release/0.1.12/`.

The intended installation is a matching keyed unpacked Chrome extension plus Windows helper from GitHub Releases. Ordinary Windows/Chrome users must manually enable Developer mode and load that folder. Keep the extension folder and update manually. Do not substitute a keyless Store ZIP or assume binary hosting exists before actual assets are uploaded.

Application/subtitle processing and Substrata remain unchanged. This documentation/workflow transition passed 293 TypeScript tests, 105 native tests (two environment skips), 165 packaging tests, 8 Node tests, both browser builds, typecheck, Python compilation and whitespace validation. This is not live-browser, legal or clean-machine acceptance. No binary release was created.
