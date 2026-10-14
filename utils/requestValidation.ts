import { validCues } from './cacheRepository';

const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value);
const text = (value: unknown, max: number): value is string => typeof value === 'string' && value.length <= max;

/** Validate client shapes before resolving private settings or opening a port. */
export function validateRequest(message: Record<string, unknown>): void {
    const fail = () => { throw Error('Invalid extension request.'); };
    const type = message.type;
    if (['PROVIDERS_BIND', 'PROVIDERS_RELEASE', 'TRANSCRIBE_NATIVE', 'TRANSLATE_NATIVE', 'CAPTURE_PRESENTATION'].includes(String(type))) {
        if (!text(message.jobId, 100) || !/^[a-zA-Z0-9_:-]+$/.test(message.jobId)) fail();
    }
    if (['CACHE_GET', 'CACHE_REMOVE', 'CACHE_PUT', 'PREFERENCES_SAVE'].includes(String(type)) &&
        (!text(message.key, 256) || !message.key)) fail();
    if (type === 'PREFERENCES_SAVE' && !text(message.value, 10000)) fail();
    if (type === 'PREFERENCES_INIT' && !record(message.legacy)) fail();
    if (type === 'PROVIDERS_SAVE' && !record(message.settings)) fail();
    if (type === 'CREDENTIAL_PROTECT' && (!['transcription','translation'].includes(String(message.stage)) ||
        !text(message.baseUrl,2048) || !text(message.apiKey,8192) || !message.apiKey ||
        !text(message.requestId,80) || !/^[a-zA-Z0-9_-]+$/.test(message.requestId as string) || message.credential !== undefined)) fail();
    if (type === 'PROVIDERS_CHECK' && message.stage !== undefined && !['transcription','translation'].includes(String(message.stage))) fail();
    if (type === 'PROVIDERS_CHECK' && (!record(message.provider) || !text(message.requestId, 80) ||
        !/^[a-zA-Z0-9_-]+$/.test(message.requestId as string))) fail();
    if (type === 'PROVIDERS_BIND' && !text(message.revision, 100)) fail();
    if (type === 'ONBOARDING_FINISH' && (!text(message.revision,100) || !record(message.languages) ||
        !text(message.languages.transcription,60) || !text(message.languages.translation,60))) fail();
    if (type === 'TRANSCRIBE_NATIVE') {
        if (!text(message.videoId, 11) || !/^[a-zA-Z0-9_-]{11}$/.test(message.videoId)) fail();
        if (message.whisperConfig !== undefined) {
            if (!record(message.whisperConfig)) return fail();
            const config = message.whisperConfig;
            if (config.language != null && !text(config.language, 40)) fail();
            if (config.prompt !== undefined && !text(config.prompt, 20000)) fail();
            for (const key of ['maxParallel', 'mbPerReq']) {
                if (config[key] !== undefined && (typeof config[key] !== 'number' || !Number.isFinite(config[key]))) fail();
            }
        }
    }
    if (type === 'TRANSLATE_NATIVE') {
        if (!Array.isArray(message.cues) || !message.cues.length || message.cues.length > 60 ||
            !message.cues.every(cue => record(cue) && text(cue.text, 100000)) ||
            !text(message.systemPrompt, 100000) || !message.systemPrompt) fail();
    }
    if (type === 'CAPTURE_PRESENTATION') {
        if (!text(message.captureId, 44)) fail();
        if (!validCues(message.sourceCues) || !validCues(message.translations) || !validCues(message.displayCues) ||
            !Array.isArray(message.sourceIndexes) || !Array.isArray(message.displayCues) ||
            message.sourceIndexes.length !== message.displayCues.length ||
            !message.sourceIndexes.every(group => Array.isArray(group) && group.length > 0 &&
                group.every(index => Number.isSafeInteger(index) && index >= 0))) return fail();
        const indexes = message.sourceIndexes.flat();
        const sourceCount = message.sourceCues.length;
        // Presentation may merge/reorder cues, but every original position is retained once.
        if (message.translations.length !== sourceCount ||
            indexes.length !== sourceCount || new Set(indexes).size !== indexes.length ||
            indexes.some(index => index >= sourceCount)) fail();
    }
    if (message.captureId !== undefined && (!text(message.captureId, 44) || !/^[A-Za-z0-9_-]{11}\/[a-f0-9]{32}$/.test(message.captureId))) fail();
}
