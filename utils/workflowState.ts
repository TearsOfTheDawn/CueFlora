import type { WorkflowState } from './types';

export const createIdleWorkflowState = (): WorkflowState => ({
    status: 'idle',
    jobId: null,
    videoId: null,
    error: null,
    transcription: { status: 'idle', message: '', percent: null },
    translation: { status: 'idle', message: '', percent: null },
    diagnostics: null,
});
