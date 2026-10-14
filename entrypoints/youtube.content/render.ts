import { preferences as preferenceStorage } from '../../utils/preferenceClient';
import { state } from '../../utils/state';
import { navigationGuard } from '../../utils/navigation';
import { bindRunProviders, releaseRunProviders, getProviderSummary } from '../../utils/providerClient';
import { log, getVideoId } from '../../utils/log';
import { STORAGE_PREFIX, resolveTranscriptionLang } from '../../utils/constants';
import { createRubyNodes } from '../../utils/ruby';
import { getEffectiveAppearance, styleAppearance, appearanceTop } from '../../utils/appearance';
import {
    beginWorkflow,
    completeWorkflow,
    failWorkflow,
    isCurrentJob,
    transitionWorkflow,
    updateWorkflowDiagnostics,
    updateWorkflowStage,
} from '../../utils/workflow';
import {
    fetchSubtitles,
    invalidateCachedTranscription,
    invalidateCachedTranslation,
    isCachedTranslationCurrent,
    restoreGeneratedTracksFromCache,
    startTranscription,
    translateSubtitles,
} from './api';
import type { CaptionTrack, Cue, Word } from '../../utils/types';

function buildWordHighlightNodes(words: Word[], timeMs: number, language: string | null): DocumentFragment {
    const parts = document.createDocumentFragment();
    for (let index = 0; index < words.length; index++) {
        const word = words[index];
        const active = timeMs >= word.startMs && timeMs < word.endMs;
        const separator = index === 0 ? '' : (word.prefix != null ? word.prefix : ' ');
        if (separator) parts.append(document.createTextNode(separator));
        const span = document.createElement('span');
        span.className = `cueflora-word${active ? ' cueflora-word-active' : ''}`;
        span.append(createRubyNodes(word.text, language));
        parts.append(span);
    }
    return parts;
}

let trackRequestId = 0;
const isCaptionTrack = (value: unknown): value is CaptionTrack => {
    if (!value || typeof value !== 'object') return false;
    const track = value as CaptionTrack;
    return typeof track.languageCode === 'string' && track.languageCode.length <= 32 &&
        (!track.baseUrl || typeof track.baseUrl === 'string') && (!track.url || typeof track.url === 'string');
};

export function getTracks(timeoutMs = 5000): Promise<CaptionTrack[]> {
    const requestId = String(++trackRequestId);
    return new Promise((resolve) => {
        let settled = false;
        const finish = (tracks: CaptionTrack[]) => {
            if (settled) return;
            settled = true;
            clearTimeout(timer);
            document.removeEventListener('CUEFLORA_TRACKS_DATA', handler as EventListener);
            resolve(tracks);
        };
        const handler = (event: CustomEvent) => {
            try {
                if (typeof event.detail !== 'string') return;
                const payload = JSON.parse(event.detail);
                if (!payload || payload.requestId !== requestId || !Array.isArray(payload.tracks)) return;
                finish(payload.tracks.filter(isCaptionTrack));
            } catch (_) {
                // Uncorrelated page data must not terminate another request.
            }
        };
        const timer = setTimeout(() => finish([]), timeoutMs);
        document.addEventListener('CUEFLORA_TRACKS_DATA', handler as EventListener);
        document.dispatchEvent(new CustomEvent('CUEFLORA_GET_TRACKS', { detail: JSON.stringify({ requestId }) }));
    });
}

interface SubtitleLanguageInfo {
    iso: string | null;
    bcp47: string | null;
}

function getSubtitleLanguage(storageKey: string): SubtitleLanguageInfo | null {
    const value = preferenceStorage.getItem(`${STORAGE_PREFIX}${storageKey}`);
    if (!value || value === 'none') return null;
    const language = resolveTranscriptionLang(value.replace(/^translation:/, ''));
    if (!language) return null;
    return {
        iso: language.iso.code,
        bcp47: language.bcp47 || language.iso.code,
    };
}

