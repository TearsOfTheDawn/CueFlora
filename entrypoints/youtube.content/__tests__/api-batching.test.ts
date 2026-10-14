import { describe, expect, it } from 'vitest';
import { buildContextualBatches, buildTranslationContextLines } from '../../../utils/translation';
import type { Cue } from '../../../utils/types';

const makeCues = (count: number, text = 'line'): Cue[] =>
    Array.from({ length: count }, (_, index) => ({
        startMs: index * 1000,
        endMs: (index + 1) * 1000,
        text: `${text}-${index}`,
    }));

describe('contextual translation batching', () => {
    it('uses non-overlapping output windows', () => {
        const cues = makeCues(65);
        const batches = buildContextualBatches(cues, 30, 2400);
        expect(batches.map((batch) => batch.cues.length)).toEqual([30, 30, 5]);
        expect(batches.map((batch) => batch.startIndex)).toEqual([0, 30, 60]);
        expect(batches.flatMap((batch) => batch.cues)).toEqual(cues);
    });

    it('honors the source-character cap before the cue target', () => {
        const cues = makeCues(8, '123456789');
        const batches = buildContextualBatches(cues, 30, 25);
        expect(batches.every((batch) => batch.cues.length <= 2)).toBe(true);
        expect(batches.flatMap((batch) => batch.cues)).toEqual(cues);
    });

    it('keeps one oversized cue so batching always advances', () => {
        const cues = [{ startMs: 0, endMs: 1000, text: 'x'.repeat(3000) }];
        const batches = buildContextualBatches(cues, 30, 2400);
        expect(batches).toHaveLength(1);
        expect(batches[0].sourceChars).toBe(3000);
    });

    it('handles empty input', () => {
        expect(buildContextualBatches([], 30, 2400)).toEqual([]);
    });

    it('builds previous bilingual and forward source-only context without central cues', () => {
        const cues = makeCues(10);
        const translated: Array<Cue | undefined> = [];
        translated[2] = { ...cues[2], text: 'translated-2' };
        translated[3] = { ...cues[3], text: 'translated-3' };
        const lines = buildTranslationContextLines(cues, translated, 4, 7, 2, 2);
        const text = lines.join('\n');
        expect(text).toContain('[S3] line-2');
        expect(text).toContain('[T3] translated-2');
        expect(text).toContain('[S8] line-7');
        expect(text).not.toContain('[S5] line-4');
        expect(text).not.toContain('[T8]');
    });
});
