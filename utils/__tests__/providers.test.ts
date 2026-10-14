import { describe, expect, it } from 'vitest';
import { createProviderService, providerDefaults, providerSummary, providerSummaryWithIdentity, validateProvider } from '../providers';

describe('private provider configuration', () => {
    it('has no hidden endpoints, keys, models or connection-kind selection', async () => {
        const value = providerDefaults();
        for (const stage of ['transcription','translation'] as const) {
            expect(value[stage]).toMatchObject({ baseUrl:'', model:'', apiKey:'' });
            expect(value[stage].connectionKind).toBeUndefined();
            expect(validateProvider(value[stage]).model).toBe('');
        }
        const summary = await providerSummaryWithIdentity(value);
        expect(summary.transcription).toMatchObject({ configured:false, label:'Not configured' });
        expect(summary.cacheIdentities).toEqual({ transcription:'', translation:'' });
    });
    const service = () => {
        const data: Record<string, unknown> = {};
        return createProviderService({ get: async () => structuredClone(data), set: async values => { Object.assign(data, structuredClone(values)); } });
    };
    it('rejects credentials in URLs and unacknowledged remote HTTP', () => {
        const base = { ...providerDefaults().transcription, model: 'test-model' };
        for (const baseUrl of ['file:///test', 'https://user:password@example.com/v1', 'https://example.com/v1?key=secret', 'http://example.com/v1']) {
            expect(() => validateProvider({ ...base, baseUrl })).toThrow();
        }
        expect(validateProvider({ ...base, baseUrl: 'http://localhost:8000/v1/' }).baseUrl).toBe('http://localhost:8000/v1');
        expect(validateProvider({ ...base, baseUrl: 'http://example.com/v1', allowRemoteHttp: true }).allowRemoteHttp).toBe(true);
    });
    it('returns only explicit nonsecret summary fields', () => {
        const settings = providerDefaults();
        settings.transcription.apiKey = 'private-key';
        settings.transcription.baseUrl = 'https://private.example/v1';
        const summary = JSON.stringify(providerSummary(settings));
        expect(summary).not.toContain('private-key');
        expect(summary).not.toContain('private.example');
        expect(summary).not.toContain('baseUrl');
    });
    it('serializes concurrent saves and rejects stale revisions', async () => {
        const store = service();
        const initial = providerDefaults();
        const results = await Promise.allSettled([store.save(initial), store.save(initial)]);
        expect(results.filter(result => result.status === 'fulfilled')).toHaveLength(1);
        const saved = await store.read();
        expect(saved.revision).not.toBe('');
        await expect(store.save(initial)).rejects.toThrow('changed elsewhere');
    });
    it('does not report a failed persistence as saved', async () => {
        const store = createProviderService({ get: async () => ({}), set: async () => { throw Error('quota'); } });
        await expect(store.save(providerDefaults())).rejects.toThrow('quota');
        expect((await store.read()).revision).toBe('');
    });
    it('fingerprints endpoint and model without including credentials or labels', async () => {
        const settings = providerDefaults();
        settings.transcription.baseUrl = 'https://source.example/v1'; settings.transcription.model = 'asr';
        settings.translation.baseUrl = 'https://target.example/v1'; settings.translation.model = 'translator';
        const original = await providerSummaryWithIdentity(settings);
        settings.translation.apiKey = 'new-secret'; settings.translation.label = 'New label';
        expect((await providerSummaryWithIdentity(settings)).cacheIdentities).toEqual(original.cacheIdentities);
        settings.translation.baseUrl = 'https://different.example/v1';
        const changed = await providerSummaryWithIdentity(settings);
        expect(changed.cacheIdentities?.translation).not.toBe(original.cacheIdentities?.translation);
        expect(changed.cacheIdentities?.transcription).toBe(original.cacheIdentities?.transcription);
        expect(JSON.stringify(changed)).not.toContain('different.example');
        settings.translation.model = 'other-model';
        expect((await providerSummaryWithIdentity(settings)).cacheIdentities?.translation).not.toBe(changed.cacheIdentities?.translation);
    });
});
