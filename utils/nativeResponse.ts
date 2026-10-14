import { validCues } from './cacheRepository';
import { TRANSCRIPTION_NORMALIZATION_VERSION } from './constants';
import type { Cue, EvidenceDiagnostics } from './types';
import { validCredential } from './credentials';

const object = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value);
const evidenceStages = new Set(['capture-open', 'normalizer', 'normalizer-source', 'download-tool', 'source-metadata',
    'source', 'prepared', 'audio-preparation', 'asr-config', 'upload', 'asr-attempt', 'chunk-layout', 'normalization',
    'translation-mapping', 'translation-request', 'translation-response', 'presentation']);
function evidence(value: unknown): EvidenceDiagnostics | undefined {
    if (value === undefined) return;
    const result: EvidenceDiagnostics = { complete: true, stages: {} };
    if (!object(value) || typeof value.complete !== 'boolean' || !object(value.stages)) {
        return { complete: false, stages: { 'invalid-diagnostic': 'incomplete' } };
    }
    result.complete = value.complete;
    for (const [key, status] of Object.entries(value.stages)) {
        if (!evidenceStages.has(key) || (status !== 'complete' && status !== 'incomplete')) {
            result.complete = false; result.stages['invalid-diagnostic'] = 'incomplete';
        } else {
            result.stages[key] = status;
            if (status === 'incomplete') result.complete = false;
        }
    }
    return result;
}

/** Project only supported public fields; never forward arbitrary nested payloads. */
export function publicNativeResponse(value: Record<string, unknown>, request: Record<string, unknown>): Record<string, unknown> {
    const result: Record<string, unknown> = {};
    if (request.type === 'CREDENTIAL_PROTECT') return typeof value.error === 'string'
        ? {requestId:request.requestId, error:'Windows key protection unavailable or invalid. Upgrade/Repair CueFlora; no plaintext was saved.'}
        : {requestId:request.requestId, credential:value.credential};
    if (request.type === 'PROVIDERS_CHECK') return { requestId: request.requestId, status: value.status,
        models: value.models, reason: value.reason };
    if (request.jobId !== undefined) result.jobId = request.jobId;
    const protectedRequest = ['whisperConfig','translateConfig','provider'].some(field=>object(request[field]) && object(request[field].credential));
    if (typeof value.error === 'string') result.error = protectedRequest
        ? 'Protected provider request failed. Check the service/key settings; upgrade or repair CueFlora if needed.'
        : privateDiagnostic(value.error, request);
    if (['output', 'network', 'auth', 'http', 'protocol'].includes(String(value.errorKind))) result.errorKind = value.errorKind;
    if (value.requestCount === 0 || value.requestCount === 1) result.requestCount = value.requestCount;
    if (value.type === 'progress') {
        result.type = 'progress';
        result.stage = protectedRequest ? (['download','compress','prepare','chunk','transcribe','merge','translate','upload','audio-preparation'].includes(String(value.stage)) ? value.stage : 'processing')
            : typeof value.stage === 'string' ? privateDiagnostic(value.stage, request) : 'unknown';
        for (const key of ['message', 'speed']) if (typeof value[key] === 'string') {
            if (protectedRequest) { if(key === 'message') result.message = 'Processing '+result.stage+'…'; }
            else result[key] = privateDiagnostic(value[key], request);
        }
        if (typeof value.percent === 'number') result.percent = value.percent;
        return result;
    }
    if (request.type === 'PING' && value.status === 'PONG') {
        result.status = 'PONG';
        result.version = typeof value.version === 'string' && /^(\d+\.\d+\.\d+[-\w.]*|development \(uninstalled\))$/.test(value.version) ? value.version : 'unavailable';
        const tools = object(value.tools) ? value.tools : {};
        result.tools = Object.fromEntries(['yt-dlp', 'ffmpeg', 'ffprobe', 'deno'].map(name => [name, { available: object(tools[name]) && tools[name].available === true }]));
        result.helperUpgradeRequired = !object(tools.deno);
        result.capabilities = {credentialProtection: object(value.capabilities) && value.capabilities.credentialProtection === 'windows-dpapi-v1' ? 'windows-dpapi-v1' : null};
    }
    if (validCues(value.cues)) result.cues = value.cues.map((cue: Cue) => ({ startMs: cue.startMs, endMs: cue.endMs, text: cue.text,
        ...(cue.words ? { words: cue.words.map(word => ({ text: word.text, startMs: word.startMs, endMs: word.endMs,
            ...(word.prefix !== undefined ? { prefix: word.prefix } : {}) })) } : {}) }));
    if (Array.isArray(value.translations)) result.translations = value.translations.map(text => typeof text === 'string' ? text : null);
    if (value.captured === true) result.captured = true;
    for (const key of ['requestedOutputTokens', 'promptTokens', 'completionTokens', 'totalTokens', 'reasoningTokens', 'durationMs']) {
        if (typeof value[key] === 'number' && Number.isFinite(value[key]) && value[key] >= 0) result[key] = value[key];
    }
    if (['stop', 'length', 'content_filter', 'tool_calls', 'function_call', 'unknown'].includes(String(value.finishReason))) result.finishReason = value.finishReason;
    if (['none', 'minimal', 'low', 'medium', 'high'].includes(String(value.reasoningEffort))) result.reasoningEffort = value.reasoningEffort;
    if (value.evidence !== undefined) result.evidence = evidence(value.evidence);
    if (object(value.diagnostics)) {
        const diagnostics: Record<string, unknown> = {};
        for (const key of ['emptySegmentCount', 'audioDurationMs', 'rawSegmentCount', 'finalCueCount', 'collapsedWordsRemoved', 'repetitionSanitizations']) {
            const metric = value.diagnostics[key];
            if (typeof metric === 'number' && Number.isFinite(metric) && metric >= 0) diagnostics[key] = metric;
        }
        diagnostics.normalizationVersion = value.diagnostics.normalizationVersion === TRANSCRIPTION_NORMALIZATION_VERSION ? TRANSCRIPTION_NORMALIZATION_VERSION : 'unknown';
        const captureId = value.diagnostics.captureId;
        if (typeof captureId === 'string' && /^[A-Za-z0-9_-]{11}\/[a-f0-9]{32}$/.test(captureId)) diagnostics.captureId = captureId;
        if (value.diagnostics.evidence !== undefined) diagnostics.evidence = evidence(value.diagnostics.evidence);
        result.diagnostics = diagnostics;
    }
    return result;
}

