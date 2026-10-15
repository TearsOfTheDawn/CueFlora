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
        'Setup refuses to take over a different extension identity. If you choose to replace an earlier CueFlora preview, remove its helper through its own Setup first, keep the old package for recovery, then install the matching new package. Settings and evidence are retained. Do not change or uninstall Substrata.', '',
        '## AI services and maintenance', '',
        'Your existing service supplies its API address, optional key and model name. Configure transcription and translation independently. CueFlora does not install models or start services, and does not choose a provider for you. Metadata checks do not generate subtitles; only Run starts AI work.', '',
        'Available YouTube captions can be used without AI or the helper; availability depends on the video. API use may cost money. Remembered keys use Windows user-scoped protection, not protection against malware running as the same user.', '',
        'Windows may warn about this unsigned installer. Do not disable antivirus. For repair, upgrade, rollback, recoverable uninstall and optional headless checks, see `INSTALLATION.md`.', '',
        'Real-browser, clean-machine and visual acceptance remain separate from automated tests. Publication requires the outstanding licence, policy, screenshot and Store/publication gates.', '']
    return '\n'.join(lines)
