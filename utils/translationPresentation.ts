import type { Cue, TranslationTimingDiagnostics } from './types';

export const TRANSLATION_MAX_CPS = 20;
export const TRANSLATION_MIN_CUE_MS = 1_500;
export const TRANSLATION_MAX_CUE_MS = 7_000;
export const TRANSLATION_CUE_GAP_MS = 1;

interface WorkingCue extends Cue {
    sourceIndexes: number[];
}

export interface TranslationPresentationResult {
    cues: Cue[];
    sourceIndexes: number[][];
    diagnostics: TranslationTimingDiagnostics;
}

const normalizeText = (text: string): string => (text || '').replace(/\s+/g, ' ').trim();

export const translationCharacterCount = (text: string): number =>
    Array.from(normalizeText(text)).length;

export const translationCps = (cue: Pick<Cue, 'startMs' | 'endMs' | 'text'>): number => {
    const durationMs = Math.max(1, cue.endMs - cue.startMs);
    return translationCharacterCount(cue.text) / (durationMs / 1000);
};

const roundCps = (value: number): number => Math.round(value * 100) / 100;

const summarize = (cues: WorkingCue[]): Pick<
TranslationTimingDiagnostics,
'fastCueCountBefore' | 'maxCpsBefore'
> => {
    const speeds = cues.map(translationCps);
    return {
        fastCueCountBefore: speeds.filter((speed) => speed > TRANSLATION_MAX_CPS).length,
        maxCpsBefore: roundCps(Math.max(0, ...speeds)),
    };
};

const extendCue = (cues: WorkingCue[], index: number): boolean => {
    const cue = cues[index];
    const next = cues[index + 1];
    const requiredDuration = Math.max(
        TRANSLATION_MIN_CUE_MS,
        Math.ceil((translationCharacterCount(cue.text) / TRANSLATION_MAX_CPS) * 1000)
    );
    const desiredEnd = cue.startMs + Math.min(requiredDuration, TRANSLATION_MAX_CUE_MS);
    const ceiling = next
        ? Math.min(cue.startMs + TRANSLATION_MAX_CUE_MS, next.startMs - TRANSLATION_CUE_GAP_MS)
        : cue.startMs + TRANSLATION_MAX_CUE_MS;
    const newEnd = Math.max(cue.endMs, Math.min(desiredEnd, ceiling));
    if (newEnd <= cue.endMs) return false;
    cue.endMs = newEnd;
    return true;
};

const mergedCue = (left: WorkingCue, right: WorkingCue): WorkingCue => ({
    startMs: Math.min(left.startMs, right.startMs),
    endMs: Math.max(left.endMs, right.endMs),
    text: normalizeText(`${left.text} ${right.text}`),
    sourceIndexes: left.sourceIndexes.concat(right.sourceIndexes),
});

interface MergeCandidate {
    startIndex: number;
    cue: WorkingCue;
    cps: number;
    direction: 'previous' | 'next';
}

const candidateFor = (
    cues: WorkingCue[],
    leftIndex: number,
    direction: MergeCandidate['direction']
): MergeCandidate | null => {
    if (leftIndex < 0 || leftIndex + 1 >= cues.length) return null;
    const left = cues[leftIndex];
    const right = cues[leftIndex + 1];
    const cue = mergedCue(left, right);
    if (cue.endMs - cue.startMs > TRANSLATION_MAX_CUE_MS) return null;
    const cps = translationCps(cue);
    if (cps >= Math.max(translationCps(left), translationCps(right))) return null;
    return { startIndex: leftIndex, cue, cps, direction };
};

export const retimeEnglishTranslationCues = (input: Cue[]): TranslationPresentationResult => {
    const normalized: WorkingCue[] = input
        .map((cue, index) => ({
            startMs: cue.startMs,
            endMs: cue.endMs,
            text: normalizeText(cue.text),
            sourceIndexes: [index],
        }))
        .sort((a, b) => a.startMs - b.startMs || a.endMs - b.endMs);
    const before = summarize(normalized);
    const cues = normalized.map((cue, index) => {
        const next = normalized[index + 1];
        const ceiling = next
            ? Math.min(
                cue.startMs + TRANSLATION_MAX_CUE_MS,
                next.startMs - TRANSLATION_CUE_GAP_MS
            )
            : cue.startMs + TRANSLATION_MAX_CUE_MS;
        return {
            ...cue,
            endMs: Math.max(cue.startMs, Math.min(cue.endMs, ceiling)),
        };
    });
    let extensions = 0;
    let merges = 0;

    for (let index = 0; index < cues.length; index++) {
        if (extendCue(cues, index)) extensions++;
    }

    let index = 0;
    while (index < cues.length) {
        if (translationCps(cues[index]) <= TRANSLATION_MAX_CPS) {
            index++;
            continue;
        }

        const candidates = [
            candidateFor(cues, index - 1, 'previous'),
            candidateFor(cues, index, 'next'),
        ].filter((candidate): candidate is MergeCandidate => !!candidate);
        if (!candidates.length) {
            index++;
            continue;
        }
        candidates.sort((a, b) => {
            const cpsDifference = a.cps - b.cps;
            if (cpsDifference !== 0) return cpsDifference;
            if (a.direction === b.direction) return 0;
            return a.direction === 'next' ? -1 : 1;
        });
        const chosen = candidates[0];
        cues.splice(chosen.startIndex, 2, chosen.cue);
        merges++;
        if (extendCue(cues, chosen.startIndex)) extensions++;
        index = Math.max(0, chosen.startIndex - 1);
    }

    const speeds = cues.map(translationCps);
    const unresolvedFastCueIndexes = cues
        .filter((cue) => translationCps(cue) > TRANSLATION_MAX_CPS)
        .flatMap((cue) => cue.sourceIndexes);
    return {
        cues: cues.map(({ sourceIndexes: _, ...cue }) => cue),
        sourceIndexes: cues.map((cue) => cue.sourceIndexes.slice()),
        diagnostics: {
            ...before,
            fastCueCountAfter: speeds.filter((speed) => speed > TRANSLATION_MAX_CPS).length,
            maxCpsAfter: roundCps(Math.max(0, ...speeds)),
            extensions,
            merges,
            unresolvedFastCueIndexes,
        },
    };
};
