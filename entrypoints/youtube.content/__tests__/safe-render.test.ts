vi.mock('../../../utils/preferenceClient', () => ({
    preferences: { getItem: (key: string) => window.localStorage.getItem(key), setItem: (key: string, value: string) => window.localStorage.setItem(key,value) },
    initializePreferences: async () => {},
    savePreference: async (key: string, value: string) => window.localStorage.setItem(key,value),
}));
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import { renderOverlay, startRenderLoop } from '../render';
import { state } from '../../../utils/state';
import { defaults, setEffectiveAppearance, validateAppearance } from '../../../utils/appearance';

describe('production safe rendering', () => {
    beforeEach(() => {
        document.body.innerHTML = '<div id="movie_player"><video></video><div id="cueflora-overlay"></div></div>';
        localStorage.clear();
        localStorage.setItem('cueflora_transcription_lang', 'transcription:zh');
        state.showTranscription = true;
        state.showTranslation = true;
        setEffectiveAppearance(defaults());
    });
    afterEach(() => {
        if (state.activeInterval) clearInterval(state.activeInterval);
        state.activeInterval = null;
        setEffectiveAppearance(null);
        vi.useRealTimers();
    });
    it('renders markup and word prefixes literally', () => {
        const text = '<img src=x onerror=alert(1)>';
        renderOverlay({ startMs: 0, endMs: 1000, text, words: [
            { text, startMs: 0, endMs: 500 },
            { text: '&last', prefix: '<svg>', startMs: 500, endMs: 1000 },
        ] }, { startMs: 0, endMs: 1000, text: '<script>bad()</script>' }, 100);
        const overlay = document.getElementById('cueflora-overlay')!;
        expect(overlay.querySelector('img,svg,script')).toBeNull();
        expect(overlay.querySelector('.cueflora-primary')!.textContent).toBe(text + '<svg>&last');
    });
    it('builds pinyin from structured tokens without interpreting non-Chinese text', () => {
        setEffectiveAppearance({ ...defaults(), pinyin: true });
        renderOverlay({ startMs: 0, endMs: 1000, text: '你好 <img src=x>' }, undefined, 100);
        const overlay = document.getElementById('cueflora-overlay')!;
        expect(overlay.querySelector('img')).toBeNull();
        expect(overlay.querySelectorAll('ruby')).toHaveLength(2);
        expect(overlay.querySelector('rt')!.textContent).toBe('nǐ');
        expect(overlay.textContent).toContain(' <img src=x>');
    });
    it('rejects color strings in every non-color field', () => {
        const input = Object.fromEntries(Object.keys(defaults()).map(key => [key, '#ffffff']));
        const result = validateAppearance(input);
        expect(result.version).toBe(1);
        expect(result.sourceSize).toBe(22);
        expect(result.highlight).toBe(true);
        expect(result.sourceFont).toBe('sans');
        expect(result.background).toBe('#ffffff');
    });
    it('updates cues when seeking while paused', () => {
        vi.useFakeTimers();
        const video = document.querySelector('video')!;
        state.transcriptionCues = [{ startMs: 1000, endMs: 2000, text: 'Paused cue' }];
        state.translationCues = [];
        expect(video.paused).toBe(true);
        startRenderLoop();
        video.currentTime = 1.5;
        vi.advanceTimersByTime(100);
        expect(document.getElementById('cueflora-overlay')!.textContent).toBe('Paused cue');
    });
    it('preserves identical content nodes across ticks', () => {
        const cue = { startMs: 0, endMs: 1000, text: 'Stable' };
        renderOverlay(cue, undefined, 100);
        const node = document.querySelector('.cueflora-primary');
        renderOverlay(cue, undefined, 200);
        expect(document.querySelector('.cueflora-primary')).toBe(node);
    });
    it('changes only word classes when highlighting advances', () => {
        const cue = { startMs: 0, endMs: 1000, text: 'one two', words: [
            { text: 'one', startMs: 0, endMs: 500 },
            { text: 'two', startMs: 500, endMs: 1000 },
        ] };
        renderOverlay(cue, undefined, 100);
        const first = document.querySelector('.cueflora-word')!;
        const selection = window.getSelection()!;
        const range = document.createRange();
        range.selectNodeContents(first);
        selection.removeAllRanges();
        selection.addRange(range);
        renderOverlay(cue, undefined, 600);
        expect(document.querySelector('.cueflora-word')).toBe(first);
        expect(first.classList.contains('cueflora-word-active')).toBe(false);
        expect(document.querySelector('.cueflora-word-active')!.textContent).toBe('two');
        expect(selection.toString()).toBe('one');
    });
});
