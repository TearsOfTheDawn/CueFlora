import { state } from './state';
import type {
    WorkflowRunDiagnostics,
    WorkflowStage,
    WorkflowStageState,
    WorkflowState,
    WorkflowStatus,
} from './types';
import { createIdleWorkflowState } from './workflowState';

export const WORKFLOW_CHANGED_EVENT = 'CUEFLORA_WORKFLOW_CHANGED';

const terminalStatuses: WorkflowStatus[] = ['complete', 'error', 'cancelled'];
const allowedTransitions: Partial<Record<WorkflowStatus, WorkflowStatus[]>> = {
    transcribing: ['transcription_complete', 'error', 'cancelled'],
    transcription_complete: ['translating', 'complete', 'error', 'cancelled'],
    translating: ['complete', 'error', 'cancelled'],
};

const notify = (): void => {
    if (typeof document !== 'undefined') {
        document.dispatchEvent(new CustomEvent(WORKFLOW_CHANGED_EVENT));
    }
};

const clampPercent = (value: number | null | undefined): number | null => {
    if (value == null || !Number.isFinite(value)) return null;
    return Math.max(0, Math.min(100, Math.round(value)));
};

const makeJobId = (videoId: string): string => {
    const suffix = typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    return `${videoId}:${suffix}`;
};

export const beginWorkflow = (
    videoId: string,
    translationRequested: boolean,
    jobId = makeJobId(videoId)
): string => {
    const now = Date.now();
    state.workflow = {
        status: 'transcribing',
        jobId,
        videoId,
        error: null,
        transcription: { status: 'waiting', message: 'starting…', percent: 0 },
        translation: translationRequested
            ? { status: 'waiting', message: 'waiting for transcription…', percent: 0 }
            : { status: 'skipped', message: 'not requested', percent: 100 },
        diagnostics: {
            jobId,
            videoId,
            startedAt: now,
            transcription: { status: 'pending' },
            translation: {
                status: translationRequested ? 'pending' : 'skipped',
                totalCues: 0,
                logicalBatches: 0,
                physicalRequests: 0,
                retries: 0,
                repairCalls: 0,
                salvagedPositions: 0,
                truncatedResponses: 0,
                qualityRepairs: 0,
                qualityFlags: [],
                unresolvedQualityFlags: [],
                recoveryIssues: [],
            },
        },
    };
    notify();
    return jobId;
};

export const isCurrentJob = (jobId: string, videoId?: string | null): boolean =>
    state.workflow.jobId === jobId &&
    (!videoId || state.workflow.videoId === videoId) &&
    !terminalStatuses.includes(state.workflow.status);

export const isWorkflowBusy = (): boolean =>
    ['transcribing', 'transcription_complete', 'translating'].includes(state.workflow.status);

export const updateWorkflowStage = (
    jobId: string,
    stage: WorkflowStage,
    patch: Partial<WorkflowStageState>
): boolean => {
    if (!isCurrentJob(jobId)) return false;
    state.workflow = {
        ...state.workflow,
        [stage]: {
            ...state.workflow[stage],
            ...patch,
            percent: patch.percent === undefined
                ? state.workflow[stage].percent
                : clampPercent(patch.percent),
        },
    };
    notify();
    return true;
};

export const transitionWorkflow = (jobId: string, status: WorkflowStatus): boolean => {
    if (!isCurrentJob(jobId)) return false;
    if (!(allowedTransitions[state.workflow.status] || []).includes(status)) return false;
    state.workflow = { ...state.workflow, status };
    notify();
    return true;
};

export const updateWorkflowDiagnostics = (
    jobId: string,
    update: (diagnostics: WorkflowRunDiagnostics) => void
): boolean => {
    if (!isCurrentJob(jobId) || !state.workflow.diagnostics) return false;
    update(state.workflow.diagnostics);
    notify();
    return true;
};

const finishDiagnostics = (workflow: WorkflowState): void => {
    if (!workflow.diagnostics) return;
    const finishedAt = Date.now();
    workflow.diagnostics.finishedAt = finishedAt;
    workflow.diagnostics.durationMs = finishedAt - workflow.diagnostics.startedAt;
    console.info('[cueflora diagnostics]', JSON.stringify(workflow.diagnostics));
};

export const completeWorkflow = (jobId: string): boolean => {
    if (!isCurrentJob(jobId)) return false;
    const workflow = { ...state.workflow, status: 'complete' as const, error: null };
    finishDiagnostics(workflow);
    state.workflow = workflow;
    notify();
    return true;
};

export const failWorkflow = (jobId: string, error: string): boolean => {
    if (!isCurrentJob(jobId)) return false;
    const workflow = { ...state.workflow, status: 'error' as const, error };
    finishDiagnostics(workflow);
    state.workflow = workflow;
    notify();
    return true;
};

export const cancelWorkflow = (reason = 'cancelled'): void => {
    if (state.workflow.jobId && isWorkflowBusy()) {
        const workflow = { ...state.workflow, status: 'cancelled' as const, error: reason };
        finishDiagnostics(workflow);
        state.workflow = workflow;
        notify();
    }
};

export const resetWorkflow = (): void => {
    state.workflow = createIdleWorkflowState();
    notify();
};
