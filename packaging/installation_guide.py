"""Short package-specific instructions; never infer installation or publication."""
import re


def render(release, version, acceptance=False):
    mode = release.get('mode') if isinstance(release, dict) else None
    identities = release.get('extensionIds', {}) if isinstance(release, dict) else {}
    identity = identities.get('chrome') if isinstance(identities, dict) else None
    if mode not in ('private', 'public') or not isinstance(identity, str) or not re.fullmatch('[a-p]{32}', identity):
        raise ValueError('Configured Chrome package required for installation guide')
    if not isinstance(version, str) or not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Exact package version required for installation guide')
    if not isinstance(acceptance, bool) or (acceptance and mode != 'public'):
        raise ValueError('Acceptance extension is only valid for a public-identity candidate')
    if release.get('distribution') == 'github':
        if mode != 'public' or not acceptance:
            raise ValueError('GitHub package must include its keyed unpacked extension')
        if release.get('extensionInventorySha256'):return paired_guide(identity,version)
        return github_guide(identity, version)
    if release.get('extensionInventorySha256'):return paired_guide(identity,version,private=mode=='private')
    label = 'private preview' if mode == 'private' else 'Store-bound candidate'
    lines = [f'# CueFlora {version} - Start here', '',
        f'Unsigned Windows x64 / Chrome {label}. This is an unreleased package, not Store approval or permission to redistribute.', '',
        f'Matching Chrome extension ID: `{identity}`.', '', '## Optional local use', '',
        '1. Extract the complete package before using its files.']
    if mode == 'private' or acceptance:
        folder = 'Chrome-preview' if mode == 'private' else 'Chrome-acceptance'
        lines += [f'2. In Chrome Extensions, enable Developer mode, choose Load unpacked, and select this package\'s `{folder}` folder.',
            '3. Run `CueFlora Setup.exe`, select Chrome and confirm Install. No Python, administrator access or PATH editing is required.',
            '4. Open CueFlora settings. Check the helper, connect your existing AI services, Save, and choose languages.',
            '5. Open a YouTube video, select the flower button, and press Run.']
    else:
        lines += ['2. No unpacked acceptance extension is included. Use only the matching Chrome Store extension after it becomes available; do not install this helper before then.']
    lines += ['', 'The Store-submission ZIP is not an unpacked preview. Do not load it expecting the same extension ID.', '',
        '## Existing CueFlora installation', '',
        'Disable any older CueFlora extension before loading a different CueFlora identity; do not run both CueFlora identities together.', '',
        'Setup refuses to take over a different extension identity. If you choose to replace an earlier CueFlora preview, remove its helper through its own Setup first, keep the old package for recovery, then install the matching new package. Settings and evidence are retained. Do not change or uninstall Substrata.', '',
        '## AI services and maintenance', '',
        'Your existing service supplies its API address, optional key and model name. Configure transcription and translation independently. CueFlora does not install models or start services, and does not choose a provider for you. Metadata checks do not generate subtitles; only Run starts AI work.', '',
        'Available YouTube captions can be used without AI or the helper; availability depends on the video. API use may cost money. Remembered keys use Windows user-scoped protection, not protection against malware running as the same user.', '',
        'Windows may warn about this unsigned installer. Do not disable antivirus. For repair, upgrade, rollback, recoverable uninstall and optional headless checks, see `INSTALLATION.md`.', '',
        'Read Third-party terms in Setup before confirming installation. CLI install/repair additionally requires `--accept-third-party-terms`; `terms` prints them without changing installation. Original component licences are retained. Keep the accompanying `CueFlora-third-party-sources.zip` available when sharing the binaries.', '',
        'Real-browser, clean-machine and visual acceptance remain separate from automated tests. Publication requires the outstanding licence, policy, screenshot and Store/publication gates.', '']
    return '\n'.join(lines)


