import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fakeBrowser } from 'wxt/testing/fake-browser';
import { state } from '../../../utils/state';
import { beginWorkflow } from '../../../utils/workflow';
import { TRANSCRIPTION_NORMALIZATION_VERSION } from '../../../utils/constants';
import { createCacheRepository, sha256, CACHE_PREFIX } from '../../../utils/cacheRepository';
import { getProviderSummary } from '../../../utils/providerClient';

vi.mock('../ui', () => ({ populateDropdowns: vi.fn() }));
vi.mock('../../../utils/providerClient', () => ({ getProviderSummary: () => ({ current: null, next: {
    revision: 'test-revision', cacheIdentities: { transcription: 'test-asr-identity', translation: 'test-translation-identity' },
    transcription: { label: 'Test', model: 'test-model' }, translation: { label: 'Test', model: 'test-model' },
} }) }));
vi.mock('../render', () => ({ startRenderLoop: vi.fn() }));
import { restoreGeneratedTracksFromCache, startTranscription, translateSubtitles } from '../api';

const source = [{ startMs: 0, endMs: 1000, text: '你好' }];
const key = 'cueflora_cache_U_V6Jqg7PV4_transcription:zh-CN';
const metaKey = 'cueflora_cache_U_V6Jqg7PV4_transcription_meta:zh-CN';
const sendMessage = vi.fn();

