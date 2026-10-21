# CueFlora privacy policy

Publisher/contact details appear in the page footer. Policy revision: 2026-10-20. This policy describes the Windows x64 / Chrome edition; publishing this policy is not a public software release.

CueFlora reads current-video/caption metadata, video ID, title and bounded description for subtitles. On explicit Run, the on-demand helper downloads temporary audio and sends prepared chunks/language/model parameters to your chosen transcription service. Source cues, languages, neighbouring context, title and bounded description go to your chosen translation service. User-triggered model checks send metadata requests and optional credentials; they do not perform inference.

Provider configuration, language/appearance preferences, setup progress and bounded subtitle caches are stored locally. Successfully remembered keys use Windows user-scoped encryption; saved plaintext is never returned to settings/player responses. Unsuccessful legacy migration leaves the original until protection and persistence are verified, with a visible warning. Protection does not defend against malware running as the same Windows user.

Data goes to YouTube and services you deliberately configure, not a CueFlora inference server. Their privacy, retention and API fees apply independently. Public builds require remote HTTPS and reject provider redirects. There is no added advertising, analytics, cookie import, persistent companion or automatic AI generation during navigation.

In the 0.2 candidate, optionally connecting ChatGPT opens OpenAI authentication in your system browser and a temporary local loopback callback. Access, refresh and ID tokens remain only in CueFlora's user-scoped Windows-protected native account store; the extension receives opaque account references and safe status, not tokens. Eligible translation text/context goes to OpenAI Responses using your chosen account/model with request storage disabled. Provider retention policies still apply. This route does not transcribe audio and never automatically falls back to a paid API. Disconnect attempts remote revocation, clears local tokens and reports if remote revocation was not confirmed. Account/client mappings remain for later reconnection.

User-triggered update checks contact GitHub for stable CueFlora release metadata. A chosen Setup is downloaded from allowlisted GitHub asset hosts into an owned local staging directory and hash-verified. AI credentials are never attached. Installation and extension restart require explicit confirmation. There is no scheduled updater or automatic publication. Installation preserves settings/evidence; recoverable old runtime/extension versions and staged update files may remain on disk.

## Limited Use commitment

CueFlora's handling of user data follows the Chrome Web Store User Data Policy, including its Limited Use requirements. Data is used only for the disclosed subtitle features and transferred only as needed to provide those features. CueFlora does not sell user data, use or transfer it for advertising, or use it to determine creditworthiness or lending eligibility.

The publisher does not receive routine audio, subtitles, API keys or browsing records and does not operate a service for reviewing them. If you voluntarily share specific redacted information for support, it is used only for that support request; sharing a public issue is not permission to inspect other data. No human review of private local evidence is enabled by CueFlora. Your chosen AI services have their own policies; CueFlora makes no promise about their retention or model training. This data-use commitment is not a claim that Google has approved the extension or its native downloader.

Temporary processing files are removed with their processing directory. Local preferences/caches/protected keys remain until changed/removed or extension storage is cleared. Helper removal preserves settings/evidence and quarantines its owned runtime; removing the extension clears its storage according to Chrome behavior.

Evidence capture is off by default and enabled explicitly through a local environment setting. It retains audio, raw ASR/translation text and processing mappings. Credentials and signed media URLs are excluded, but audio/text can still be private. Users control deletion and sharing. Ordinary diagnostics contain IDs, counts, timings and reason codes, not subtitle text or credential payloads.

From 0.2.1, the extension retains up to 20 recent failure stage/reason/HTTP-status records in browser-session memory, surviving background-worker sleep but clearing on extension reload/update or browser restart. These records exclude credentials, service addresses, models, video IDs, subtitles and raw provider responses. User-triggered support reports add extension/helper versions and tool availability, and are not sent to the publisher automatically. You choose whether to copy or share a report. Retention failure is reported as incomplete history; it does not trigger new AI requests.

Contact the publisher through the linked support/contact route for privacy questions. Do not post API keys or private evidence publicly. These disclosures do not guarantee third-party deletion, filesystem backup erasure, or protection from malware running under your Windows account.

## Website and public support

This source/help website is hosted by GitHub Pages. GitHub handles website connections under its [Privacy Statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement). The publisher adds no analytics, tracking scripts or forms to these static pages.

Support uses GitHub Issues. Reports and replies are public when the repository is public. Posting is optional; use redacted details and do not submit API keys, encrypted credential records, signed URLs or private audio/subtitle captures. A public issue tracker is not a private channel for sensitive evidence.