export function applyOverlaySettings(): void {
    const overlay = document.getElementById('cueflora-overlay');
    if (!overlay) return;
    const appearance = getEffectiveAppearance();
    if (appearance) {
        const height = document.getElementById('movie_player')?.clientHeight || 720;
        styleAppearance(overlay, appearance, height);
        overlay.style.top = `${appearanceTop(height, overlay.querySelector('.cueflora-line-container')?.getBoundingClientRect().height || 0, appearance.position)}px`;
        overlay.style.bottom = 'auto';
        return;
    }
    overlay.style.setProperty('--cueflora-bg-opacity', String(state.subtitleBgOpacity / 100));
    overlay.style.top = 'auto';
    overlay.style.bottom = `${state.overlayOffsetBottom}px`;
}

const renderedContent = new WeakMap<HTMLElement, string>();

export function renderOverlay(
    transcriptionCue: Cue | undefined,
    translationCue: Cue | undefined,
    timeMs: number
): void {
    const overlay = document.getElementById('cueflora-overlay');
    if (!overlay) return;
    const transcriptionText = state.showTranscription && transcriptionCue
        ? transcriptionCue.text
        : '';
    const translationText = state.showTranslation && translationCue
        ? translationCue.text
        : '';
    const contentKey = JSON.stringify([
        transcriptionText, translationText, transcriptionCue?.words,
        getSubtitleLanguage('transcription_lang'), getSubtitleLanguage('translation_lang'),
        getEffectiveAppearance(), state.highlightCurrentWord,
        preferenceStorage.getItem(`${STORAGE_PREFIX}ruby_zh`),
    ]);
    if (renderedContent.get(overlay) === contentKey && overlay.firstChild) {
        overlay.querySelectorAll('.cueflora-word').forEach((node, index) => {
            const word = transcriptionCue?.words?.[index];
            node.classList.toggle('cueflora-word-active', !!word && timeMs >= word.startMs && timeMs < word.endMs);
        });
        return;
    }
    renderedContent.set(overlay, contentKey);
    const content = document.createDocumentFragment();
    if (transcriptionText || translationText) {
        const transcriptionLanguage = transcriptionText
            ? getSubtitleLanguage('transcription_lang')
            : null;
        const translationLanguage = translationText
            ? getSubtitleLanguage('translation_lang')
            : null;
        const transcriptionHtml = transcriptionText
            ? (getEffectiveAppearance()?.highlight ?? state.highlightCurrentWord) && transcriptionCue?.words?.length
                ? buildWordHighlightNodes(transcriptionCue.words, timeMs, transcriptionLanguage?.iso || null)
                : createRubyNodes(transcriptionText, transcriptionLanguage?.iso || null)
            : null;
        const translationHtml = translationText
            ? createRubyNodes(translationText, translationLanguage?.iso || null)
            : null;
        const container = document.createElement('div');
        container.className = 'cueflora-line-container';
        if (transcriptionHtml) {
            const line = document.createElement('div');
            line.className = 'cueflora-primary';
            if (transcriptionLanguage?.bcp47) line.lang = transcriptionLanguage.bcp47;
            line.append(transcriptionHtml);
            container.append(line);
        }
        if (translationHtml) {
            const line = document.createElement('div');
            line.className = 'cueflora-secondary';
            if (translationLanguage?.bcp47) line.lang = translationLanguage.bcp47;
            line.append(translationHtml);
            container.append(line);
        }
        content.append(container);
    }
    const existing = overlay.firstChild;
    if (!existing?.isEqualNode(content.firstChild) || overlay.childNodes.length !== content.childNodes.length) {
        overlay.replaceChildren(content);
    }
    applyOverlaySettings();
}

export function startRenderLoop(): void {
    if (state.activeInterval) clearInterval(state.activeInterval);
    const video = document.querySelector('video');
    if (!video) return;
    state.activeInterval = setInterval(() => {
        const timeMs = video.currentTime * 1000;
        renderOverlay(
            state.transcriptionCues.find((cue) => timeMs >= cue.startMs && timeMs <= cue.endMs),
            state.translationCues.find((cue) => timeMs >= cue.startMs && timeMs <= cue.endMs),
            timeMs
        );
    }, 100);
}

