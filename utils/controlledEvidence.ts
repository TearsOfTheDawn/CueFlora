import type { WorkflowRunDiagnostics } from './types';

/** Evaluation-only gate. Ordinary Runs must retain valid subtitles on capture failure. */
export function assertControlledEvidence(diagnostics: WorkflowRunDiagnostics | null): void {
    if (diagnostics?.transcription.evidence?.complete !== true ||
        diagnostics.translation.evidence?.complete !== true ||
        diagnostics.translation.evidence.stages.presentation !== 'complete') {
        throw Error('Controlled evaluation requires complete transcription, translation and presentation evidence.');
    }
}
