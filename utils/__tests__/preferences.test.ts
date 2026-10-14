import { describe, expect, it } from 'vitest';
import { createPreferencesService, PREFERENCES_KEY } from '../preferences';

describe('production preference migration', () => {
    function setup() {
        const data: Record<string,unknown> = {};
        const storage = { get: async () => structuredClone(data), set: async (items: Record<string,unknown>) => { Object.assign(data, structuredClone(items)); } };
        return { data, storage, service: createPreferencesService(storage) };
    }
    it('imports only validated preferences and leaves provider/cache input out', async () => {
        const {service} = setup();
        expect(await service.initialize({ cueflora_translation_url: 'https://evil.example', cueflora_translation_key: 'secret',
            cueflora_cache_old: '[]', cueflora_show_translation: '0', cueflora_transcription_lang: 'transcription:zh-CN',
            cueflora_translation_batch_size: '999', cueflora_highlight_current_word: '#ffffff' })).toEqual({
                cueflora_show_translation: '0', cueflora_transcription_lang: 'transcription:zh-CN', cueflora_translation_batch_size: '60',
            });
    });
    it('never reimports changed page data once migration has succeeded', async () => {
        const {service} = setup();
        await service.initialize({cueflora_show_translation:'1'});
        expect(await service.initialize({cueflora_show_translation:'0'})).toEqual({cueflora_show_translation:'1'});
    });
    it('retries migration after failed persistence', async () => {
        const {storage,data} = setup();
        let fail = true;
        const service = createPreferencesService({ ...storage, set: async items => { if(fail) throw Error('disk'); await storage.set(items); } });
        await expect(service.initialize({cueflora_show_translation:'0'})).rejects.toThrow('disk');
        expect(data[PREFERENCES_KEY]).toBeUndefined();
        fail = false;
        await expect(service.initialize({cueflora_show_translation:'0'})).resolves.toEqual({cueflora_show_translation:'0'});
    });
    it('merges concurrent preference writes without losing unrelated fields', async () => {
        const {service} = setup(); await service.initialize({});
        await Promise.all([service.save('cueflora_show_translation','0'),service.save('cueflora_show_transcription','1')]);
        expect(await service.initialize({})).toEqual({cueflora_show_translation:'0',cueflora_show_transcription:'1'});
        await expect(service.save('cueflora_translation_url','https://evil.example')).rejects.toThrow('Invalid');
    });
    it('revalidates stored fields and never returns unexpected private values', async () => {
        const { service, data } = setup();
        data[PREFERENCES_KEY] = { migrated: true, values: { cueflora_show_translation: '0',
            cueflora_translation_key: 'private-key', cueflora_appearance_v1: 'broken',
            cueflora_translation_url: 'https://private.example' } };
        expect(await service.initialize({ cueflora_show_transcription: '0' })).toEqual({ cueflora_show_translation: '0' });
        await service.save('cueflora_show_transcription', '1');
        expect(JSON.stringify(data[PREFERENCES_KEY])).not.toContain('private');
    });
    it('does not reimport page values when a completed record has corrupted values', async () => {
        const { service, data } = setup();
        data[PREFERENCES_KEY] = { migrated: true, values: ['invalid'] };
        expect(await service.initialize({ cueflora_show_translation: '0' })).toEqual({});
    });
});