const selectTrack = (
    tracks: CaptionTrack[],
    code: string | null,
    allowFallback: boolean
): CaptionTrack | null => {
    const selected = code ? tracks.find((track) => track.languageCode === code) : null;
    return selected || (allowFallback ? tracks[0] || null : null);
};

let restoreSequence = 0;
/** Restore displayable cached tracks. This function never starts AI generation. */
export async function loadSubtitles(
    transcriptionCode: string | null,
    translationCode: string | null,
    injectedTranslationCues?: Cue[]
): Promise<void> {
    const sequence = ++restoreSequence;
    const navigationCurrent = navigationGuard();
    const current = () => navigationCurrent() && sequence === restoreSequence;
    log(`Restoring subtitles: source=${transcriptionCode}, target=${translationCode || 'none'}`);
    await restoreGeneratedTracksFromCache();
    if (!current()) return;
    const tracks = await getTracks();
    if (!current()) return;
    let source: Cue[];
    let translation: Cue[];

    if (transcriptionCode?.startsWith('transcription:')) {
        source = state.generatedTracks[transcriptionCode] || [];
    } else {
        source = await fetchSubtitles(
            selectTrack(tracks, transcriptionCode, true)
        );
    }
    if (!current()) return;
    if (injectedTranslationCues) {
        translation = injectedTranslationCues;
    } else if (translationCode?.startsWith('translation:')) {
        const targetLanguage = translationCode.substring('translation:'.length);
        const cached = state.generatedTracks[targetLanguage];
        if (
            cached &&
            await isCachedTranslationCurrent(
                targetLanguage,
                source,
                transcriptionCode || 'unknown'
            )
        ) {
            translation = cached;
        } else {
            if (!current()) return;
            if (cached) invalidateCachedTranslation(targetLanguage);
            translation = [];
        }
    } else if (translationCode) {
        translation = await fetchSubtitles(
            selectTrack(tracks, translationCode, false)
        );
    } else {
        translation = [];
    }
    if (!current()) return;
    state.availableTracks = tracks;
    state.transcriptionCues = source;
    state.translationCues = translation;
    startRenderLoop();
}

