# Permissions and helper installation — draft

Single purpose: configurable source subtitles and translations for the current YouTube video.

`nativeMessaging`: connects on demand to `cueflora_host` for user-triggered audio preparation/AI requests, metadata/capability checks and Windows credential protection/migration. It is not a continuously running companion. A saved-key request checks protection capability on the same native connection before dispatch.

`storage`: saves user-chosen providers, Windows-DPAPI encrypted keys, language/appearance settings, setup progress and validated bounded subtitle caches. Background mediation prevents saved-key payloads from reaching settings/player responses; session Runs retain opaque references. Legacy plaintext is removed only after verified protection/persistence. DPAPI does not protect against malware running as the same Windows user.

`https://*.youtube.com/*`: runs the player overlay and reads available caption/video metadata only on YouTube. A MAIN-world bridge accesses caption-track information; its IDs correlate replies, not authenticate page data. There is no `<all_urls>`, microphone, tab capture, browsing-history API or cookies permission in the manifest. Native network activity must still be disclosed.

Native remote-code worksheet: extension scripts are packaged locally. The helper's yt-dlp may download YouTube player JavaScript as challenge input and execute it through bundled Deno; local EJS code is packaged and remote component downloads disabled. Do not certify "no remote code anywhere" without policy review. Explain native behavior accurately and settle the blocker before submission.

Preview instructions: extract the full private package; load `Chrome-preview` as an unpacked extension; run its matching unsigned CueFlora Setup when you choose; explicitly select Chrome and confirm Install. No administrator access, Python/PATH editing or AI provisioning is intended. Never install into or repair Substrata. In extension settings, check the helper, supply your existing compatible service address/key/model, save, choose languages, then use the flower button and press Run. Captions can be used without AI/helper when the video provides them.

Future public flow: install the store extension and download its correctly store-ID-bound helper from the publisher's HTTPS page. That package does not exist yet; keyless candidates are not compatible with the development preview registration. Repairs/upgrades require a matching identity. Setup supports maintenance and recoverable uninstall; settings/evidence are retained. Public URLs, signing and clean-machine acceptance must be completed first.
