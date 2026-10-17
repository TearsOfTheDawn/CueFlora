# Reviewer information — prepared, not submitted

Current version: 0.1.12. Existing Store item: akcolbcdfnjcahhhodnpablekjagfadf. Windows x64 / Chrome. Policy hold: see POLICY_ASSESSMENT.md; the native audio route is not represented as authorised/approved.

## Architecture and accounts

The extension supplies the actual YouTube subtitle overlay, appearance controls, caption handling, configuration and orchestration. An on-demand native messaging helper supplies audio tools and provider requests. There is no CueFlora account, publisher AI server, model provisioning or automatic generation on navigation. AI use needs compatible services/API access selected by the user; no shared reviewer credentials or provider credits have been created.

## Non-inference inspection

1. Install the extension and open its toolbar settings action. Caption-only use can skip AI/helper configuration, subject to the video's available tracks.
2. After release clearance and real hosting, run the matching unsigned Setup, explicitly select Chrome and confirm Install. Setup modifies per-user CueFlora entries, not Substrata or unrelated registrations.
3. Check helper connection from settings. This reports tool/capability health, not live ASR/translation compatibility.
4. Provider fields start blank. Hosted/local choices are equal; stage address/model/key are supplied independently. Model discovery, when explicitly requested and supported, is metadata-only. Manual model entry remains available.
5. Configure languages. Open the flower button on YouTube to inspect source/translation display and Appearance. Save/Cancel and Apply/Cancel retain separate drafts. Only an explicit trusted Run action starts AI requests.

Full AI testing requires suitable authorised content, the resolved acquisition-policy route, the installed helper and working external services. These dependencies cannot be replaced with a fabricated test account or a mocked screenshot. The publisher has deferred clean-Windows/real-Chrome functional testing; automated checks do not pretend to establish it.

## Remote native execution and privacy

The downloader's local EJS code can evaluate fetched YouTube player JavaScript through Deno in a separate process without extension API bindings. The helper never sends executable provider output into extension eval. Frozen execution ignores unrelated plugins/configuration, disables remote solver components/self-updates and removes inherited Deno broker/auth/logging/telemetry overrides. Known dependency findings have scoped recorded assessments, not a zero-vulnerability claim.

Audio chunks go to the chosen transcription service; subtitle text/languages/limited video context go to the chosen translation service. Saved keys use Windows DPAPI. The publisher has no routine receiver for audio, captions, keys or browsing records. Opt-in local evidence capture can contain private content and remains off by default.

## Question to resolve before release

The current full-video AI path temporarily downloads YouTube audio through a native helper. The source does not establish the required service/content permission for general use. No paywall/login-cookie import or media-export UI is provided, but those facts are not claimed to grant permission. If seeking official clarification, provide this full description and ask whether a specifically authorised scope/alternative input route is required. No clarification request has been sent from Codex and no answer is presumed.

Source and current release documents: https://github.com/TearsOfTheDawn/CueFlora
Privacy: https://tearsofthedawn.github.io/CueFlora/privacy.html
Support: https://github.com/TearsOfTheDawn/CueFlora/issues