describe('production evidence and normalization cache boundaries', () => {
    it('preserves sparse repair capture mappings, context and safe workflow diagnostics', async () => {
        const original = Array.from({ length: 9 }, (_, i) => ({
            startMs: i * 10000, endMs: i * 10000 + 9000, text: `原文${i}`,
        }));
        state.transcriptionCues = original;
        state.workflow.diagnostics!.transcription.captureId = 'capture';
        let calls = 0;
        sendMessage.mockImplementation(async (message) => {
            if (message.type !== 'TRANSLATE_NATIVE') return { jobId: 'job', captured: true };
            calls++;
            return { jobId: 'job', requestCount: 1, translations: message.cues.map((cue: any, i: number) =>
                calls === 1 && [1, 4, 6].includes(i) ? '' : `Translated ${cue.text}`) };
        });
        await translateSubtitles('en', 'transcription:zh-CN', 'job');
        const requests = sendMessage.mock.calls.map(([message]) => message)
            .filter(message => message.type === 'TRANSLATE_NATIVE');
        expect(requests).toHaveLength(2);
        expect(requests[1].sourceIndexes).toEqual([1, 4, 6]);
        expect(requests[1].cues).toEqual([original[1], original[4], original[6]]);
        expect(requests[1].systemPrompt).toContain('input id 1 corresponds to source [S5]');
        expect(requests[1].systemPrompt).toContain('[T3] Translated 原文2');
        expect(requests[1].systemPrompt).toContain('[S8] 原文7');
        expect(requests[1].systemPrompt).not.toContain('[T5]');
        expect(state.translationCues.map(cue => cue.text)).toEqual(original.map(cue => `Translated ${cue.text}`));
        expect(state.workflow.diagnostics!.translation).toMatchObject({
            status: 'complete', physicalRequests: 2, repairCalls: 1,
            recoveryIssues: [1, 4, 6].map(cueIndex => ({ cueIndex, reason: 'empty' })),
            lastRecoveryAttempt: { call: 2, maxCalls: 8, kind: 'repair', sourceIndexes: [1, 4, 6] },
        });
        expect(JSON.stringify(state.workflow.diagnostics!.translation)).not.toContain('原文');
        const presentation = sendMessage.mock.calls.map(([message]) => message)
            .find(message => message.type === 'CAPTURE_PRESENTATION');
        expect(presentation.translations.map((cue: any) => cue.text)).toEqual(original.map(cue => `Translated ${cue.text}`));
    });

    beforeEach(async () => {
        fakeBrowser.reset();
        localStorage.clear();
        window.history.replaceState({}, '', '/watch?v=U_V6Jqg7PV4');
        document.title = 'Test';
        state.generatedTracks = {};
        state.transcriptionCues = [];
        state.translationCues = [];
        beginWorkflow('U_V6Jqg7PV4', true, 'job');
        sendMessage.mockReset();
        await fakeBrowser.storage.local.set({ cueflora_transcription_key: 'local', cueflora_translation_key: 'local' });
        const cache = createCacheRepository(fakeBrowser.storage.local);
        vi.spyOn(fakeBrowser.runtime, 'sendMessage').mockImplementation(async (message: any) => {
            if (message.type === 'PREFERENCES_SAVE') return { value: message.value };
            if (message.type === 'CACHE_PUT') return cache.put(message.key, message.cues, message.metadata);
            if (message.type === 'CACHE_LIST') return cache.list();
            if (message.type === 'CACHE_GET') return (await cache.list()).find(record => record.key === message.key) || null;
            return sendMessage(message);
        });
        localStorage.setItem('cueflora_transcription_model', 'test-model');
        localStorage.setItem('cueflora_transcription_url', 'http://localhost:8000/v1');
    });

    it('leaves legacy caches untouched and restores only validated extension records', async () => {
        localStorage.setItem('cueflora_cache_keys', JSON.stringify([key]));
        localStorage.setItem(key, JSON.stringify(source));
        await restoreGeneratedTracksFromCache();
        expect(state.generatedTracks).toEqual({});
        const cache = createCacheRepository(fakeBrowser.storage.local);
        await cache.put(key, source, { normalizationVersion: TRANSCRIPTION_NORMALIZATION_VERSION,
            fingerprint: await sha256(source), model: getProviderSummary().next.transcription.model,
            providerRevision: getProviderSummary().next.revision, providerIdentity: getProviderSummary().next.cacheIdentities?.transcription });
        await restoreGeneratedTracksFromCache();
        expect(state.generatedTracks['transcription:zh-CN']).toEqual(source);
        expect(localStorage.getItem(key)).toBe(JSON.stringify(source));
    });

    it('commits fresh matching native normalization metadata and capture identity', async () => {
        sendMessage.mockResolvedValue({ jobId: 'job', cues: source,
            diagnostics: { normalizationVersion: TRANSCRIPTION_NORMALIZATION_VERSION, captureId: 'capture' } });
        await startTranscription('zh-CN', 'job');
        const stored = await fakeBrowser.storage.local.get(CACHE_PREFIX + key);
        expect(stored[CACHE_PREFIX + key]).toMatchObject({ metadata: {
            normalizationVersion: TRANSCRIPTION_NORMALIZATION_VERSION, fingerprint: await sha256(source),
        } });
        expect(localStorage.getItem(metaKey)).toBeNull();
        expect(state.workflow.diagnostics?.transcription.captureId).toBe('capture');
    });
    it('does not restore generated records without matching endpoint/model identity', async () => {
        const cache = createCacheRepository(fakeBrowser.storage.local);
        const metadata = { normalizationVersion: TRANSCRIPTION_NORMALIZATION_VERSION,
            fingerprint: await sha256(source), model: getProviderSummary().next.transcription.model,
            providerRevision: getProviderSummary().next.revision };
        await cache.put(key, source, metadata);
        await restoreGeneratedTracksFromCache();
        expect(state.generatedTracks).toEqual({});
        await cache.put(key, source, { ...metadata, providerIdentity: 'other-provider' });
        await restoreGeneratedTracksFromCache();
        expect(state.generatedTracks).toEqual({});
    });

    it('rejects native version mismatch before state/cache commit', async () => {
        sendMessage.mockResolvedValue({ jobId: 'job', cues: source, diagnostics: { normalizationVersion: 'old' } });
        await expect(startTranscription('zh-CN', 'job')).rejects.toThrow('outdated');
        expect(localStorage.getItem(key)).toBeNull();
        expect(state.transcriptionCues).toEqual([]);
    });

    it('captures positional candidates and display mapping only when enabled', async () => {
        state.transcriptionCues = source;
        state.workflow.diagnostics!.transcription.captureId = 'capture';
        sendMessage.mockImplementation(async (message) => message.type === 'TRANSLATE_NATIVE'
            ? { jobId: 'job', translations: ['Hello'], requestCount: 1 }
            : { jobId: 'job', captured: true });
        await translateSubtitles('en', 'transcription:zh-CN', 'job');
        expect(sendMessage.mock.calls[0][0]).toMatchObject({ captureId: 'capture', sourceIndexes: [0] });
        expect(sendMessage.mock.calls[1][0]).toMatchObject({ type: 'CAPTURE_PRESENTATION',
            sourceCues: source, sourceIndexes: [[0]], translations: [{ ...source[0], text: 'Hello' }] });
        expect(state.workflow.diagnostics!.translation.physicalRequests).toBe(1);
    });

    it('keeps valid translations when evidence writes and presentation transport fail', async () => {
        state.transcriptionCues = source;
        state.workflow.diagnostics!.transcription.captureId = 'capture';
        sendMessage.mockImplementation(async (message) => {
            if (message.type === 'TRANSLATE_NATIVE') return {
                jobId: 'job', translations: ['Hello'], requestCount: 1,
                evidence: { complete: false, stages: { 'translation-response': 'incomplete' } },
            };
            throw new Error('Native capture disconnected');
        });
        await translateSubtitles('en', 'transcription:zh-CN', 'job');
        expect(state.translationCues[0].text).toBe('Hello');
        expect(state.workflow.diagnostics!.translation).toMatchObject({
            status: 'complete', physicalRequests: 1,
            evidence: { complete: false, stages: { presentation: 'incomplete', 'translation-response': 'incomplete' } },
        });
        expect(sendMessage.mock.calls.filter(([message]) => message.type === 'TRANSLATE_NATIVE')).toHaveLength(1);
    });
});
