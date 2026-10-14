import { describe, it, expect } from 'vitest';
import { parseJson3, parseVttTime, parseVtt } from '../parsers';

describe('parseJson3', () => {
    it('should return empty array for null/undefined input', () => {
        expect(parseJson3(null)).toEqual([]);
        expect(parseJson3(undefined as any)).toEqual([]);
        expect(parseJson3({} as any)).toEqual([]);
    });

    it('should return empty array when events array is empty', () => {
        expect(parseJson3({ events: [] })).toEqual([]);
    });

    it('should skip events without tStartMs', () => {
        const result = parseJson3({
            events: [{ segs: [{ utf8: 'hello' }] }]
        });
        expect(result).toEqual([]);
    });

    it('should skip events without segs', () => {
        const result = parseJson3({
            events: [{ tStartMs: 1000 }]
        });
        expect(result).toEqual([]);
    });

    it('should skip append-only events (aAppend === 1)', () => {
        const result = parseJson3({
            events: [{ tStartMs: 1000, aAppend: 1, segs: [{ utf8: 'hello' }] }]
        });
        expect(result).toEqual([]);
    });

    it('should parse a single segment event into a cue', () => {
        const result = parseJson3({
            events: [{
                tStartMs: 1000,
                dDurationMs: 3000,
                segs: [{ utf8: 'Hello world' }]
            }]
        });
        expect(result).toHaveLength(1);
        expect(result[0].startMs).toBe(1000);
        expect(result[0].endMs).toBe(4000);
        expect(result[0].text).toBe('Hello world');
    });

    it('should parse multiple segments with tOffsetMs into words', () => {
        const result = parseJson3({
            events: [{
                tStartMs: 1000,
                dDurationMs: 5000,
                segs: [
                    { utf8: 'Hello', tOffsetMs: 0 },
                    { utf8: 'world', tOffsetMs: 500 }
                ]
            }]
        });
        expect(result).toHaveLength(1);
        expect(result[0].text).toBe('Hello world');
        expect(result[0].words).toHaveLength(2);
        expect(result[0].words![0]).toEqual({ text: 'Hello', startMs: 1000, endMs: 1500 });
        expect(result[0].words![1].text).toBe('world');
        expect(result[0].words![1].startMs).toBe(1500);
    });

    it('should strip HTML tags from segment text', () => {
        const result = parseJson3({
            events: [{
                tStartMs: 0,
                dDurationMs: 2000,
                segs: [{ utf8: '<b>Bold</b> <i>italic</i>' }]
            }]
        });
        expect(result[0].text).toBe('Bold italic');
    });

    it('should decode HTML entities', () => {
        const result = parseJson3({
            events: [{
                tStartMs: 0,
                dDurationMs: 2000,
                segs: [{ utf8: "it&#39;s a &quot;test&quot;" }]
            }]
        });
        expect(result[0].text).toBe("it's a \"test\"");
    });

    it('should skip pure newline segments', () => {
        const result = parseJson3({
            events: [{
                tStartMs: 0,
                dDurationMs: 2000,
                segs: [{ utf8: '\n' }, { utf8: 'Hello' }]
            }]
        });
        expect(result[0].text).toBe('Hello');
        expect(result[0].words).toHaveLength(1);
    });

    it('should skip events that result in empty text', () => {
        const result = parseJson3({
            events: [{
                tStartMs: 0,
                dDurationMs: 2000,
                segs: [{ utf8: '\n' }, { utf8: '  ' }]
            }]
        });
        expect(result).toEqual([]);
    });

    it('should clamp cue endMs against next cue startMs', () => {
        const result = parseJson3({
            events: [
                { tStartMs: 0, dDurationMs: 5000, segs: [{ utf8: 'First' }] },
                { tStartMs: 2000, dDurationMs: 3000, segs: [{ utf8: 'Second' }] }
            ]
        });
        expect(result).toHaveLength(2);
        // First cue's endMs should be clamped to second cue's startMs
        expect(result[0].endMs).toBeLessThanOrEqual(result[1].startMs);
    });

    it('should derive endMs from word timing when multiple words exist', () => {
        const result = parseJson3({
            events: [{
                tStartMs: 1000,
                dDurationMs: 10000,
                segs: [
                    { utf8: 'Hello', tOffsetMs: 0 },
                    { utf8: 'beautiful', tOffsetMs: 500 },
                    { utf8: 'world', tOffsetMs: 1000 }
                ]
            }]
        });
        // endMs should be derived from word timing, not dDurationMs
        // avgGap = (2000 - 1000) / 2 = 500, clamped between 200..500 = 500
        // endMs = 2000 + 500 = 2500
        expect(result[0].endMs).toBe(2500);
        expect(result[0].endMs).not.toBe(11000); // not tStartMs + dDurationMs
    });

    it('should set word endMs to next word startMs', () => {
        const result = parseJson3({
            events: [{
                tStartMs: 0,
                dDurationMs: 5000,
                segs: [
                    { utf8: 'A', tOffsetMs: 0 },
                    { utf8: 'B', tOffsetMs: 200 },
                    { utf8: 'C', tOffsetMs: 400 }
                ]
            }]
        });
        expect(result[0].words![0].endMs).toBe(200);
        expect(result[0].words![1].endMs).toBe(400);
        // Last word endMs = cue endMs
        expect(result[0].words![2].endMs).toBe(result[0].endMs);
    });
});

