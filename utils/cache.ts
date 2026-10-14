import {
    TRANSLATION_CACHE_SCHEMA_VERSION,
    TRANSLATION_PIPELINE_VERSION,
} from './constants';
import type { Cue, TranslationCacheMetadata } from './types';

export const cueFingerprint = (cues: Cue[]): string => {
    let hash = 0x811c9dc5;
    for (const cue of cues) {
        const value = `${Math.round(cue.startMs)}|${Math.round(cue.endMs)}|${cue.text}\n`;
        for (let i = 0; i < value.length; i++) {
            hash ^= value.charCodeAt(i);
            hash = Math.imul(hash, 0x01000193);
        }
    }
    return (hash >>> 0).toString(16).padStart(8, '0');
};

export const createTranslationCacheMetadata = (
    sourceCues: Cue[],
    sourceLanguage: string,
    targetLanguage: string,
    model: string
): TranslationCacheMetadata => ({
    schemaVersion: TRANSLATION_CACHE_SCHEMA_VERSION,
    pipelineVersion: TRANSLATION_PIPELINE_VERSION,
    sourceFingerprint: cueFingerprint(sourceCues),
    sourceLanguage,
    targetLanguage,
    model,
});

export const isTranslationCacheMetadataCurrent = (
    value: unknown,
    expected: TranslationCacheMetadata
): value is TranslationCacheMetadata => {
    if (!value || typeof value !== 'object') return false;
    const actual = value as Partial<TranslationCacheMetadata>;
    return actual.schemaVersion === expected.schemaVersion &&
        actual.pipelineVersion === expected.pipelineVersion &&
        actual.sourceFingerprint === expected.sourceFingerprint &&
        actual.sourceLanguage === expected.sourceLanguage &&
        actual.targetLanguage === expected.targetLanguage &&
        actual.model === expected.model;
};
