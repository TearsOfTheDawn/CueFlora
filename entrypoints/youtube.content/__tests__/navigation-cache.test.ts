import { beforeEach, describe, expect, it, vi } from 'vitest';
import { state } from '../../../utils/state';
import { invalidateNavigation } from '../../../utils/navigation';
import { fetchSubtitles, restoreGeneratedTracksFromCache } from '../api';
import { readCache, listCaches, writeCache } from '../../../utils/cacheClient';

vi.mock('../../../utils/cacheClient', () => ({ readCache: vi.fn(), listCaches: vi.fn(), writeCache: vi.fn(), removeCache: vi.fn() }));
vi.mock('../ui', () => ({ populateDropdowns: vi.fn() }));
vi.mock('../render', () => ({ startRenderLoop: vi.fn() }));
const cue = [{ text: 'old video', startMs: 0, endMs: 1000 }];
const track = { languageCode: 'en', baseUrl: 'https://www.youtube.com/api/timedtext' };

describe('production cache and fetch navigation guards', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        window.history.replaceState({}, '', '/watch?v=U_V6Jqg7PV4');
        invalidateNavigation();
        state.subtitleCache = {}; state.generatedTracks = {};
    });
    it('discards a delayed cache response after same-video navigation', async () => {
        let resolve!: (value: any) => void;
        vi.mocked(readCache).mockReturnValue(new Promise(done => { resolve = done; }));
        const pending = fetchSubtitles(track);
        invalidateNavigation();
        resolve({ cues: cue });
        expect(await pending).toEqual([]);
        expect(state.subtitleCache).toEqual({});
    });
    it('discards delayed network data without saving it for the new video', async () => {
        vi.mocked(readCache).mockResolvedValue(null);
        let resolve!: (value: any) => void;
        const network = vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(done => { resolve = done; }));
        try {
            const pending = fetchSubtitles(track);
            await vi.waitFor(() => expect(network).toHaveBeenCalledOnce());
            window.history.replaceState({}, '', '/watch?v=zEpLJgf_4u0');
            invalidateNavigation();
            resolve({ json: async () => ({ events: [{ tStartMs: 0, dDurationMs: 1000, segs: [{ utf8: 'old video' }] }] }) });
            expect(await pending).toEqual([]);
            expect(state.subtitleCache).toEqual({});
            expect(writeCache).not.toHaveBeenCalled();
        } finally { network.mockRestore(); }
    });
    it('does not restore generated records across a navigation generation', async () => {
        let resolve!: (value: any) => void;
        vi.mocked(listCaches).mockReturnValue(new Promise(done => { resolve = done; }));
        const pending = restoreGeneratedTracksFromCache();
        invalidateNavigation();
        resolve([{ key: 'cueflora_cache_U_V6Jqg7PV4_translation:en', cues: cue, metadata: {} }]);
        await pending;
        expect(state.generatedTracks).toEqual({});
    });
});
