import { afterEach, expect, it, vi } from 'vitest';
import bridge from '../bridge.content';
import { getTracks } from '../youtube.content/render';

afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); document.body.innerHTML = ''; });

it('exchanges string envelopes through the production bridge', async () => {
    const listeners = vi.spyOn(document, 'addEventListener');
    const player = document.createElement('div');
    player.id = 'movie_player';
    Object.assign(player, { getAudioTrack: () => ({ captionTracks: [{ languageCode: 'zh' }] }) });
    document.body.append(player);
    const dispatch = vi.spyOn(document, 'dispatchEvent');
    bridge.main({} as never);
    try {
        await expect(getTracks()).resolves.toEqual([{ languageCode: 'zh' }]);
        const envelopes = dispatch.mock.calls.map(([event]) => event as CustomEvent)
            .filter(event => event.type.startsWith('CUEFLORA_'));
        expect(envelopes).toHaveLength(2);
        expect(envelopes.every(event => typeof event.detail === 'string')).toBe(true);
    } finally {
        for (const [name, handler] of listeners.mock.calls) document.removeEventListener(name, handler);
    }
});

it('ignores malformed and unrelated replies then accepts the correlated reply', async () => {
    const dispatch = vi.spyOn(document, 'dispatchEvent');
    const pending = getTracks();
    const request = dispatch.mock.calls[0][0] as CustomEvent;
    const { requestId } = JSON.parse(request.detail);
    for (const detail of ['{', JSON.stringify({ requestId: 'wrong', tracks: [] }), { requestId, tracks: [] }]) {
        document.dispatchEvent(new CustomEvent('CUEFLORA_TRACKS_DATA', { detail }));
    }
    document.dispatchEvent(new CustomEvent('CUEFLORA_TRACKS_DATA', {
        detail: JSON.stringify({ requestId, tracks: [{ languageCode: 'en' }, { languageCode: 5 }] }),
    }));
    await expect(pending).resolves.toEqual([{ languageCode: 'en' }]);
});

it('times out missing replies and removes the response listener', async () => {
    vi.useFakeTimers();
    const remove = vi.spyOn(document, 'removeEventListener');
    const pending = getTracks(50);
    await vi.advanceTimersByTimeAsync(50);
    await expect(pending).resolves.toEqual([]);
    expect(remove).toHaveBeenCalledWith('CUEFLORA_TRACKS_DATA', expect.any(Function));
});
