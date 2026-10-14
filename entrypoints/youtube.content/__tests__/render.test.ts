import { describe, it, expect, beforeEach } from 'vitest';
import { state } from '../../../utils/state';
import { STORAGE_PREFIX, langByBcp47 } from '../../../utils/constants';
import type { Cue } from '../../../utils/types';

// render.js helpers test — we test buildWordHighlightHtml indirectly via renderOverlay,
// and test cue-matching logic that startRenderLoop uses.

describe('cue matching logic', () => {
    // This tests the find-cue-by-time logic used in startRenderLoop
    function findCue(cues: Cue[], timeMs: number): Cue | null {
        return cues.find((c) => {
            return timeMs >= c.startMs && timeMs <= c.endMs;
        }) || null;
    }

    it('should find the correct cue at a given time', () => {
        const cues: Cue[] = [
            { startMs: 0, endMs: 1000, text: 'First' },
            { startMs: 1500, endMs: 3000, text: 'Second' },
            { startMs: 3500, endMs: 5000, text: 'Third' },
        ];

        expect(findCue(cues, 500)).toEqual(cues[0]);
        expect(findCue(cues, 2000)).toEqual(cues[1]);
        expect(findCue(cues, 4000)).toEqual(cues[2]);
    });

    it('should return null between cues (gap)', () => {
        const cues: Cue[] = [
            { startMs: 0, endMs: 1000, text: 'First' },
            { startMs: 2000, endMs: 3000, text: 'Second' },
        ];

        expect(findCue(cues, 1500)).toBeNull();
    });

    it('should match at exact start and end boundaries', () => {
        const cues: Cue[] = [
            { startMs: 1000, endMs: 2000, text: 'Test' },
        ];

        expect(findCue(cues, 1000)).toEqual(cues[0]);
        expect(findCue(cues, 2000)).toEqual(cues[0]);
    });

    it('should return null before first cue', () => {
        const cues: Cue[] = [
            { startMs: 1000, endMs: 2000, text: 'Test' },
        ];

        expect(findCue(cues, 0)).toBeNull();
        expect(findCue(cues, 999)).toBeNull();
    });

    it('should return null after last cue', () => {
        const cues: Cue[] = [
            { startMs: 1000, endMs: 2000, text: 'Test' },
        ];

        expect(findCue(cues, 2001)).toBeNull();
    });

    it('should handle empty cue array', () => {
        expect(findCue([], 1000)).toBeNull();
    });
});

describe('renderOverlay', () => {
    beforeEach(() => {
        document.body.innerHTML = '';
        state.showTranscription = true;
        state.showTranslation = true;
        state.highlightCurrentWord = false;
        state.subtitleBgOpacity = 75;
        state.overlayOffsetBottom = 60;
        localStorage.clear();
    });

    it('should not throw when overlay element is missing', async () => {
        // renderOverlay accesses DOM — should gracefully handle missing element
        const { renderOverlay } = await import('../render');
        expect(() => renderOverlay(undefined, undefined, 0)).not.toThrow();
    });

    it('should render transcription text into overlay', async () => {
        document.body.innerHTML = '<div id="cueflora-overlay"></div>';

        const { renderOverlay } = await import('../render');
        const cue: Cue = { startMs: 0, endMs: 1000, text: 'Hello world' };

        renderOverlay(cue, undefined, 500);

        const overlay = document.getElementById('cueflora-overlay')!;
        expect(overlay.innerHTML).toContain('Hello world');
        expect(overlay.innerHTML).toContain('cueflora-primary');
    });

    it('should render both transcription and translation', async () => {
        document.body.innerHTML = '<div id="cueflora-overlay"></div>';

        const { renderOverlay } = await import('../render');
        const transcriptionCue: Cue = { startMs: 0, endMs: 1000, text: 'Hello' };
        const translationCue: Cue = { startMs: 0, endMs: 1000, text: 'Hola' };

        renderOverlay(transcriptionCue, translationCue, 500);

        const overlay = document.getElementById('cueflora-overlay')!;
        expect(overlay.innerHTML).toContain('Hello');
        expect(overlay.innerHTML).toContain('Hola');
        expect(overlay.innerHTML).toContain('cueflora-primary');
        expect(overlay.innerHTML).toContain('cueflora-secondary');
    });

    it('should not render when showTranscription is false and no translation', async () => {
        document.body.innerHTML = '<div id="cueflora-overlay"></div>';
        state.showTranscription = false;

        const { renderOverlay } = await import('../render');
        const cue: Cue = { startMs: 0, endMs: 1000, text: 'Hidden' };

        renderOverlay(cue, undefined, 500);

        const overlay = document.getElementById('cueflora-overlay')!;
        expect(overlay.innerHTML).toBe('');
    });

    it('should clear overlay when no cues match', async () => {
        document.body.innerHTML = '<div id="cueflora-overlay">old content</div>';

        const { renderOverlay } = await import('../render');
        renderOverlay(undefined, undefined, 500);

        const overlay = document.getElementById('cueflora-overlay')!;
        expect(overlay.innerHTML).toBe('');
    });
});

describe('applyOverlaySettings', () => {
    beforeEach(() => {
        document.body.innerHTML = '';
        state.subtitleBgOpacity = 75;
        state.overlayOffsetBottom = 60;
    });

    it('should not throw when overlay element is missing', async () => {
        const { applyOverlaySettings } = await import('../render');
        expect(() => applyOverlaySettings()).not.toThrow();
    });

    it('should set CSS custom property and bottom offset', async () => {
        document.body.innerHTML = '<div id="cueflora-overlay"></div>';
        state.subtitleBgOpacity = 50;
        state.overlayOffsetBottom = 100;

        const { applyOverlaySettings } = await import('../render');
        applyOverlaySettings();

        const overlay = document.getElementById('cueflora-overlay')!;
        expect(overlay.style.getPropertyValue('--cueflora-bg-opacity')).toBe('0.5');
        expect(overlay.style.bottom).toBe('100px');
    });
});
