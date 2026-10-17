# Completed policy assessment: public-release hold

Date: 2026-10-17. Candidate: CueFlora 0.1.12, Windows x64 / Chrome. This is an evidence-backed engineering assessment, not legal advice, a finding of illegality, or Google's decision. No external reviewer was contacted.

## Conclusion

**Assessment complete; release not cleared.** The unresolved requirement is authorisation for the current automatic YouTube audio acquisition, not another general code audit. Available code/evidence does not establish that authorisation or an enforceable authorised-only acquisition boundary. This conclusion must not be changed to passed merely because the installer works, a disclaimer is added, or the Store later approves an item.

## Code actually reviewed

`native/cueflora_host/download.py` invokes bundled yt-dlp for the selected video's `worstaudio`, in a temporary directory, without a playlist or browser-cookie import. The frozen path uses fixed local tools, ignores unrelated configuration/plugins and disables remote EJS component downloads. Audio is prepared and sent to the chosen transcription provider after explicit Run. There is no media-export/offline-player UI. Those limits reduce scope; they are not evidence of permission to acquire arbitrary videos.

The local EJS solver may evaluate downloaded YouTube player JavaScript through bundled Deno. The child has no extension API bindings or permission-granting solver flags; validated messages/results cross the native boundary. Provider secrets are not solver inputs. Frozen environment isolation and synthetic permission probes were verified. This is not an OS sandbox or proof of resistance to every V8/native defect.

Extension scripts/styles are packaged locally. Subtitle/model responses become validated data/text nodes, not evaluated program code. Public requests require remote HTTPS; remembered keys use Windows user-scoped protection. The manifest requests nativeMessaging, storage and YouTube host access, not browsing-history, cookies, microphone, tabCapture or all-sites APIs.

## Published rules and application

The [Chrome Store policies](https://developer.chrome.com/docs/webstore/program-policies/policies) prohibit facilitating unauthorised copyrighted-media access/download and require truthful functionality/data disclosure. They do not declare every video downloader categorically forbidden. CueFlora's internal-only transcription use is relevant context, but it does not itself demonstrate authorisation. No claim of universal compliance follows.

[YouTube's terms, Permissions and Restrictions](https://www.youtube.com/static?template=terms) restrict downloading and automated access outside the permissions they identify, and address interference with protective features. Public playback availability is not a demonstrated grant for this separate helper workflow. No applicable permission has been supplied; ownership or a content licence alone must not be assumed to settle the separate service terms. Jurisdictional exceptions cannot be presumed to cover every user/video. This is the specific release hold.

[MV3 requirements](https://developer.chrome.com/docs/webstore/program-policies/mv3-requirements) include an exception for code isolated from extension APIs, subject to discernible functionality and data policies. A separate native Deno context provides a reasoned isolation argument, not an automatic approved exemption. The complete native challenge behaviour should be disclosed for Google to assess. [Native messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging) documents the process connection; it does not grant media rights or make every native operation acceptable.

The [YouTube API developer policies](https://developers.google.com/youtube/terms/developer-policies) cannot be cited as permission for this workflow. The source does not configure an official YouTube Data API client; whether additional API terms apply to accessed services needs the appropriate terms analysis. No supposed Data API exception is used to clear the hold.

## Narrow closure paths

1. Establish the necessary permission for the existing automated acquisition/challenge route and its intended scope; retain the evidence, reassess exact claims and only then clear the gate.
2. If that cannot be established, approve a separate design using an authorised audio-input route. Possible directions are user-supplied authorised audio or supported playback capture, but neither is built here or asserted automatically acceptable. Whole-video pre-generation and installation simplicity have tradeoffs requiring an explicit product decision.

Do not silently disable transcription, relabel downloaded code as data, add an unchecked ownership checkbox, bypass a safeguard, or imply that Store review grants content/service permission. No architecture change is authorised by this report.

## Submission and remaining external facts

The policy report and candid reviewer explanation are ready. The [dashboard guidance](https://developer.chrome.com/docs/webstore/cws-dashboard-privacy) requires accurate purpose, permission, remote-code and data disclosures. Listing drafts must describe native JavaScript execution rather than certify no remote code anywhere. [Listing guidance](https://developer.chrome.com/docs/webstore/cws-dashboard-listing) requires genuine product imagery; branding is not a live screenshot. Those account actions and Google's final decision cannot be performed from this environment without browser use, and are not claimed completed.

The dependency licensing/native-security work remains complete for the exact candidate. There is no newly invented paid-signing, mandatory external-auditor or routine manual-testing requirement. Public source/help hosting is separate from releasing the full download-enabled product.
