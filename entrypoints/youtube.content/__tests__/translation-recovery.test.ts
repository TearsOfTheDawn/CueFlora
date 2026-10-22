import { describe, expect, it } from 'vitest';
import {
    recoverTranslationBatch,
    TranslationRequestError,
    validateTranslationOutput,
    type TranslationAttemptContext,
} from '../../../utils/translation';
import type { Cue } from '../../../utils/types';

const cues = (count: number): Cue[] => Array.from({ length: count }, (_, index) => ({
    startMs: index * 1000,
    endMs: index * 1000 + 900,
    text: `source ${index}`,
}));

describe('translation recovery', () => {
    it('repairs eight scattered runs together without exhausting the eight-call budget', async () => {
        const source = cues(30).map(cue => ({ ...cue,
            text: '现在院子里面所有的排水都从这里流出去，后面还需要把周围重新整理一下。' }));
        const bad = [0, 2, 4, 6, 8, 10, 12, 14, 15, 16, 17, 18];
        const attempts: TranslationAttemptContext[] = [];
        const resolved = new Map<number, Cue>();
        const result = await recoverTranslationBatch({
            cues: source, startIndex: 40, maxCalls: 8, maxSplitDepth: 2,
            enableEnglishAdequacyCheck: true,
            request: async (_, __, attempt) => {
                attempts.push(attempt);
                return attempt.sourceIndexes.map(index => attempt.call === 1 && bad.includes(index - 40)
                    ? 'Okay.' : `All the drainage flows out here and the surrounding area needs work, source ${index}.`);
            },
            onResolved: (index, cue) => resolved.set(index, cue),
        });
        expect(attempts).toHaveLength(2);
        expect(attempts[1].sourceIndexes).toEqual(bad.map(index => index + 40));
        expect(result.stats).toMatchObject({ calls: 2, qualityRepairs: 12, repairCalls: 1 });
        expect(result.cues.map(cue => cue.startMs)).toEqual(source.map(cue => cue.startMs));
        expect(result.cues.map(cue => cue.text)).toEqual(source.map((_, i) =>
            `All the drainage flows out here and the surrounding area needs work, source ${40 + i}.`));
        expect([...resolved.keys()].sort((a, b) => a - b)).toEqual(source.map((_, i) => 40 + i));
    });

    it('keeps sparse indexes and request-local labels aligned through nested repairs', async () => {
        const attempts: number[][] = [];
        const issues: unknown[] = [];
        const result = await recoverTranslationBatch({
            cues: cues(7), startIndex: 10, maxCalls: 8, maxSplitDepth: 2,
            request: async (_, __, attempt) => {
                attempts.push(attempt.sourceIndexes);
                if (attempt.call === 1) return ['', 'keep-11', '[Truncated]', 'keep-13', '4. leaked', 'keep-15', 'keep-16'];
                if (attempt.call === 2) return ['fixed-10', '1. still leaked', 'fixed-14'];
                return ['fixed-12'];
            },
            onValidationIssue: issue => issues.push(issue),
        });
        expect(attempts).toEqual([[10, 11, 12, 13, 14, 15, 16], [10, 12, 14], [12]]);
        expect(result.cues.map(cue => cue.text)).toEqual([
            'fixed-10', 'keep-11', 'fixed-12', 'keep-13', 'fixed-14', 'keep-15', 'keep-16',
        ]);
        expect(issues).toEqual([
            { cueIndex: 10, reason: 'empty' }, { cueIndex: 12, reason: 'truncated-marker' },
            { cueIndex: 14, reason: 'label-leak' }, { cueIndex: 12, reason: 'label-leak' },
        ]);
        expect(JSON.stringify(issues)).not.toMatch(/source|leaked|fixed/);
    });

    it('preserves sparse mappings through output-error retries and splits', async () => {
        const attempts: number[][] = [];
        const result = await recoverTranslationBatch({
            cues: cues(9), startIndex: 20, maxCalls: 8, maxSplitDepth: 2,
            request: async (_, __, attempt) => {
                attempts.push(attempt.sourceIndexes);
                if (attempt.call === 1) return ['', 'keep', '', 'keep', '', 'keep', '', 'keep', 'keep'];
                if (attempt.call === 2 || attempt.call === 3) throw new TranslationRequestError('invalid objects', true);
                return attempt.sourceIndexes.map(index => `fixed-${index}`);
            },
        });
        // Four-cue repair splits immediately at depth 1; two-cue child retries once.
        expect(attempts).toEqual([[20, 21, 22, 23, 24, 25, 26, 27, 28], [20, 22, 24, 26], [20, 22], [20, 22], [24, 26]]);
        expect(result.cues.filter((_, i) => i < 7 && i % 2 === 0).map(cue => cue.text))
            .toEqual(['fixed-20', 'fixed-22', 'fixed-24', 'fixed-26']);
        expect(result.stats.calls).toBe(5);
    });

    it('never dispatches a ninth request and counts only dispatched adequacy repairs', async () => {
        let calls = 0;
        let repairs = 0;
        await expect(recoverTranslationBatch({
            cues: cues(60), startIndex: 0, maxCalls: 8, maxSplitDepth: 2,
            request: async (group) => {
                calls++;
                // Salvage one position each time, leaving the rest structurally invalid.
                return group.map((_, i) => i === 0 ? 'valid' : '');
            },
            onQualityRepair: count => { repairs += count; },
        })).rejects.toThrow('8/8 model calls');
        expect(calls).toBe(8);
        expect(repairs).toBe(0);
        await expect(recoverTranslationBatch({
            cues: [{ startMs: 0, endMs: 1000, text: '一'.repeat(30) }],
            startIndex: 0, maxCalls: 1, maxSplitDepth: 2, enableEnglishAdequacyCheck: true,
            request: async () => ['Okay.'], onQualityRepair: count => { repairs += count; },
        })).rejects.toThrow('No extra request was sent');
        expect(repairs).toBe(0);
    });

    it('applies the one-time adequacy allowance to original sparse positions only', async () => {
        const flagged: number[] = [];
        const result = await recoverTranslationBatch({
            cues: cues(5).map(cue => ({ ...cue, text: '一'.repeat(30) })),
            startIndex: 60, maxCalls: 8, maxSplitDepth: 2, enableEnglishAdequacyCheck: true,
            request: async (_, __, attempt) => attempt.sourceIndexes.map(index => index % 2 === 0
                ? 'Okay.' : 'This is a complete translation with sufficient lexical content.'),
            onUnresolvedQuality: flag => flagged.push(flag.cueIndex),
        });
        expect(result.stats).toMatchObject({ calls: 2, qualityRepairs: 3, unresolvedQualityFlags: 3 });
        expect(flagged).toEqual([60, 62, 64]);
    });

    it('rejects label leakage while preserving legitimate source numbering', () => {
        const source = { startMs: 0, endMs: 1000, text: '你好' };
        expect(validateTranslationOutput(source, '[0] Hello', 0)).toMatchObject({
            valid: false,
            reason: 'label-leak',
        });
        expect(validateTranslationOutput(source, '[S12] Hello', 0)).toMatchObject({
            valid: false,
            reason: 'label-leak',
        });
        expect(validateTranslationOutput(
            { ...source, text: '2. 第二步' },
            '2. The second step',
            2
        )).toEqual({ valid: true, text: '2. The second step' });
        expect(validateTranslationOutput(
            { ...source, text: '2: 第二步' },
            '2. The second step',
            2
        )).toMatchObject({ valid: false, reason: 'label-leak' });
        expect(validateTranslationOutput(source, '2.5 million', 2)).toEqual({
            valid: true,
            text: '2.5 million',
        });
    });

    it('flags only extreme English under-translation', () => {
        const substantial = {
            startMs: 0,
            endMs: 5000,
            text: '现在院子里面所有的排水都从这里流出去，后面还需要把周围重新整理一下。',
        };
        expect(validateTranslationOutput(substantial, 'All done.', 0, true)).toMatchObject({
            valid: false,
            reason: 'extreme-under-translation',
        });
        expect(validateTranslationOutput(
            substantial,
            "It's really no big deal.",
            0,
            true
        )).toEqual({ valid: true, text: "It's really no big deal." });
        expect(validateTranslationOutput(
            { ...substantial, text: '没问题。' },
            'No problem.',
            0,
            true
        )).toEqual({ valid: true, text: 'No problem.' });
    });

    it('preserves positional timing and text alignment', async () => {
        const source = cues(3);
        const result = await recoverTranslationBatch({
            cues: source,
            startIndex: 0,
            maxCalls: 8,
            maxSplitDepth: 2,
            request: async () => ['A', 'B', 'C'],
        });
        expect(result.cues.map((cue) => cue.text)).toEqual(['A', 'B', 'C']);
        expect(result.cues.map((cue) => cue.startMs)).toEqual(source.map((cue) => cue.startMs));
        expect(result.stats.calls).toBe(1);
    });

    it('salvages valid positions and repairs only the bad adjacent run', async () => {
        const requested: number[][] = [];
        const source = cues(5);
        const result = await recoverTranslationBatch({
            cues: source,
            startIndex: 10,
            maxCalls: 8,
            maxSplitDepth: 2,
            request: async (group, start) => {
                requested.push([start, group.length]);
                return start === 10
                    ? ['A', '', '[Truncated]', 'D', 'E']
                    : ['B', 'C'];
            },
        });
        expect(requested).toEqual([[10, 5], [11, 2]]);
        expect(result.cues.map((cue) => cue.text)).toEqual(['A', 'B', 'C', 'D', 'E']);
        expect(result.stats).toMatchObject({ calls: 2, repairCalls: 1, salvagedPositions: 3 });
    });

    it('rejects ambiguous overlong output rather than guessing', async () => {
        let calls = 0;
        await expect(recoverTranslationBatch({
            cues: cues(2),
            startIndex: 0,
            maxCalls: 2,
            maxSplitDepth: 2,
            request: async () => {
                calls++;
                return ['A', 'B', 'EXTRA'];
            },
        })).rejects.toThrow(/positional alignment is ambiguous/);
        expect(calls).toBe(2);
    });

    it('repairs a leaked request label instead of displaying it', async () => {
        const requested: number[][] = [];
        const result = await recoverTranslationBatch({
            cues: cues(2),
            startIndex: 5,
            maxCalls: 8,
            maxSplitDepth: 2,
            request: async (group, start) => {
                requested.push([start, group.length]);
                return start === 5 ? ['First', '1. Second'] : ['Second'];
            },
        });
        expect(requested).toEqual([[5, 2], [6, 1]]);
        expect(result.cues.map((cue) => cue.text)).toEqual(['First', 'Second']);
    });

    it('enforces the physical request budget without retry explosion', async () => {
        let calls = 0;
        await expect(recoverTranslationBatch({
            cues: cues(20),
            startIndex: 0,
            maxCalls: 4,
            maxSplitDepth: 2,
            request: async () => {
                calls++;
                throw new TranslationRequestError('invalid JSON', true);
            },
        })).rejects.toThrow(/4 model calls|4\/4 model calls/);
        expect(calls).toBe(4);
    });

    it('does not retry network or configuration failures', async () => {
        let calls = 0;
        await expect(recoverTranslationBatch({
            cues: cues(10),
            startIndex: 0,
            maxCalls: 8,
            maxSplitDepth: 2,
            request: async () => {
                calls++;
                throw new TranslationRequestError('connection refused', false);
            },
        })).rejects.toThrow('connection refused');
        expect(calls).toBe(1);
    });

    it('repairs only a suspicious cue once', async () => {
        const source = cues(3);
        source[1].text = '现在院子里面所有的排水都从这里流出去，后面还需要把周围重新整理一下。';
        const requested: number[][] = [];
        const flags: number[] = [];
        const result = await recoverTranslationBatch({
            cues: source,
            startIndex: 20,
            maxCalls: 8,
            maxSplitDepth: 2,
            enableEnglishAdequacyCheck: true,
            request: async (group, start) => {
                requested.push([start, group.length]);
                return start === 20 ? ['First', 'All done.', 'Third'] : [
                    'All of the yard drainage flows out here, and the surrounding area still needs work.',
                ];
            },
            onQualityFlag: (flag) => flags.push(flag.cueIndex),
        });
        expect(requested).toEqual([[20, 3], [21, 1]]);
        expect(flags).toEqual([21]);
        expect(result.stats.qualityRepairs).toBe(1);
        expect(result.cues[1].text).toContain('yard drainage');
    });

    it('accepts a structurally valid second result with an unresolved quality warning', async () => {
        const source = [{
            startMs: 0,
            endMs: 5000,
            text: '现在院子里面所有的排水都从这里流出去，后面还需要把周围重新整理一下。',
        }];
        const unresolved: number[] = [];
        const result = await recoverTranslationBatch({
            cues: source,
            startIndex: 30,
            maxCalls: 8,
            maxSplitDepth: 2,
            enableEnglishAdequacyCheck: true,
            request: async () => ['All done.'],
            onUnresolvedQuality: (flag) => unresolved.push(flag.cueIndex),
        });
        expect(result.stats.calls).toBe(2);
        expect(result.stats.qualityRepairs).toBe(1);
        expect(result.stats.unresolvedQualityFlags).toBe(1);
        expect(unresolved).toEqual([30]);
        expect(result.cues[0].text).toBe('All done.');
    });
});
