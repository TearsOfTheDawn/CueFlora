import { describe, expect, it } from 'vitest';
import {
    retimeEnglishTranslationCues,
    TRANSLATION_MAX_CUE_MS,
    translationCps,
} from '../translationPresentation';
import type { Cue } from '../types';

describe('English translation presentation timing', () => {
    it('extends a fast cue into an available gap', () => {
        const input: Cue[] = [
            { startMs: 0, endMs: 1000, text: 'x'.repeat(40) },
            { startMs: 3000, endMs: 4000, text: 'Later' },
        ];
        const result = retimeEnglishTranslationCues(input);
        expect(result.cues[0].endMs).toBe(2000);
        expect(translationCps(result.cues[0])).toBe(20);
        expect(result.diagnostics.extensions).toBeGreaterThan(0);
    });

    it('creates the fixed one-millisecond gap when source cues abut', () => {
        const result = retimeEnglishTranslationCues([
            { startMs: 0, endMs: 1000, text: 'First' },
            { startMs: 1000, endMs: 2000, text: 'Second' },
        ]);
        expect(result.cues[0].endMs).toBe(999);
        expect(result.cues[1].startMs - result.cues[0].endMs).toBe(1);
    });

    it('merges English cues without mutating the source cues', () => {
        const input: Cue[] = [
            { startMs: 0, endMs: 1000, text: 'x'.repeat(50) },
            { startMs: 1001, endMs: 4000, text: 'short text' },
        ];
        const snapshot = structuredClone(input);
        const result = retimeEnglishTranslationCues(input);
        expect(input).toEqual(snapshot);
        expect(result.cues).toHaveLength(1);
        expect(result.cues[0].text).toContain('short text');
        expect(result.diagnostics.merges).toBe(1);
        expect(result.sourceIndexes).toEqual([[0, 1]]);
        expect(result.diagnostics.maxCpsAfter).toBeLessThan(result.diagnostics.maxCpsBefore);
    });

    it('chooses the adjacent merge with the lower resulting CPS', () => {
        const result = retimeEnglishTranslationCues([
            { startMs: 0, endMs: 2000, text: 'short' },
            { startMs: 2001, endMs: 3001, text: 'x'.repeat(50) },
            { startMs: 3002, endMs: 6002, text: 'y'.repeat(40) },
        ]);
        expect(result.cues).toHaveLength(2);
        expect(result.cues[0].text).toBe(`short ${'x'.repeat(50)}`);
    });

    it('breaks equal-CPS merge ties toward the following cue', () => {
        const result = retimeEnglishTranslationCues([
            { startMs: 0, endMs: 1000, text: 'a'.repeat(20) },
            { startMs: 1001, endMs: 2001, text: 'x'.repeat(50) },
            { startMs: 2002, endMs: 3002, text: 'b'.repeat(20) },
        ]);
        expect(result.cues).toHaveLength(2);
        expect(result.cues[1].text).toBe(`${'x'.repeat(50)} ${'b'.repeat(20)}`);
    });

    it('leaves impossible fast cues bounded and reports their source indexes', () => {
        const result = retimeEnglishTranslationCues([
            { startMs: 0, endMs: 7000, text: 'x'.repeat(200) },
        ]);
        expect(result.cues[0].endMs - result.cues[0].startMs).toBe(TRANSLATION_MAX_CUE_MS);
        expect(result.diagnostics.fastCueCountAfter).toBe(1);
        expect(result.diagnostics.unresolvedFastCueIndexes).toEqual([0]);
    });

    it('reports before metrics from the original timing', () => {
        const result = retimeEnglishTranslationCues([
            { startMs: 0, endMs: 10000, text: 'x'.repeat(180) },
        ]);
        expect(result.diagnostics.fastCueCountBefore).toBe(0);
        expect(result.diagnostics.maxCpsBefore).toBe(18);
        expect(result.diagnostics.fastCueCountAfter).toBe(1);
    });

    it('always returns chronological non-overlapping cues no longer than seven seconds', () => {
        const result = retimeEnglishTranslationCues([
            { startMs: 0, endMs: 1000, text: 'a'.repeat(80) },
            { startMs: 1001, endMs: 2000, text: 'b'.repeat(80) },
            { startMs: 2001, endMs: 9000, text: 'c'.repeat(80) },
        ]);
        for (let index = 0; index < result.cues.length; index++) {
            const cue = result.cues[index];
            expect(cue.endMs - cue.startMs).toBeLessThanOrEqual(TRANSLATION_MAX_CUE_MS);
            if (index > 0) expect(cue.startMs).toBeGreaterThan(result.cues[index - 1].endMs);
        }
    });
});
