import { describe, expect, it } from 'vitest';
import { validateRequest } from '../requestValidation';
import { retimeEnglishTranslationCues } from '../translationPresentation';

describe('client message shape boundary', () => {
    it('rejects malformed configuration, identifiers and bounded text before native dispatch', () => {
        for (const request of [
            { type: 'TRANSCRIBE_NATIVE', jobId: 'job', videoId: 'U_V6Jqg7PV4', whisperConfig: [] },
            { type: 'TRANSCRIBE_NATIVE', jobId: 'job', videoId: 'U_V6Jqg7PV4', whisperConfig: { mbPerReq: Infinity } },
            { type: 'TRANSLATE_NATIVE', jobId: 'job', cues: [{ text: 5 }], systemPrompt: 'Translate' },
            { type: 'PROVIDERS_RELEASE', jobId: '../other' },
            { type: 'PROVIDERS_SAVE', settings: null },
            { type: 'CACHE_GET', key: {} },
            { type: 'PREFERENCES_INIT', legacy: [] },
        ]) expect(() => validateRequest(request)).toThrow('Invalid extension request');
    });
    it('accepts ordinary translation without altering literal text', () => {
        const request = { type: 'TRANSLATE_NATIVE', jobId: 'job', cues: [{ text: '<b>literal</b>' }], systemPrompt: 'Translate' };
        expect(() => validateRequest(request)).not.toThrow();
        expect(request.cues[0].text).toBe('<b>literal</b>');
    });
    it('rejects invalid capture references and presentation mappings', () => {
        expect(() => validateRequest({ type: 'CAPTURE_PRESENTATION', jobId: 'job', captureId: '../private' })).toThrow();
        expect(() => validateRequest({ type: 'CAPTURE_PRESENTATION', jobId: 'job', sourceCues: [], translations: [], displayCues: [], sourceIndexes: [[-1]] })).toThrow();
    });
    it('accepts production presentation mappings without changing them', () => {
        const sourceCues = [{ text: 'One long sentence that requires merging.', startMs: 0, endMs: 500 },
            { text: 'Next.', startMs: 501, endMs: 1000 }];
        const presented = retimeEnglishTranslationCues(sourceCues);
        const request = { type: 'CAPTURE_PRESENTATION', jobId: 'job', captureId: `U_V6Jqg7PV4/${'a'.repeat(32)}`,
            sourceCues, translations: sourceCues, displayCues: presented.cues, sourceIndexes: presented.sourceIndexes };
        const original = JSON.stringify(request);
        expect(() => validateRequest(request)).not.toThrow();
        expect(JSON.stringify(request)).toBe(original);
    });
    it('rejects missing, duplicate, out-of-range and empty source mapping groups', () => {
        const cues = [{ text: 'One', startMs: 0, endMs: 1000 }, { text: 'Two', startMs: 1001, endMs: 2000 }];
        const request = { type: 'CAPTURE_PRESENTATION', jobId: 'job', captureId: `U_V6Jqg7PV4/${'a'.repeat(32)}`,
            sourceCues: cues, translations: cues, displayCues: cues };
        for (const sourceIndexes of [[[0], [0]], [[0], [2]], [[], [1]], [[0], [1, 2]]]) {
            expect(() => validateRequest({ ...request, sourceIndexes })).toThrow();
        }
        expect(() => validateRequest({ ...request, translations: cues.slice(0, 1), sourceIndexes: [[0], [1]] })).toThrow();
    });
});