/** The sole owner of explicit Run sequencing and top-level workflow transitions. */
export async function runSubtitleWorkflow(
    transcriptionCode: string,
    translationCode: string | null
): Promise<void> {
    const videoId = getVideoId();
    if (!videoId) throw new Error('No YouTube video ID found.');
    const jobId = beginWorkflow(videoId, !!translationCode);
    ++restoreSequence; // An explicit Run supersedes any pending cache restoration.
    const transcriptionStartedAt = Date.now();

    try {
        const configured = getProviderSummary().next;
        if (transcriptionCode.startsWith('transcription:') && !configured.transcription.model) throw Error('Transcription is not configured. Open CueFlora settings first.');
        if (translationCode?.startsWith('translation:') && !configured.translation.model) throw Error('Translation is not configured. Open CueFlora settings first.');
        if (transcriptionCode.startsWith('transcription:') || translationCode?.startsWith('translation:')) {
            await bindRunProviders(jobId);
              if (!isCurrentJob(jobId, videoId)) return;
          }
          // A stale displayed provider revision must not erase usable subtitles.
          state.transcriptionCues = [];
          state.translationCues = [];
          if (transcriptionCode.startsWith('transcription:')) {
              invalidateCachedTranscription(transcriptionCode);
          }
          if (translationCode?.startsWith('translation:')) {
              invalidateCachedTranslation(translationCode.substring('translation:'.length));
          }
        let sourceCues: Cue[] | null;
        if (transcriptionCode.startsWith('transcription:')) {
            sourceCues = await startTranscription(
                transcriptionCode.substring('transcription:'.length),
                jobId
            );
        } else {
            updateWorkflowDiagnostics(jobId, (diagnostics) => {
                diagnostics.transcription.startedAt = transcriptionStartedAt;
                diagnostics.transcription.status = 'running';
            });
            updateWorkflowStage(jobId, 'transcription', {
                status: 'running',
                message: 'loading YouTube subtitles…',
                percent: 20,
            });
            const tracks = await getTracks();
            if (!isCurrentJob(jobId, videoId)) return;
            state.availableTracks = tracks;
            sourceCues = await fetchSubtitles(selectTrack(tracks, transcriptionCode, true));
            if (!sourceCues.length) throw new Error('Failed to load source subtitles.');
            state.transcriptionCues = sourceCues;
            updateWorkflowDiagnostics(jobId, (diagnostics) => {
                diagnostics.transcription.status = 'complete';
                diagnostics.transcription.finalCueCount = sourceCues!.length;
                diagnostics.transcription.durationMs = Date.now() - transcriptionStartedAt;
            });
            updateWorkflowStage(jobId, 'transcription', {
                status: 'done',
                message: `loaded YouTube subtitles — ${sourceCues.length} cues`,
                percent: 100,
            });
        }

        if (!sourceCues?.length || !isCurrentJob(jobId, videoId)) return;
        transitionWorkflow(jobId, 'transcription_complete');

        if (translationCode) {
            transitionWorkflow(jobId, 'translating');
            if (translationCode.startsWith('translation:')) {
                const targetLanguage = translationCode.substring('translation:'.length);
                const translated = await translateSubtitles(
                    targetLanguage,
                    transcriptionCode,
                    jobId
                );
                if (!translated || !isCurrentJob(jobId, videoId)) return;
                state.translationCues = translated;
            } else {
                const startedAt = Date.now();
                updateWorkflowDiagnostics(jobId, (diagnostics) => {
                    diagnostics.translation.startedAt = startedAt;
                    diagnostics.translation.status = 'running';
                    diagnostics.translation.totalCues = sourceCues!.length;
                });
                updateWorkflowStage(jobId, 'translation', {
                    status: 'running',
                    message: 'loading YouTube translation…',
                    percent: 20,
                });
                const tracks = state.availableTracks.length
                    ? state.availableTracks
                    : await getTracks();
                const translated = await fetchSubtitles(
                    selectTrack(tracks, translationCode, false)
                );
                if (!translated.length) throw new Error('Selected translation track is unavailable.');
                state.translationCues = translated;
                updateWorkflowDiagnostics(jobId, (diagnostics) => {
                    diagnostics.translation.status = 'complete';
                    diagnostics.translation.durationMs = Date.now() - startedAt;
                });
                updateWorkflowStage(jobId, 'translation', {
                    status: 'done',
                    message: `loaded YouTube translation — ${translated.length} cues`,
                    percent: 100,
                });
            }
        }

        if (!isCurrentJob(jobId, videoId)) return;
        startRenderLoop();
        completeWorkflow(jobId);
    } catch (error) {
        if (!isCurrentJob(jobId, videoId)) return;
        const message = error instanceof Error ? error.message : String(error);
        if (state.workflow.transcription.status !== 'done') {
            updateWorkflowDiagnostics(jobId, (diagnostics) => {
                diagnostics.transcription.status = 'error';
                diagnostics.transcription.error = message;
                diagnostics.transcription.durationMs = Date.now() - transcriptionStartedAt;
            });
            updateWorkflowStage(jobId, 'transcription', {
                status: 'error',
                message,
                percent: null,
            });
        } else if (translationCode && state.workflow.translation.status !== 'done') {
            updateWorkflowDiagnostics(jobId, (diagnostics) => {
                diagnostics.translation.status = 'error';
                diagnostics.translation.error = message;
                if (diagnostics.translation.startedAt) {
                    diagnostics.translation.durationMs = Date.now() - diagnostics.translation.startedAt;
                }
            });
            updateWorkflowStage(jobId, 'translation', {
                status: 'error',
                message,
                percent: null,
            });
        }
        failWorkflow(jobId, message);
        console.error(`[cueflora] Workflow ${jobId} failed:`, error);
    } finally {
        await releaseRunProviders(jobId);
    }
}
