# Copy-ready Store fields and privacy worksheet

Status: prepared, not submitted. The audio-acquisition policy hold must be resolved before public release. This document does not tick or certify the publisher's dashboard.

## Single purpose

Display and customise source subtitles and translations for the current YouTube video, using available captions and optional user-configured transcription/translation services after explicit Run.

## Permission justifications

**nativeMessaging:** Connects on demand to the separately installed cueflora_host helper for temporary audio download/preparation, user-selected transcription/translation requests, explicit helper/model checks and Windows credential protection/migration. No persistent companion or background AI generation is installed.

**storage:** Saves chosen providers, encrypted remembered API keys, setup progress, language/appearance settings and bounded subtitle caches. Active Run session records hold opaque credential references. Background mediation keeps saved keys out of player and settings responses.

**https://*.youtube.com/**: Injects the subtitle overlay/controls and reads current video/caption-track metadata on YouTube. It does not request access to all sites. Native requests to selected services happen outside this browser host-permission mechanism and are disclosed separately.

## Remote code declaration: disclose native behaviour

Do not give an unqualified “No remote code anywhere” answer. If the dashboard offers the yes/no remote-code field, use Yes with the explanation below rather than concealing the helper's behaviour. This is truthful disclosure, not an assertion that Google has approved the isolation argument.

All extension JavaScript is packaged locally; no fetched script is evaluated in an extension page/content script. The separately installed native helper uses packaged yt-dlp/EJS and bundled Deno; it may evaluate downloaded YouTube player JavaScript for media challenges in a separate native process without extension API bindings. Remote solver component downloads and tool self-updates are disabled. The source, pinned dependencies and native boundary are available for review. Media-acquisition permission and Store eligibility are separately identified in the policy report.

## Data categories and use

Use the current dashboard's descriptions, not a blanket “no user data” claim. Relevant categories include website content (audio, captions and subtitle/video context), authentication information (provider API keys), and current-video browsing information/identifiers as applicable. No claim of reading Chrome's history database is made. Video ID/title can still identify the page being used. Speech/content may contain personal information; do not assume it is anonymous.

Necessary recipients are YouTube/media delivery services, the AI services deliberately selected by the user and GitHub when the user opens public help/support. No publisher inference, advertising, analytics or data-broker endpoint is present in the reviewed source. Chosen providers' retention and pricing remain independent.

Data is used for the disclosed subtitle purpose, not sold, used for advertising or used for credit/lending decisions. The publisher's Limited Use commitment is in the live privacy policy. Certify only statements consistent with that commitment and the actual form. Local storage and user-selected recipients do not eliminate disclosure obligations.

Remembered keys are protected by Windows user-scoped DPAPI, not returned as saved plaintext. It does not defend against malware under the same Windows user. Public profiles require HTTPS outside exact loopback exceptions and reject provider redirects. Opt-in local evidence capture is off by default; it can retain private audio/text and is not automatically sent to the publisher. Public support is not a private evidence channel.

## Links and distribution

- Privacy: https://tearsofthedawn.github.io/CueFlora/privacy.html
- Homepage: https://tearsofthedawn.github.io/CueFlora/
- Support: https://github.com/TearsOfTheDawn/CueFlora/issues
- Helper instructions/status: https://tearsofthedawn.github.io/CueFlora/download.html
- Existing Store item: akcolbcdfnjcahhhodnpablekjagfadf
- Intended distribution after clearance: Public, Windows x64 / Google Chrome.

Use the current English listing, supplied 128×128 icon/promotional graphics and at least one genuine CueFlora screenshot. No screenshot or private dashboard value has been assumed present. Other platforms and a successful end-user Run are not certified.

[Official privacy-fields guidance](https://developer.chrome.com/docs/webstore/cws-dashboard-privacy) describes accurate purpose/permissions/remote-code/data declarations; [listing guidance](https://developer.chrome.com/docs/webstore/cws-dashboard-listing) describes the listing and imagery.
