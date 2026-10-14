import { expect, it, vi } from 'vitest';
import content from '../index';
import { createUI, populateDropdowns } from '../ui';
import { getTracks } from '../render';
import { state } from '../../../utils/state';

vi.mock('../ui', () => ({ createUI: vi.fn(), populateDropdowns: vi.fn() }));
vi.mock('../api', () => ({ restoreGeneratedTracksFromCache: vi.fn(async () => {}) }));
vi.mock('../render', () => ({ getTracks: vi.fn(async () => []), loadSubtitles: vi.fn(async () => {}) }));

it('serializes initialization and prevents a stale generation from rescheduling', async () => {
    vi.useFakeTimers();
    const listeners = vi.spyOn(document, 'addEventListener');
    const pending: Array<() => void> = [];
    vi.mocked(createUI).mockImplementation(() => new Promise(resolve => pending.push(resolve)));
    document.body.innerHTML = '<div class="ytp-right-controls"></div>';
    window.history.replaceState({}, '', '/watch?v=U_V6Jqg7PV4');
    try {
        content.main({} as never);
        await vi.advanceTimersByTimeAsync(1500);
        expect(createUI).toHaveBeenCalledTimes(1);
        await vi.advanceTimersByTimeAsync(9000);
        expect(createUI).toHaveBeenCalledTimes(1);

        document.dispatchEvent(new Event('yt-navigate-finish'));
        await vi.advanceTimersByTimeAsync(3000);
        expect(createUI).toHaveBeenCalledTimes(2);
        pending[0]();
        await vi.advanceTimersByTimeAsync(0);
        expect(populateDropdowns).not.toHaveBeenCalled();
        document.body.insertAdjacentHTML('beforeend', '<button id="cueflora-btn"></button><div id="cueflora-panel"></div>');
        pending[1]();
        await vi.advanceTimersByTimeAsync(0);
        expect(getTracks).toHaveBeenCalledTimes(1);
        await vi.advanceTimersByTimeAsync(1500);
        expect(createUI).toHaveBeenCalledTimes(2);
        expect(getTracks).toHaveBeenCalledTimes(2);
    } finally {
        for (const [type, listener] of listeners.mock.calls) {
            if (type === 'yt-navigate-finish') document.removeEventListener(type, listener);
        }
        vi.clearAllTimers(); state.initInterval = null;
        vi.useRealTimers(); vi.restoreAllMocks();
    }
});
