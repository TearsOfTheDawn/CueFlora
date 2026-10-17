# GitHub-only distribution

Decision: 2026-10-17. Target: Windows x64 / Google Chrome. The publisher abandoned Chrome Web Store distribution. This supersedes earlier instructions to submit, supply Store screenshots, obtain Google approval or publish a Store item. No Store account or draft was modified.

## User route

After the matching package is actually released:

1. Download the extension/helper package from [GitHub Releases](https://github.com/TearsOfTheDawn/CueFlora/releases), and extract it to a folder you will keep.
2. Open `chrome://extensions`, enable **Developer mode**, choose **Load unpacked**, and select the included extension folder containing `manifest.json`.
3. Run the matching **CueFlora Setup.exe**, explicitly select Chrome and confirm installation.
4. In CueFlora settings check the helper, connect existing compatible AI services, select languages, and press **Run** on a YouTube video. Suitable native captions can be used without AI configuration.

This is Chrome's manual development-loading route, not normal consumer installation. Setup must not silently install the extension, fake enterprise management, disable browser/security protections or install AI services. [Chrome distribution rules](https://developer.chrome.com/docs/extensions/how-to/distribute), [manual loading instructions](https://developer.chrome.com/docs/extensions/get-started/tutorial/hello-world#load-unpacked).

## Identity and updates

The extension's manifest public key must derive the exact ID allowed by its helper. Do not distribute a keyless Store ZIP as the unpacked extension. The existing candidate's release key/ID can remain stable even though its original Store draft is abandoned; a Store listing is not required to load that keyed folder. The existing development identity remains separate. No new identity or credential is needed merely to choose GitHub distribution.

Keep the extracted folder. A documented update must preserve its public key and replace/reload extension files; it must not remove the extension and imply that settings automatically transfer between IDs. Install a matching helper update through Setup when required. Retain existing repair, rollback, conflict rejection and recoverable uninstall. Do not touch Substrata.

## Finite engineering follow-up

This document changes the release route, not frozen executables. Existing packages and exact-bound assessments remain immutable. The existing pipeline still contains Store-specific public-activation/readiness decisions; those are not silently removed here.

1. Add and test a GitHub-specific package/readiness path that requires a keyed unpacked extension and matching installer identity. Remove only Store-channel prerequisites for that path, retaining source/hash integrity, credential protection, HTTPS, licence/security checks, and explicit publication authority. Preserve legacy installation-record compatibility; do not globally turn failed gates into passed ones.
2. Build and verify the matching extension/helper release, checksums, original notices, corresponding sources, and exact update/removal instructions. CI currently builds a development-key extension/source artifact only; that is not the complete installed product or redistribution approval.
3. Stage exact reviewed files on GitHub Releases, verify anonymous downloads, then update Pages with real asset links. Never describe a planned URL as an available installer. No binary upload was performed by this documentation transition.

No screenshot, Store developer account, Store approval or publication work belongs to this route. No new features, subtitle-processing changes, mandatory live testing or alternate-platform certification are introduced.

## Permission is separate

YouTube's published terms restrict downloading and automated access except under their stated permissions or applicable law. No general transcription exemption or permission for CueFlora's arbitrary-video yt-dlp route has been established. That completed assessment is not a finding that every use is illegal, nor proof that distributing the software itself is categorically prohibited. It must not be relabelled cleared merely because distribution moves to GitHub. [YouTube terms](https://www.youtube.com/t/terms).

GitHub hosting remains subject to its own legal/copyright policies and third-party redistribution obligations. Do not promise that another hosting channel eliminates account, takedown or legal risk. [GitHub policies](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies).
