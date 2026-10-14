import { describe, expect, it } from 'vitest';
import {
    recoverTranslationBatch,
    TranslationRequestError,
    validateTranslationOutput,
} from '../../../utils/translation';
import type { Cue } from '../../../utils/types';

const cues = (count: number): Cue[] => Array.from({ length: count }, (_, index) => ({
    startMs: index * 1000,
    endMs: index * 1000 + 900,
    text: `source ${index}`,
}));

describe('translation recovery', () => {
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
