import { describe, it, expect } from 'vitest';
import { parseJson3, parseVtt } from '../../../utils/parsers';
import type { Cue, Word } from '../../../utils/types';

// Tests that verify data flows between parsers and rendering logic —
// the shape contracts that TS interfaces will enforce.

describe('cue shape contracts', () => {
    it('parseJson3 cues should have startMs, endMs, text, and words', () => {
        const result = parseJson3({
            events: [{
                tStartMs: 1000,
                dDurationMs: 3000,
                segs: [
                    { utf8: 'Hello', tOffsetMs: 0 },
                    { utf8: 'world', tOffsetMs: 500 }
                ]
            }]
        });

        const cue = result[0];
        expect(typeof cue.startMs).toBe('number');
        expect(typeof cue.endMs).toBe('number');
        expect(typeof cue.text).toBe('string');
        expect(Array.isArray(cue.words)).toBe(true);
        expect(cue.startMs).toBeLessThan(cue.endMs);
    });

    it('parseJson3 words should have text, startMs, and endMs', () => {
        const result = parseJson3({
            events: [{
                tStartMs: 0,
                dDurationMs: 3000,
                segs: [
                    { utf8: 'A', tOffsetMs: 0 },
                    { utf8: 'B', tOffsetMs: 500 }
                ]
            }]
        });

        const word = result[0].words![0];
        expect(typeof word.text).toBe('string');
        expect(typeof word.startMs).toBe('number');
        expect(typeof word.endMs).toBe('number');
    });

    it('parseVtt cues should have startMs, endMs, and text (no words)', () => {
        const vtt = [
            'WEBVTT', '',
            '00:00:01.000 --> 00:00:04.000',
            'Hello world',
        ].join('\n');

        const cue = parseVtt(vtt)[0];
        expect(typeof cue.startMs).toBe('number');
        expect(typeof cue.endMs).toBe('number');
        expect(typeof cue.text).toBe('string');
        expect(cue.words).toBeUndefined();
    });

    it('all cue timing values should be non-negative integers', () => {
        const result = parseJson3({
            events: [
                { tStartMs: 0, dDurationMs: 1000, segs: [{ utf8: 'A', tOffsetMs: 0 }, { utf8: 'B', tOffsetMs: 200 }] },
                { tStartMs: 1500, dDurationMs: 2000, segs: [{ utf8: 'C' }] }
            ]
        });

        result.forEach((cue) => {
            expect(cue.startMs).toBeGreaterThanOrEqual(0);
            expect(cue.endMs).toBeGreaterThanOrEqual(0);
            expect(Number.isInteger(cue.startMs) || cue.startMs === Math.floor(cue.startMs)).toBe(true);
            if (cue.words) {
                cue.words.forEach((w) => {
                    expect(w.startMs).toBeGreaterThanOrEqual(0);
                    expect(w.endMs).toBeGreaterThanOrEqual(0);
                });
            }
        });
    });
});

describe('cue ordering contracts', () => {
    it('parsed cues should be in chronological order', () => {
        const result = parseJson3({
            events: [
                { tStartMs: 0, dDurationMs: 1000, segs: [{ utf8: 'First' }] },
                { tStartMs: 2000, dDurationMs: 1000, segs: [{ utf8: 'Second' }] },
                { tStartMs: 4000, dDurationMs: 1000, segs: [{ utf8: 'Third' }] }
            ]
        });

        for (let i = 1; i < result.length; i++) {
            expect(result[i].startMs).toBeGreaterThanOrEqual(result[i - 1].startMs);
        }
    });

    it('words within a cue should be in chronological order', () => {
        const result = parseJson3({
            events: [{
                tStartMs: 0,
                dDurationMs: 5000,
                segs: [
                    { utf8: 'The', tOffsetMs: 0 },
                    { utf8: 'quick', tOffsetMs: 200 },
                    { utf8: 'brown', tOffsetMs: 400 },
                    { utf8: 'fox', tOffsetMs: 600 }
                ]
            }]
        });

        const words = result[0].words!;
        for (let i = 1; i < words.length; i++) {
            expect(words[i].startMs).toBeGreaterThanOrEqual(words[i - 1].startMs);
        }
    });

    it('word endMs should never exceed cue endMs', () => {
        const result = parseJson3({
            events: [{
                tStartMs: 0,
                dDurationMs: 3000,
                segs: [
                    { utf8: 'A', tOffsetMs: 0 },
                    { utf8: 'B', tOffsetMs: 500 },
                    { utf8: 'C', tOffsetMs: 1000 }
                ]
            }]
        });

        const cue = result[0];
        cue.words!.forEach((w) => {
            expect(w.endMs).toBeLessThanOrEqual(cue.endMs);
        });
    });

    it('cue endMs should not exceed next cue startMs (clamping)', () => {
        const result = parseJson3({
            events: [
                { tStartMs: 0, dDurationMs: 5000, segs: [{ utf8: 'Long first' }] },
                { tStartMs: 1000, dDurationMs: 2000, segs: [{ utf8: 'Quick second' }] }
            ]
        });

        expect(result[0].endMs).toBeLessThanOrEqual(result[1].startMs);
    });
});

describe('cache serialization round-trip', () => {
    it('JSON3 cues should survive JSON stringify/parse', () => {
        const original = parseJson3({
            events: [{
                tStartMs: 12345,
                dDurationMs: 6789,
                segs: [
                    { utf8: 'Hello', tOffsetMs: 0 },
                    { utf8: 'world', tOffsetMs: 500 }
                ]
            }]
        });

        const roundTripped = JSON.parse(JSON.stringify(original));
        expect(roundTripped).toEqual(original);
    });

    it('VTT cues should survive JSON stringify/parse', () => {
        const vtt = [
            'WEBVTT', '',
            '00:01:30.500 --> 00:02:00.000',
            'Test subtitle line',
        ].join('\n');

        const original = parseVtt(vtt);
        const roundTripped = JSON.parse(JSON.stringify(original));
        expect(roundTripped).toEqual(original);
    });
});