describe('parseVttTime', () => {
    it('should parse HH:MM:SS.mmm format', () => {
        expect(parseVttTime('00:01:30.500')).toBe(90500);
    });

    it('should parse MM:SS.mmm format', () => {
        expect(parseVttTime('01:30.500')).toBe(90500);
    });

    it('should parse zero time', () => {
        expect(parseVttTime('00:00:00.000')).toBe(0);
    });

    it('should handle hours correctly', () => {
        expect(parseVttTime('01:00:00.000')).toBe(3600000);
    });
});

describe('parseVtt', () => {
    it('should return empty array for empty input', () => {
        expect(parseVtt('')).toEqual([]);
    });

    it('should parse a simple VTT file', () => {
        const vtt = [
            'WEBVTT',
            '',
            '1',
            '00:00:01.000 --> 00:00:04.000',
            'Hello world',
            '',
            '2',
            '00:00:05.000 --> 00:00:08.000',
            'Second line',
        ].join('\n');

        const result = parseVtt(vtt);
        expect(result).toHaveLength(2);
        expect(result[0].startMs).toBe(1000);
        expect(result[0].endMs).toBe(4000);
        expect(result[0].text).toBe('Hello world');
        expect(result[1].startMs).toBe(5000);
        expect(result[1].text).toBe('Second line');
    });

    it('should strip HTML tags from VTT text', () => {
        const vtt = [
            'WEBVTT',
            '',
            '00:00:01.000 --> 00:00:04.000',
            '<b>Bold text</b>',
        ].join('\n');

        const result = parseVtt(vtt);
        expect(result[0].text).toBe('Bold text');
    });

    it('should combine multi-line cue text', () => {
        const vtt = [
            'WEBVTT',
            '',
            '00:00:01.000 --> 00:00:04.000',
            'Line one',
            'Line two',
            '',
            '00:00:05.000 --> 00:00:08.000',
            'Next cue',
        ].join('\n');

        const result = parseVtt(vtt);
        expect(result[0].text).toBe('Line one Line two');
    });

    it('should handle MM:SS.mmm timestamps', () => {
        const vtt = [
            'WEBVTT',
            '',
            '01:30.000 --> 02:00.000',
            'Some text',
        ].join('\n');

        const result = parseVtt(vtt);
        expect(result[0].startMs).toBe(90000);
        expect(result[0].endMs).toBe(120000);
    });

    it('should not include word-level timing (VTT has none)', () => {
        const vtt = [
            'WEBVTT',
            '',
            '00:00:01.000 --> 00:00:04.000',
            'Hello',
        ].join('\n');

        const result = parseVtt(vtt);
        expect(result[0].words).toBeUndefined();
    });
});
