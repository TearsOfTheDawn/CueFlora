vi.mock('../../../utils/preferenceClient', () => ({
    preferences: { getItem: (key: string) => window.localStorage.getItem(key), setItem: (key: string, value: string) => window.localStorage.setItem(key,value) },
    initializePreferences: async () => {},
    savePreference: async (key: string, value: string) => window.localStorage.setItem(key,value),
}));
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { state } from '../../../utils/state';
import { STORAGE_PREFIX, LANGUAGES, langByBcp47 } from '../../../utils/constants';
import type { CaptionTrack } from '../../../utils/types';

// Test getTrackDisplayName logic (extracted from ui.js)
function getTrackDisplayName(t: CaptionTrack): string {
    const entry = langByBcp47(t.languageCode);
    if (entry) return entry.name;
    if (t.name && t.name.simpleText) return t.name.simpleText;
    if (t.languageName && t.languageName.simpleText) return t.languageName.simpleText;
    return t.languageCode;
}

// Test track deduplication logic (extracted from populateDropdowns)
function deduplicateTracks(tracks: CaptionTrack[]): CaptionTrack[] {
    const dedupTracks: CaptionTrack[] = [];
    const seenCodes: Record<string, boolean> = {};
    const seenNames: Record<string, boolean> = {};
    const sorted = tracks.slice().sort((a, b) => {
        if (a.kind === 'asr' && b.kind !== 'asr') return 1;
        if (a.kind !== 'asr' && b.kind === 'asr') return -1;
        return 0;
    });
    sorted.forEach((t) => {
        const code = t.languageCode;
        const name = getTrackDisplayName(t);
        if (!seenCodes[code] && !seenNames[name]) {
            dedupTracks.push(t);
            seenCodes[code] = true;
            seenNames[name] = true;
        }
    });
    return dedupTracks;
}

describe('getTrackDisplayName', () => {
    it('should use LANGUAGES name for known bcp47 codes', () => {
        expect(getTrackDisplayName({ languageCode: 'en' })).toBe('English (US)');
        expect(getTrackDisplayName({ languageCode: 'ja' })).toBe('Japanese');
        expect(getTrackDisplayName({ languageCode: 'zh-CN' })).toBe('Chinese (Simplified)');
    });

    it('should fall back to track name.simpleText', () => {
        expect(getTrackDisplayName({
            languageCode: 'unknown-code',
            name: { simpleText: 'Custom Track' }
        })).toBe('Custom Track');
    });

    it('should fall back to languageName.simpleText', () => {
        expect(getTrackDisplayName({
            languageCode: 'unknown-code',
            languageName: { simpleText: 'Custom Language' }
        })).toBe('Custom Language');
    });

    it('should fall back to raw languageCode', () => {
        expect(getTrackDisplayName({ languageCode: 'xx-YY' })).toBe('xx-YY');
    });
});

describe('track deduplication', () => {
    it('should prefer non-ASR tracks over ASR tracks', () => {
        const tracks: CaptionTrack[] = [
            { languageCode: 'en', kind: 'asr', name: { simpleText: 'English (auto)' } },
            { languageCode: 'en', kind: 'standard', name: { simpleText: 'English' } },
        ];
        const result = deduplicateTracks(tracks);
        expect(result).toHaveLength(1);
        expect(result[0].kind).toBe('standard');
    });

    it('should deduplicate by language code', () => {
        const tracks: CaptionTrack[] = [
            { languageCode: 'en', kind: 'standard' },
            { languageCode: 'en', kind: 'standard' },
            { languageCode: 'fr', kind: 'standard' },
        ];
        const result = deduplicateTracks(tracks);
        expect(result).toHaveLength(2);
    });

    it('should deduplicate by display name', () => {
        // Two tracks with different codes but same display name
        const tracks: CaptionTrack[] = [
            { languageCode: 'en', kind: 'standard' },
            { languageCode: 'en-US', kind: 'standard', name: { simpleText: 'English (US)' } },
        ];
        const result = deduplicateTracks(tracks);
        expect(result).toHaveLength(1);
    });

    it('should keep all tracks with different languages', () => {
        const tracks: CaptionTrack[] = [
            { languageCode: 'en', kind: 'standard' },
            { languageCode: 'fr', kind: 'standard' },
            { languageCode: 'de', kind: 'standard' },
        ];
        const result = deduplicateTracks(tracks);
        expect(result).toHaveLength(3);
    });

    it('should return empty array for empty input', () => {
        expect(deduplicateTracks([])).toEqual([]);
    });
});

