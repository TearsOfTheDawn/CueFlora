import type { AppState } from './types';
import { createIdleWorkflowState } from './workflowState';

export const state: AppState = {
    activeInterval: null,
    initInterval: null,
    transcriptionCues: [],
    translationCues: [],
    availableTracks: [],
    generatedTracks: {},
    subtitleCache: {},
    isPanelOpen: false,
    showTranscription: true,
    showTranslation: true,
    highlightCurrentWord: true,
    workflow: createIdleWorkflowState(),
    overlayOffsetBottom: 60,
    subtitleBgOpacity: 75,
    _cleanupUI: null,
};
