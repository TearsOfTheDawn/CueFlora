import { beforeEach, describe, expect, it } from 'vitest';
import { state } from '../state';
import {
    beginWorkflow,
    completeWorkflow,
    failWorkflow,
    isCurrentJob,
    resetWorkflow,
    transitionWorkflow,
    updateWorkflowStage,
} from '../workflow';

describe('workflow state authority', () => {
    beforeEach(() => resetWorkflow());

    it('follows the successful transcription then translation sequence', () => {
        const jobId = beginWorkflow('video-1', true, 'job-1');
        expect(state.workflow.status).toBe('transcribing');
        expect(state.workflow.diagnostics?.translation).toMatchObject({
            physicalRequests: 0,
            truncatedResponses: 0,
        });
        updateWorkflowStage(jobId, 'transcription', { status: 'done', percent: 100 });
        expect(transitionWorkflow(jobId, 'transcription_complete')).toBe(true);
        expect(transitionWorkflow(jobId, 'translating')).toBe(true);
        updateWorkflowStage(jobId, 'translation', { status: 'done', percent: 100 });
        expect(completeWorkflow(jobId)).toBe(true);
        expect(state.workflow.status).toBe('complete');
    });

    it('rejects invalid transitions', () => {
        const jobId = beginWorkflow('video-1', true, 'job-1');
        expect(transitionWorkflow(jobId, 'translating')).toBe(false);
        expect(state.workflow.status).toBe('transcribing');
    });

    it('records errors as terminal state', () => {
        const jobId = beginWorkflow('video-1', false, 'job-1');
        expect(failWorkflow(jobId, 'boom')).toBe(true);
        expect(state.workflow.status).toBe('error');
        expect(state.workflow.error).toBe('boom');
        expect(isCurrentJob(jobId)).toBe(false);
    });

    it('a new Run invalidates updates from the previous job', () => {
        const oldJob = beginWorkflow('video-1', true, 'job-old');
        const newJob = beginWorkflow('video-1', true, 'job-new');
        expect(isCurrentJob(oldJob)).toBe(false);
        expect(isCurrentJob(newJob)).toBe(true);
        expect(updateWorkflowStage(oldJob, 'translation', { status: 'done' })).toBe(false);
        expect(state.workflow.translation.status).toBe('waiting');
    });
});
