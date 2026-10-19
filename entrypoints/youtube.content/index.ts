import { preferences as preferenceStorage } from '../../utils/preferenceClient';
import './style.css';
import { state } from '../../utils/state';
import { invalidateNavigation } from '../../utils/navigation';
import { documentCheck } from '../../utils/runIdentity';
import { log } from '../../utils/log';
import { STORAGE_PREFIX } from '../../utils/constants';
import { cancelWorkflow, resetWorkflow } from '../../utils/workflow';
import { restoreGeneratedTracksFromCache } from './api';
import { createUI, populateDropdowns } from './ui';
import { getTracks, loadSubtitles } from './render';
import type { CaptionTrack } from '../../utils/types';

export default defineContentScript({
    matches: ['https://www.youtube.com/*'],
    runAt: 'document_idle',

    main() {
        browser.runtime.onMessage.addListener(message => {
            const response=documentCheck(message);
            if(response!==undefined)return Promise.resolve(response);
        });
        console.log('[cueflora] Content script loaded (Isolated World).');

        let initGeneration = 0;
        let navigationTimer: ReturnType<typeof setTimeout> | null = null;
        function init(): void {
            if (state.initInterval) clearTimeout(state.initInterval);
            const generation = ++initGeneration;

            let uiCreated = false;
            let trackAttempts = 0;
            let subtitlesInitialized = false;
            const maxTrackAttempts = 3;
            let stopped = false;

            const stopInitInterval = (): void => {
                stopped = true;
                if (state.initInterval) {
                    clearTimeout(state.initInterval);
                    state.initInterval = null;
                }
            };

            const schedule = (): void => {
            state.initInterval = setTimeout(async () => {
                if (generation !== initGeneration || stopped) return;
                try {
                const controlsReady = document.querySelector('.ytp-right-controls');

                if (!uiCreated && controlsReady) {
                    await createUI();
                    if (generation !== initGeneration) return;

                    // createUI() can legitimately return before YouTube has mounted
                    // #movie_player.  Only mark initialization complete when both
                    // halves of the CueFlora UI actually exist; otherwise the next
                    // interval tick retries instead of leaving an inert/missing S.
                    uiCreated = !!document.getElementById('cueflora-btn') &&
                                !!document.getElementById('cueflora-panel');

                    if (uiCreated) {
                        // Generated tracks are stored per-video. Restore them as soon
                        // as the UI exists instead of waiting for YouTube to expose a
                        // native caption track. This is what makes AI captions survive
                        // a normal refresh, including on videos with no YouTube captions.
                        await restoreGeneratedTracksFromCache();
                        if (generation !== initGeneration) return;
                        populateDropdowns();
                    }
                }

                if (!uiCreated || subtitlesInitialized) return;

                if (trackAttempts >= maxTrackAttempts) {
                    stopInitInterval();
                    return;
                }

                trackAttempts++;

                const tracks = await getTracks();
                if (generation !== initGeneration) return;
                const newTracks: CaptionTrack[] = tracks || [];
                state.availableTracks = newTracks;

                // Refresh generatedTracks after the video id / navigation has
                // settled. loadSubtitles() also restores the cache defensively.
                await restoreGeneratedTracksFromCache();
                if (generation !== initGeneration) return;

                const savedTranscription = preferenceStorage.getItem(STORAGE_PREFIX + 'transcription_lang');
                const savedTranslation = preferenceStorage.getItem(STORAGE_PREFIX + 'translation_lang');

                /*
                 * AI transcription is a persistent user choice, not a track that
                 * has to exist already for the current video. Keep the saved
                 * "transcription:<lang>" value even when this video has no cached
                 * transcription yet. Startup may restore an existing cache, but
                 * generation only begins when the user presses Run.
                 */
                if (savedTranscription && savedTranscription.startsWith('transcription:')) {
                    const autoTranslationCode =
                        savedTranslation && savedTranslation !== 'none'
                            ? savedTranslation
                            : null;

                    subtitlesInitialized = true;
                    stopInitInterval();
                    populateDropdowns();
                    await loadSubtitles(savedTranscription, autoTranslationCode);
                    if (generation !== initGeneration) return;
                    populateDropdowns();
                    return;
                }

                /*
                 * For ordinary YouTube caption tracks, wait briefly for YouTube to
                 * expose them. This preserves the old native-caption behaviour.
                 */
                if (newTracks.length > 0) {
                    let autoTranscriptionCode: string;

                    if (savedTranscription && !savedTranscription.startsWith('transcription:')) {
                        const trackExists = newTracks.some((tr) => tr.languageCode === savedTranscription);
                        autoTranscriptionCode = trackExists
                            ? savedTranscription
                            : newTracks[0].languageCode;
                    } else {
                        autoTranscriptionCode = newTracks[0].languageCode;
                    }

                    let autoTranslationCode: string | null = null;

                    if (savedTranslation && savedTranslation !== 'none') {
                        if (savedTranslation.startsWith('translation:')) {
                            // Keep the user's AI translation choice even when the
                            // translation is not cached yet. Startup preserves the
                            // selection but waits for the user to press Run.
                            autoTranslationCode = savedTranslation;
                        } else {
                            const translationTrackExists = newTracks.some(
                                (tr) => tr.languageCode === savedTranslation
                            );
                            autoTranslationCode = translationTrackExists
                                ? savedTranslation
                                : null;
                        }
                    }

                    preferenceStorage.setItem(
                        STORAGE_PREFIX + 'transcription_lang',
                        autoTranscriptionCode
                    );
                    preferenceStorage.setItem(
                        STORAGE_PREFIX + 'translation_lang',
                        autoTranslationCode || 'none'
                    );

                    subtitlesInitialized = true;
                    stopInitInterval();
                    populateDropdowns();
                    await loadSubtitles(autoTranscriptionCode, autoTranslationCode);
                    if (generation !== initGeneration) return;
                    populateDropdowns();
                    return;
                }

                // No native tracks were found. If there is no saved AI
                // transcription either, there is nothing to auto-load.
                if (trackAttempts >= maxTrackAttempts) {
                    populateDropdowns();
                    stopInitInterval();
                }
                } catch {
                    // A failed settings load remains retryable on the next tick.
                    // Do not expose storage/provider details to the page.
                    if (generation === initGeneration) log('Initialization unavailable; will retry.');
                } finally {
                    if (!stopped && generation === initGeneration) schedule();
                }
            }, 1500);
            };
            schedule();
        }

        document.addEventListener('yt-navigate-finish', () => {
            const oldJob=state.workflow.jobId;
            if(oldJob)void browser.runtime.sendMessage({type:'PROVIDERS_RELEASE',jobId:oldJob}).catch(()=>{});
            invalidateNavigation();
            log('Navigation detected, resetting state');
            cancelWorkflow('YouTube navigation invalidated the active job.');
            state.availableTracks = [];
            state.transcriptionCues = [];
            state.translationCues = [];
            state.generatedTracks = {};
            state.subtitleCache = {};
            state.isPanelOpen = false;

            if (state._cleanupUI) state._cleanupUI();
            if (state.activeInterval) clearInterval(state.activeInterval);
            if (state.initInterval) clearTimeout(state.initInterval);
            ++initGeneration;
            if (navigationTimer) clearTimeout(navigationTimer);

            const elOverlay = document.getElementById('cueflora-overlay');
            if (elOverlay) elOverlay.remove();

            const elBtn = document.getElementById('cueflora-btn');
            if (elBtn) elBtn.remove();

            const elPanel = document.getElementById('cueflora-panel');
            if (elPanel) elPanel.remove();

            resetWorkflow();

            // Let YouTube finish swapping the player/video id before restoring
            // this video's generated tracks or starting a new AI transcription.
            navigationTimer = setTimeout(() => {
                navigationTimer = null;
                init();
            }, 1500);
        });

        init();
    },
});
