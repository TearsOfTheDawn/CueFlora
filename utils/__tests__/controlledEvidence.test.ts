import { describe, expect, it } from 'vitest';
import { assertControlledEvidence } from '../controlledEvidence';
import type { WorkflowRunDiagnostics } from '../types';

describe('evaluation-only evidence gate', () => {
    const make = (presentation?: 'complete' | 'incomplete') => ({
        transcription: { evidence: { complete: true, stages: { normalization: 'complete' } } },
        translation: { physicalRequests: 1, evidence: { complete: true, stages: { 'translation-response': 'complete', ...(presentation ? { presentation } : {}) } } },
    } as unknown as WorkflowRunDiagnostics);
    it('requires presentation evidence even after successful translation', () => {
        for (const status of [undefined, 'incomplete'] as const) {
            const diagnostics = make(status);
            expect(() => assertControlledEvidence(diagnostics)).toThrow('Controlled evaluation');
            expect(diagnostics.translation.physicalRequests).toBe(1);
        }
    });
    it('accepts complete stages but rejects an earlier incomplete stage', () => {
        const diagnostics = make('complete');
        expect(() => assertControlledEvidence(diagnostics)).not.toThrow();
        diagnostics.transcription.evidence!.complete = false;
        expect(() => assertControlledEvidence(diagnostics)).toThrow();
    });
});
