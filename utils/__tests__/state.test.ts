import { describe, it, expect, beforeEach } from 'vitest';
import { state } from '../state';

describe('state singleton', () => {
    it('should export a state object', () => {
        expect(state).toBeDefined();
        expect(typeof state).toBe('object');
    });

    it('should have the expected initial fields', () => {
        expect(state).toHaveProperty('activeInterval');
        expect(state).toHaveProperty('initInterval');
        expect(state).toHaveProperty('transcriptionCues');
        expect(state).toHaveProperty('translationCues');
        expect(state).toHaveProperty('availableTracks');
        expect(state).toHaveProperty('generatedTracks');
        expect(state).toHaveProperty('subtitleCache');
        expect(state).toHaveProperty('isPanelOpen');
        expect(state).toHaveProperty('showTranscription');
        expect(state).toHaveProperty('showTranslation');
        expect(state).toHaveProperty('highlightCurrentWord');
        expect(state).toHaveProperty('workflow');
        expect(state).toHaveProperty('overlayOffsetBottom');
        expect(state).toHaveProperty('subtitleBgOpacity');
    });

    it('should have correct default values', () => {
        expect(state.activeInterval).toBeNull();
        expect(state.initInterval).toBeNull();
        expect(state.isPanelOpen).toBe(false);
        expect(state.showTranscription).toBe(true);
        expect(state.showTranslation).toBe(true);
        expect(state.highlightCurrentWord).toBe(true);
        expect(state.workflow.status).toBe('idle');
        expect(state.workflow.jobId).toBeNull();
        expect(state.overlayOffsetBottom).toBe(60);
        expect(state.subtitleBgOpacity).toBe(75);
    });

    it('should have arrays initialized as empty', () => {
        expect(Array.isArray(state.transcriptionCues)).toBe(true);
        expect(Array.isArray(state.translationCues)).toBe(true);
        expect(Array.isArray(state.availableTracks)).toBe(true);
        expect(state.transcriptionCues).toHaveLength(0);
        expect(state.translationCues).toHaveLength(0);
        expect(state.availableTracks).toHaveLength(0);
    });

    it('should have objects initialized as empty', () => {
        expect(typeof state.generatedTracks).toBe('object');
        expect(typeof state.subtitleCache).toBe('object');
        expect(Object.keys(state.generatedTracks)).toHaveLength(0);
        expect(Object.keys(state.subtitleCache)).toHaveLength(0);
    });

    it('should be mutable (state is shared mutable singleton)', () => {
        state.isPanelOpen = true;
        expect(state.isPanelOpen).toBe(true);

        state.transcriptionCues = [{ startMs: 0, endMs: 1000, text: 'test' }];
        expect(state.transcriptionCues).toHaveLength(1);

        // Reset for other tests
        state.isPanelOpen = false;
        state.transcriptionCues = [];
    });
});
