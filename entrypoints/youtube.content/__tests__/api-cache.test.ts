import { describe, it, expect } from 'vitest';
import type { Cue } from '../../../utils/types';
import { createTranslationCacheMetadata, isTranslationCacheMetadataCurrent } from '../../../utils/cache';

// Persistence tests import createCacheRepository in utils/__tests__/cacheRepository.test.ts.
describe('translation cache semantic validity', () => {
    const source: Cue[] = [{ startMs: 0, endMs: 1000, text: '你好' }];

    it('accepts identical semantic inputs', () => {
        const metadata = createTranslationCacheMetadata(source, 'transcription:zh-CN', 'en', 'qwen2.5:7b');
        expect(isTranslationCacheMetadataCurrent(metadata, { ...metadata })).toBe(true);
    });

    it('invalidates on source, language, model, schema, or pipeline changes', () => {
        const metadata = createTranslationCacheMetadata(source, 'transcription:zh-CN', 'en', 'qwen2.5:7b');
        const changes = [
            { ...metadata, sourceFingerprint: 'different' },
            { ...metadata, sourceLanguage: 'transcription:ja' },
            { ...metadata, targetLanguage: 'fr' },
            { ...metadata, model: 'other-model' },
            { ...metadata, schemaVersion: metadata.schemaVersion + 1 },
            { ...metadata, pipelineVersion: 'old-pipeline' },
        ];
        for (const changed of changes) {
            expect(isTranslationCacheMetadataCurrent(changed, metadata)).toBe(false);
        }
    });

    it('invalidates legacy bare fingerprint metadata', () => {
        const metadata = createTranslationCacheMetadata(source, 'transcription:zh-CN', 'en', 'qwen2.5:7b');
        expect(isTranslationCacheMetadataCurrent('deadbeef', metadata)).toBe(false);
    });
});
