import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fakeBrowser } from 'wxt/testing';
import { createCacheRepository, CACHE_PREFIX, validCues } from '../cacheRepository';
import { CACHE_POLICY } from '../cachePolicy';

describe('production cache repository', () => {
    beforeEach(() => fakeBrowser.reset());
    const cue = [{ text: '你好', startMs: 0, endMs: 1000 }];
    it('stores cues and metadata as one record with SHA-256 integrity', async () => {
        const repo = createCacheRepository(fakeBrowser.storage.local);
        const record = await repo.put('video:zh', cue, { model: 'test' });
        expect(record.checksum).toMatch(/^[a-f0-9]{64}$/);
        expect(await repo.list()).toEqual([record]);
        await fakeBrowser.storage.local.set({ [CACHE_PREFIX + record.key]: { ...record, cues: [{ ...cue[0], text: 'tampered' }] } });
        expect(await repo.list()).toEqual([]);
    });
    it('serializes concurrent writes and bounds the inventory', async () => {
        const repo = createCacheRepository(fakeBrowser.storage.local);
        await Promise.all(Array.from({ length: 25 }, (_, i) => repo.put('record' + i, cue, {})));
        expect(await repo.list()).toHaveLength(CACHE_POLICY.maxRecords);
    });
    it('rejects malformed cue and word timing', () => {
        expect(validCues([{ ...cue[0], endMs: -1 }])).toBe(false);
        expect(validCues([{ ...cue[0], words: [{ text: 'x', startMs: 5, endMs: 1 }] }])).toBe(false);
        expect(validCues([{ ...cue[0], startMs: 500 }, cue[0]])).toBe(false);
    });
    it('does not evict good data for an individually oversized record', async () => {
        const repo = createCacheRepository(fakeBrowser.storage.local);
        await repo.put('good', cue, {});
        await expect(repo.put('large', [{ ...cue[0], text: 'x'.repeat(CACHE_POLICY.maxBytes) }], {})).rejects.toThrow('budget');
        expect((await repo.list()).map(item => item.key)).toEqual(['good']);
    });
    it('never reads legacy page caches or removes unrelated extension keys', async () => {
        await fakeBrowser.storage.local.set({ other: 'keep', cueflora_cache_old: cue });
        const repo = createCacheRepository(fakeBrowser.storage.local);
        expect(await repo.list()).toEqual([]);
        await repo.put('new', cue, {}); await repo.remove('new');
        expect((await fakeBrowser.storage.local.get('other')).other).toBe('keep');
    });
    it('propagates persistence errors without poisoning the write queue', async () => {
        let fail = true;
        const repo = createCacheRepository({ get: async () => ({}), remove: async () => {}, set: async () => { if (fail) throw Error('quota'); } });
        await expect(repo.put('a', cue, {})).rejects.toThrow('quota');
        fail = false;
        await expect(repo.put('a', cue, {})).resolves.toHaveProperty('key', 'a');
    });
    it('purges only corrupt owned records when writing new data', async () => {
        await fakeBrowser.storage.local.set({ [CACHE_PREFIX + 'broken']: { version: 1 }, private: 'keep' });
        const repo = createCacheRepository(fakeBrowser.storage.local);
        await repo.put('valid', cue, {});
        const stored = await fakeBrowser.storage.local.get(null);
        expect(stored).not.toHaveProperty(CACHE_PREFIX + 'broken');
        expect(stored.private).toBe('keep');
    });
    it('touches LRU on reads and evicts the actual least-recently-used record', async () => {
        const now = vi.spyOn(Date, 'now');
        try {
            const repo = createCacheRepository(fakeBrowser.storage.local);
            for (let i = 0; i < 20; i++) { now.mockReturnValue(i); await repo.put(String(i), cue, {}); }
            now.mockReturnValue(30); await repo.get('0');
            now.mockReturnValue(31); await repo.put('new', cue, {});
            const keys = (await repo.list()).map(record => record.key);
            expect(keys).toContain('0'); expect(keys).not.toContain('1');
        } finally { now.mockRestore(); }
    });
    it('reads valid data even when updating its access timestamp fails', async () => {
        const stored = createCacheRepository(fakeBrowser.storage.local);
        await stored.put('valid', cue, {});
        const repo = createCacheRepository({ get: keys => fakeBrowser.storage.local.get(keys),
            set: async () => { throw Error('quota'); }, remove: keys => fakeBrowser.storage.local.remove(keys) });
        expect((await repo.get('valid'))?.cues).toEqual(cue);
    });
    it('retains the prior atomic record when a replacement write fails', async () => {
        const store = fakeBrowser.storage.local;
        await createCacheRepository(store).put('same', cue, { model: 'old' });
        const repo = createCacheRepository({ get: keys => store.get(keys), remove: keys => store.remove(keys),
            set: async () => { throw Error('interrupted'); } });
        await expect(repo.put('same', [{ ...cue[0], text: 'new' }], { model: 'new' })).rejects.toThrow('interrupted');
        expect((await repo.list())[0]).toMatchObject({ cues: cue, metadata: { model: 'old' } });
    });
    it('reconstructs valid inventory after interruption between eviction and insertion', async () => {
        const store = fakeBrowser.storage.local;
        const baseline = createCacheRepository(store);
        for (let i = 0; i < 20; i++) await baseline.put(String(i), cue, {});
        const failing = createCacheRepository({ get: keys => store.get(keys), remove: keys => store.remove(keys),
            set: async () => { throw Error('interrupted'); } });
        await expect(failing.put('new', cue, {})).rejects.toThrow('interrupted');
        const restarted = createCacheRepository(store);
        const survivors = await restarted.list();
        expect(survivors).toHaveLength(19);
        expect(survivors.every(record => record.cues[0].text === cue[0].text)).toBe(true);
        await restarted.put('new', cue, {});
        expect(await restarted.list()).toHaveLength(20);
    });
});