def github_guide(identity, version):
    return f'''# CueFlora {version} - Start here

Windows x64 / Google Chrome. Unsigned installer. Chrome ID: `{identity}`.

## Install

1. Extract the complete Windows package to a permanent folder, not a temporary download preview.
2. Open `chrome://extensions`, enable Developer mode, click Load unpacked and select `Chrome-extension` (the folder containing `manifest.json`). Keep this folder after installation.
3. Run `CueFlora Setup.exe`, explicitly select Chrome, choose Install / Upgrade, read Third-party terms and confirm. No administrator access, separate Python installation or PATH changes are required.
4. Open CueFlora settings and check the helper connection. Connect your existing transcription and translation APIs independently: service address, optional API key and exact model name. Save explicitly. No service/model is supplied or started by CueFlora.
5. Choose languages, open a YouTube video, select the flower button and press Run. Only Run starts AI work. Available native captions may be used without AI or the helper.

Transcription needs a compatible `/audio/transcriptions` service; translation needs `/chat/completions` with structured JSON Schema output. A website subscription or ChatGPT login is not necessarily API access. Model-list checks use metadata only. Remote services require HTTPS; local loopback HTTP remains supported.

## Update without losing settings

Close the CueFlora settings tab and finish any active Run. Replace the files in your existing `Chrome-extension` folder with the new matching extension files, keeping the same manifest key/Chrome ID. Click Reload for CueFlora at `chrome://extensions`, then reload YouTube tabs. Do not remove the extension to update it. Run the new matching Setup for helper upgrades. Browser-managed or disabled Developer mode may prevent manual installation.

Different CueFlora identities do not share settings. Disable any older CueFlora identity first; do not run both CueFlora identities together. Setup refuses to take over a different identity. To replace an older preview, use its own Setup to uninstall its helper, keep the old package for recovery, then install the new one. Do not change or uninstall Substrata.

## Repair or remove

Use CueFlora Setup from the Start Menu for Repair, Roll back or Uninstall. Uninstall unregisters owned entries and moves runtime files into a recoverable removed folder; settings, evidence and maintenance copies remain. Remove the extension separately if desired. CLI install/repair requires `--apply --accept-third-party-terms`; installation also requires `--browser chrome`.

The helper runs on demand, not as a persistent service. Remembered API keys use Windows user-scoped protection, not protection against malware running as the same user. Hosted AI may cost money and model output may be inaccurate.

Do not disable antivirus or automatically bypass a warning. Verify the release and checksums. Automated tests do not establish real-browser or clean-machine acceptance. Keep the original notices and accompanying third-party sources when sharing binaries. Process only content you are entitled to use and comply with applicable terms and law.
'''


def paired_guide(identity,version,private=False):
    return f'''# CueFlora {version} — Start here

Windows x64 / Google Chrome. Unsigned {'development preview' if private else 'release candidate'}; not published by this build. Chrome ID: `{identity}`.

## New installation

1. Download and run **CueFlora Setup.exe**. It contains the helper, matching extension, audio tools and notices. Select Chrome, read the terms and confirm Install.
2. Setup shows one stable extension folder. Open `chrome://extensions`, enable Developer mode, choose **Load unpacked**, and select that folder (normally `%LOCALAPPDATA%\\CueFlora\\Chrome-extension`). Keep it in place. Setup does not silently install or remove Chrome extensions.
3. In CueFlora settings, check the helper and connect your existing AI services. Supply each service's API base address, optional API key and exact model ID. Alternatively, explicitly choose Continue with ChatGPT for translation only, complete sign-in yourself, load eligible models and choose one. Save explicitly. ChatGPT plan usage does not cover audio transcription.
4. Choose YouTube captions or configured AI for each language. Available captions require no AI service and depend on the video.
5. On YouTube, select the flower button and press **Run**. Only Run starts AI work. CueFlora does not install models or start AI services.

## Existing 0.1.13 installation — one-time manual bootstrap

Finish all Runs. Download this first new Setup manually. In Setup, select the exact **currently loaded CueFlora extension folder**, confirm adoption, then Install / Upgrade. Setup accepts only recognized, unmodified CueFlora files and keeps a recoverable backup. Do not remove/reinstall the extension: its identity and settings must stay unchanged. After Setup succeeds, click CueFlora **Reload** at `chrome://extensions` once and reload YouTube tabs. Setup never reads or changes Chrome profiles. A modified/foreign folder is refused without overwriting it.

## Later updates

{'Development previews use matching manual packages; public GitHub updates do not replace a development identity.' if private else 'In CueFlora settings: Check for updates → Download update → Install update. Confirm Install / Upgrade in Setup. Then Check installation → Restart CueFlora, and reload YouTube tabs. Only compatible stable releases from TearsOfTheDawn/CueFlora are used. No silent installs, resident updater or scheduled task is added.'}

Manual fallback: run the matching Setup and use Chrome Reload. Finish all tabs/profiles/native jobs first. Repair restores the matching pair; Roll back accepts a compatible previous pair. Automatic downgrade to 0.1.x is refused because it cannot safely read new account settings. Existing packages remain available for recovery.

## Privacy and removal

Saved API keys use user-scoped Windows protection. ChatGPT tokens stay exclusively in the helper's protected native account store. This does not defend against malware running as your Windows user. Account sign-in/model checks do not generate subtitles. Hosted APIs may charge; ChatGPT plan limits and credits apply to that optional route. No paid API fallback is automatic.

Use Setup from the Start Menu for Repair, Roll back or Uninstall. Uninstall unregisters owned helper/shortcut entries and quarantines owned runtime/extension files. Settings, protected accounts, evidence, maintenance copies and recoverable backups remain. Remove the Chrome extension separately if desired. Do not change or uninstall Substrata; do not run both CueFlora identities together.

Windows may warn about unsigned Setup. Do not disable security software or automatically bypass warnings. Checksums verify integrity, not protection against a compromised publisher account. Retain original notices and corresponding third-party sources when sharing binaries. Process only content you are entitled to use under applicable terms and law.

Automated checks are not genuine ChatGPT login, live Chrome updating, visual, clean-machine or semantic subtitle acceptance. This candidate does not authorise publication.
'''