export function privateDiagnostic(value: string, request: Record<string, unknown>): string {
    let text = value;
    for (const config of [request, ...['whisperConfig', 'translateConfig', 'provider'].map(field=>request[field] as Record<string, unknown> | undefined)]) {
        const blob = object(config?.credential) ? config.credential.blob : undefined;
        if (typeof blob === 'string' && blob) text = text.split(blob).join('[redacted]');
        for (const key of ['apiKey', 'baseUrl']) {
            const secret = config?.[key];
            if (typeof secret === 'string' && secret) text = text.split(secret).join('[redacted]');
            if (key === 'baseUrl' && typeof secret === 'string') {
                try { text = text.split(new URL(secret).host).join('[endpoint]'); } catch { /* Invalid configuration is rejected before dispatch. */ }
            }
        }
    }
    return text.replace(/https?:\/\/[^\s<>"']+/gi, '[endpoint]').slice(0, 500);
}

/** Validate the envelope, not translation adequacy (owned by translation.ts). */
export function validNativeResponse(value: unknown, request: Record<string, unknown>): value is Record<string, unknown> {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
    const result = value as Record<string, unknown>;
    if (request.type === 'CREDENTIAL_PROTECT') return result.requestId === request.requestId &&
        (typeof result.error === 'string' || validCredential(result.credential));
    if (request.type === 'PROVIDERS_CHECK') return result.requestId === request.requestId &&
        ['connected','unavailable','unsupported'].includes(String(result.status)) &&
        ['ok','auth','http','network','unsupported','invalid-response','oversized'].includes(String(result.reason)) &&
        Array.isArray(result.models) && result.models.length <= 500 && result.models.every(id => typeof id === 'string' && /^[\w.:/\-]{1,200}$/.test(id));
    if (request.type !== 'PING' && result.jobId !== request.jobId) return false;
    if (result.type === 'progress') return typeof result.stage === 'string' &&
        (result.speed === undefined || typeof result.speed === 'string') &&
        (result.message === undefined || typeof result.message === 'string') &&
        (result.percent === undefined || (typeof result.percent === 'number' && Number.isFinite(result.percent) && result.percent >= 0 && result.percent <= 100));
    if (result.error !== undefined) return typeof result.error === 'string' &&
        (request.type !== 'TRANSLATE_NATIVE' || result.requestCount === 0 || result.requestCount === 1);
    if (request.type === 'PING') return result.status === 'PONG' && !!result.tools && typeof result.tools === 'object';
    if (request.type === 'TRANSCRIBE_NATIVE') return validCues(result.cues);
    if (request.type === 'TRANSLATE_NATIVE') return Array.isArray(result.translations) && result.translations.length <= 60 && result.requestCount === 1;
    if (request.type === 'CAPTURE_PRESENTATION') return result.captured === true;
    return false;
}
