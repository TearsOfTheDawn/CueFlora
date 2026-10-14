import { describe, expect, it } from 'vitest';
import { privateDiagnostic, publicNativeResponse, validNativeResponse } from '../nativeResponse';

describe('native response boundary', () => {
    const request = { type: 'TRANSLATE_NATIVE', jobId: 'job', translateConfig: { apiKey: 'private-key', baseUrl: 'https://private.example/v1' } };
    it('redacts configured keys, endpoints and other URLs in diagnostic strings', () => {
        const safe = privateDiagnostic('private-key https://private.example/v1 private.example https://media.example/?sig=secret', request);
        expect(safe).not.toMatch(/private-key|private\.example|media\.example|sig=secret/);
    });
    it('rejects null, primitives, stale jobs and malformed progress', () => {
        for (const value of [null, 1, [], { jobId: 'old', translations: [], requestCount: 1 },
            { jobId: 'job', type: 'progress', stage: 'translate', percent: NaN },
            { jobId: 'job', type: 'progress', stage: 'translate', speed: {} }]) {
            expect(validNativeResponse(value, request)).toBe(false);
        }
    });
    it('preserves adequacy recovery ownership and requires physical request accounting', () => {
        expect(validNativeResponse({ jobId: 'job', translations: ['', null], requestCount: 1 }, request)).toBe(true);
        expect(validNativeResponse({ jobId: 'job', translations: ['Hello'] }, request)).toBe(false);
        expect(validNativeResponse({ jobId: 'job', error: 'failed', requestCount: 1 }, request)).toBe(true);
    });
    it('rejects malformed transcription timing without altering legitimate subtitle text', () => {
        const transcribe = { type: 'TRANSCRIBE_NATIVE', jobId: 'job' };
        expect(validNativeResponse({ jobId: 'job', cues: [{ text: '<script>literal</script>', startMs: 0, endMs: 1000 }] }, transcribe)).toBe(true);
        expect(validNativeResponse({ jobId: 'job', cues: [{ text: 'x', startMs: 1000, endMs: 0 }] }, transcribe)).toBe(false);
    });
    it('projects safe metrics and removes unknown nested diagnostic content', () => {
        const result = publicNativeResponse({ jobId: 'job', translations: ['Hello'], requestCount: 1,
            apiKey: 'secret', promptTokens: 'secret', completionTokens: 10,
            diagnostics: { apiKey: 'secret', audioDurationMs: Infinity, captureId: 'private/path', raw: 'private transcript' },
            evidence: { complete: true, stages: { 'translation-response': 'complete', 'secret': 'complete' } },
        }, request);
        expect(result).toMatchObject({ translations: ['Hello'], completionTokens: 10,
            evidence: { complete: false, stages: { 'invalid-diagnostic': 'incomplete' } } });
        expect(result).not.toHaveProperty('promptTokens');
        expect(JSON.stringify(result)).not.toMatch(/secret|private/);
    });
    it('strips extra cue fields but preserves literal cue text and word prefixes', () => {
        const cue = { text: 'literal <b>', startMs: 0, endMs: 1000, apiKey: 'secret',
            words: [{ text: 'literal', startMs: 0, endMs: 1000, prefix: ' ', raw: 'secret' }] };
        const result = publicNativeResponse({ cues: [cue] }, { type: 'TRANSCRIBE_NATIVE', jobId: 'job' });
        expect(JSON.stringify(result)).not.toContain('secret');
        expect(result.cues).toEqual([{ text: cue.text, startMs: 0, endMs: 1000,
            words: [{ text: 'literal', startMs: 0, endMs: 1000, prefix: ' ' }] }]);
    });
});
