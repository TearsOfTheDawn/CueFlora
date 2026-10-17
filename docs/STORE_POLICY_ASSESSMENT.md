# Store policy assessment — unresolved questions

Current boundary, 2026-10-17: the [final checklist](FINAL_RELEASE_STATUS.md) supersedes the old general list at the end. Actual publisher/Store identity and privacy/help hosting are supplied; prelaunch functional testing is deferred; paid signing and an independent auditor's signature are not mandatory new project requirements. This scoped engineering review does not establish Google's decision or resolve actual third-party rights. The download/challenge questions below remain genuine and must not be hidden or marked passed solely to finish a checklist.

Reconsidered 2026-10-13 for 0.1.3. This is engineering evidence, not legal advice or Chrome Store compliance/approval. No external reviewer was contacted and no architecture was redesigned. See `RELEASE_CANDIDATE_SECURITY_AUDIT.md` for the scoped security changes.

Implemented in 0.1.2: user-scoped Windows key protection; no remembered-key plaintext fallback; settings-only credential operations; store-candidate remote HTTPS enforcement at both boundaries; exact loopback exceptions and no provider redirects. Independent review and genuine browser acceptance remain unperformed. [Current Chrome policies](https://developer.chrome.com/docs/webstore/program-policies/policies)

## Audio downloading

Explicit Run uses native yt-dlp to download temporary `worstaudio` from YouTube for transcription. There is no media export UI, browser-cookie import or continuous harvesting. Nevertheless, internal temporary processing is still a download. User initiation alone does not establish authorization, copyright rights or eligibility under YouTube/store terms.

Before submission, a responsible publisher must establish an authorized use scope and accurate declarations. Potential remedies include enforceable restrictions to authorized content or a separately reviewed supported ingestion route. A checkbox disclaimer alone is not a demonstrated remedy. No restriction/architecture change is implemented or presumed approved here.

## Native challenge execution

Frozen yt-dlp uses bundled Deno and verified local EJS, ignores unrelated config/plugins and disables remote component downloads/self-updates. YouTube player JavaScript remains remote challenge input executed by native tooling. Packaged extension JavaScript and local solver files do not establish that the entire native behavior is acceptable under the store's remotely hosted code/security expectations. [MV3 policy requirements](https://developer.chrome.com/docs/webstore/program-policies/mv3-requirements)

Review actual execution/permissions, downloader updates, user explanation and publisher obligations. Possible remedies include a reviewed bounded challenge mechanism, stronger native isolation or an alternative authorized ingestion path. None is silently added; disabling challenge handling may break downloads and must be assessed as an explicit product change.

## Privacy and transport

Disclose audio chunks to the selected ASR service; subtitle text/languages/context/title/description to translation; current-video/caption metadata; explicit credential-bearing GET model checks; local cache/provider settings; Windows-protected keys and opt-in evidence files. Provider fees/retention remain outside CueFlora control. Preview remote HTTP acknowledgement is compatibility behavior, not public-profile clearance. The keyless candidate alone cannot be installed with the preview helper's registration.

Remaining gates: exact dependency licence/source closure, policy assessment of downloads/challenge execution, independent security review, publisher/store identity and matching installer, public privacy/download/support locations, genuine screenshots and scanner/clean-system/live-browser acceptance. The first release is explicitly unsigned; paid signing is not a prerequisite. Publication and redistribution authorization remain false.
