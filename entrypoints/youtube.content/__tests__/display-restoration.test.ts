import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import { state } from '../../../utils/state';
import { invalidateNavigation } from '../../../utils/navigation';
import { loadSubtitles } from '../render';
import { fetchSubtitles, startTranscription, translateSubtitles } from '../api';
import type { Cue } from '../../../utils/types';

vi.mock('../api', () => ({ fetchSubtitles: vi.fn(), restoreGeneratedTracksFromCache: vi.fn(async () => {}),
    isCachedTranslationCurrent: vi.fn(async () => true), invalidateCachedTranscription: vi.fn(),
    invalidateCachedTranslation: vi.fn(), startTranscription: vi.fn(), translateSubtitles: vi.fn() }));
const cues = (text: string): Cue[] => [{ text, startMs: 0, endMs: 1000 }];
const respond = (event: Event) => document.dispatchEvent(new CustomEvent('CUEFLORA_TRACKS_DATA', {
    detail: JSON.stringify({ requestId: JSON.parse((event as CustomEvent).detail).requestId,
        tracks: [{ languageCode: 'en' }, { languageCode: 'fr' }] }),
}));

describe('production display restoration coordination', () => {
    beforeEach(() => {
        vi.clearAllMocks(); document.body.innerHTML = '';
        window.history.replaceState({}, '', '/watch?v=U_V6Jqg7PV4'); invalidateNavigation();
        state.transcriptionCues = cues('existing source'); state.translationCues = cues('existing target');
        document.addEventListener('CUEFLORA_GET_TRACKS', respond);
    });
    afterEach(() => document.removeEventListener('CUEFLORA_GET_TRACKS', respond));
    it('commits both tracks together and never invokes AI', async () => {
        let source!: (value: Cue[]) => void; let target!: (value: Cue[]) => void;
        vi.mocked(fetchSubtitles).mockReturnValueOnce(new Promise(resolve => { source = resolve; }))
            .mockReturnValueOnce(new Promise(resolve => { target = resolve; }));
        const pending = loadSubtitles('en', 'fr');
        await vi.waitFor(() => expect(fetchSubtitles).toHaveBeenCalledTimes(1));
        source(cues('new source'));
        await vi.waitFor(() => expect(fetchSubtitles).toHaveBeenCalledTimes(2));
        expect(state.transcriptionCues).toEqual(cues('existing source'));
        expect(state.translationCues).toEqual(cues('existing target'));
        target(cues('new target')); await pending;
        expect(state.transcriptionCues).toEqual(cues('new source'));
        expect(state.translationCues).toEqual(cues('new target'));
        expect(startTranscription).not.toHaveBeenCalled(); expect(translateSubtitles).not.toHaveBeenCalled();
    });
    it('does not commit a late restoration after navigation', async () => {
        let resolve!: (value: Cue[]) => void;
        vi.mocked(fetchSubtitles).mockReturnValueOnce(new Promise(done => { resolve = done; }));
        const pending = loadSubtitles('en', null);
        await vi.waitFor(() => expect(fetchSubtitles).toHaveBeenCalledOnce());
        invalidateNavigation(); state.transcriptionCues = cues('new navigation');
        resolve(cues('stale')); await pending;
        expect(state.transcriptionCues).toEqual(cues('new navigation'));
    });
    it('lets the latest restoration win even on the same video', async () => {
        let resolve!: (value: Cue[]) => void;
        vi.mocked(fetchSubtitles).mockReturnValueOnce(new Promise(done => { resolve = done; }))
            .mockResolvedValueOnce(cues('latest'));
        const first = loadSubtitles('en', null);
        await vi.waitFor(() => expect(fetchSubtitles).toHaveBeenCalledOnce());
        await loadSubtitles('fr', null);
        resolve(cues('stale')); await first;
        expect(state.transcriptionCues).toEqual(cues('latest'));
    });
});
