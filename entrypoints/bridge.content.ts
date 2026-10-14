import type { CaptionTrack } from '../utils/types';

// Minimal interface for YouTube's internal player API (untyped)
interface MoviePlayer extends HTMLElement {
    getAudioTrack?: () => { captionTracks?: CaptionTrack[] } | null;
}

export default defineContentScript({
    matches: ['https://www.youtube.com/*'],
    world: 'MAIN',
    runAt: 'document_idle',

    main() {
        const TAG = '[cueflora bridge]';

        document.addEventListener('CUEFLORA_GET_TRACKS', (event) => {
            // Strings cross the page/extension boundary without sharing objects.
            const detail = (event as CustomEvent).detail;
            if (typeof detail !== 'string') return;
            let requestId: unknown;
            try { requestId = JSON.parse(detail)?.requestId; } catch { return; }
            if (typeof requestId !== 'string' || !/^\d{1,20}$/.test(requestId)) return;
            const player = document.querySelector('#movie_player') as MoviePlayer | null;
            let tracks: CaptionTrack[] = [];
            if (player && player.getAudioTrack) {
                try {
                    const audioTrack = player.getAudioTrack();
                    if (audioTrack && audioTrack.captionTracks) {
                        tracks = audioTrack.captionTracks;
                    }
                } catch (e) {
                    console.error(TAG, 'Error getting tracks:', e);
                }
            }
            console.log(TAG, 'Returning', tracks.length, 'caption tracks');
            document.dispatchEvent(new CustomEvent('CUEFLORA_TRACKS_DATA', { detail: JSON.stringify({ requestId, tracks }) }));
        });

        console.log(TAG, 'Loaded in MAIN world.');
    },
});