describe('settings toggle parsing', () => {
    // This mirrors the pattern used in createUI for parsing boolean localStorage values
    function parseBoolSetting(value: string | null, defaultVal: boolean): boolean {
        if (value === null) return defaultVal;
        return value !== '0';
    }

    it('should return default when value is null', () => {
        expect(parseBoolSetting(null, true)).toBe(true);
        expect(parseBoolSetting(null, false)).toBe(false);
    });

    it('should return false for "0"', () => {
        expect(parseBoolSetting('0', true)).toBe(false);
    });

    it('should return true for "1"', () => {
        expect(parseBoolSetting('1', false)).toBe(true);
    });

    it('should return true for any non-"0" string', () => {
        expect(parseBoolSetting('yes', false)).toBe(true);
        expect(parseBoolSetting('true', false)).toBe(true);
    });
});

describe('atomic flower button and panel lifecycle', () => {
    beforeEach(() => {
        state._cleanupUI?.();
        state._cleanupUI = null;
        state.isPanelOpen = false;
        document.body.innerHTML = '';
        localStorage.clear();
    });

    it('creates no orphan button when the player is not ready', async () => {
        document.body.innerHTML = '<div class="ytp-right-controls"></div>';
        const { createUI } = await import('../ui');
        await createUI();
        expect(document.getElementById('cueflora-btn')).toBeNull();
        expect(document.getElementById('cueflora-panel')).toBeNull();
    });

    it('creates the button and panel together when both anchors exist', async () => {
        document.body.innerHTML =
            '<div id="movie_player"></div><div class="ytp-right-controls"></div>';
        const { createUI } = await import('../ui');
        await createUI();
        expect(document.getElementById('cueflora-btn')).not.toBeNull();
        expect(document.getElementById('cueflora-panel')).not.toBeNull();
        const button = document.getElementById('cueflora-btn')!;
        expect(button.tagName).toBe('BUTTON'); expect(button.getAttribute('aria-label')).toBe('CueFlora subtitles');
        expect(button.querySelector('svg')?.getAttribute('aria-hidden')).toBe('true');
        expect(button.querySelectorAll('circle')).toHaveLength(6);
        expect(button.textContent).not.toContain('S');
        for (const element of document.getElementById('cueflora-panel')!.querySelectorAll('[id]')) expect(element.id).toMatch(/^cueflora-/);
    });

    it('does not expose legacy provider inputs or interpolate page settings', async () => {
        document.body.innerHTML = '<div id="movie_player"></div><div class="ytp-right-controls"></div>';
        const payload = '\"><img id="injected-setting" src=x>';
        localStorage.setItem('cueflora_translation_model', payload);
        localStorage.setItem('cueflora_transcription_url', payload);
        const { createUI } = await import('../ui');
        await createUI();
        expect(document.getElementById('injected-setting')).toBeNull();
        expect(document.getElementById('cfg-translation-model')).toBeNull();
        expect(document.getElementById('cfg-transcription-url')).toBeNull();
        expect(document.getElementById('cfg-transcription-key')).toBeNull();
        expect(document.getElementById('cfg-translation-key')).toBeNull();
        expect(document.getElementById('cueflora-open-options')).not.toBeNull();
    });

    it('removes a partial old UI before rebuilding the pair', async () => {
        document.body.innerHTML =
            '<div id="movie_player"></div>' +
            '<div class="ytp-right-controls"><div id="cueflora-btn"></div></div>';
        const { createUI } = await import('../ui');
        await createUI();
        expect(document.querySelectorAll('#cueflora-btn')).toHaveLength(1);
        expect(document.getElementById('cueflora-panel')).not.toBeNull();
    });

    it('identifies selected native captions and Off in the player summary', async () => {
        document.body.innerHTML = '<div id="movie_player"></div><div class="ytp-right-controls"></div>';
        const { createUI } = await import('../ui');
        await createUI();
        const source = document.getElementById('cueflora-transcription-lang') as HTMLSelectElement;
        const target = document.getElementById('cueflora-translation-lang') as HTMLSelectElement;
        source.replaceChildren(new Option('Chinese <literal>', 'zh'));
        target.replaceChildren(new Option('Off', 'none'));
        document.dispatchEvent(new Event('cueflora-providers-changed'));
        const summary = document.getElementById('cueflora-provider-summary')!;
        expect(summary.textContent).toContain('YouTube captions / Chinese <literal>');
        expect(summary.textContent).toContain('Translation: Off');
        expect(summary.querySelector('literal')).toBeNull();
    });
});
