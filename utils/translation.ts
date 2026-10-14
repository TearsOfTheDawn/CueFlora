import type {
    Cue,
    TranslationBatch,
    TranslationQualityFlag,
    TranslationQualityReason,
} from './types';

export interface TranslationAttemptContext {
    call: number;
    maxCalls: number;
    groupStart: number;
    cueCount: number;
    depth: number;
    kind: 'initial' | 'retry' | 'split' | 'repair';
    label: string;
    recoveryReason?: string;
}

export interface TranslationRecoveryStats {
    calls: number;
    retries: number;
    repairCalls: number;
    salvagedPositions: number;
    qualityRepairs: number;
    unresolvedQualityFlags: number;
}

export class TranslationRequestError extends Error {
    constructor(message: string, public readonly recoverable: boolean) {
        super(message);
        this.name = 'TranslationRequestError';
    }
}

interface RecoverTranslationBatchOptions {
    cues: Cue[];
    startIndex: number;
    maxCalls: number;
    maxSplitDepth: number;
    enableEnglishAdequacyCheck?: boolean;
    request: (
        cues: Cue[],
        groupStart: number,
        attempt: TranslationAttemptContext
    ) => Promise<unknown[]>;
    onAttempt?: (attempt: TranslationAttemptContext) => void;
    onResolved?: (absoluteIndex: number, cue: Cue) => void;
    onSalvage?: (count: number) => void;
    onQualityFlag?: (flag: TranslationQualityFlag) => void;
    onQualityRepair?: (count: number) => void;
    onUnresolvedQuality?: (flag: TranslationQualityFlag) => void;
    onStatus?: (message: string, stats: TranslationRecoveryStats) => void;
}

export const buildContextualBatches = (
    cues: Cue[],
    batchCueTarget: number,
    maxSourceChars: number
): TranslationBatch[] => {
    const batches: TranslationBatch[] = [];
    let startIndex = 0;
    while (startIndex < cues.length) {
        let endIndex = startIndex;
        let sourceChars = 0;
        while (endIndex < cues.length && endIndex - startIndex < batchCueTarget) {
            const nextChars = Math.max(1, (cues[endIndex].text || '').length);
            if (endIndex > startIndex && sourceChars + nextChars > maxSourceChars) break;
            sourceChars += nextChars;
            endIndex++;
        }
        if (endIndex === startIndex) {
            endIndex++;
            sourceChars = Math.max(1, (cues[startIndex].text || '').length);
        }
        batches.push({
            cues: cues.slice(startIndex, endIndex),
            startIndex,
            endIndex,
            sourceChars,
        });
        startIndex = endIndex;
    }
    return batches;
};

export const buildTranslationContextLines = (
    allCues: Cue[],
    translatedByIndex: Array<Cue | undefined>,
    groupStart: number,
    groupEnd: number,
    previousCount: number,
    forwardCount: number
): string[] => {
    const sanitize = (text: string): string => (text || '').replace(/\s+/g, ' ').trim();
    const lines: string[] = [];
    const previousStart = Math.max(0, groupStart - previousCount);
    if (previousStart < groupStart) {
        lines.push('PREVIOUS CONTEXT (reference only; do not output these lines):');
        for (let index = previousStart; index < groupStart; index++) {
            lines.push(`[S${index + 1}] ${sanitize(allCues[index].text)}`);
            const translated = translatedByIndex[index];
            if (translated) lines.push(`[T${index + 1}] ${sanitize(translated.text)}`);
        }
    }

    const forwardEnd = Math.min(allCues.length, groupEnd + forwardCount);
    if (groupEnd < forwardEnd) {
        if (lines.length) lines.push('');
        lines.push('FOLLOWING SOURCE CONTEXT (reference only; do not output these lines):');
        for (let index = groupEnd; index < forwardEnd; index++) {
            lines.push(`[S${index + 1}] ${sanitize(allCues[index].text)}`);
        }
    }
    return lines;
};

export type TranslationValidationReason =
    | 'not-string'
    | 'empty'
    | 'truncated-marker'
    | TranslationQualityReason;

export type TranslationValidationResult =
    | { valid: true; text: string }
    | {
        valid: false;
        reason: TranslationValidationReason;
        qualityFlag?: Omit<TranslationQualityFlag, 'cueIndex'>;
    };

type InvalidTranslationValidationResult = Extract<
TranslationValidationResult,
{ valid: false }
>;

const informationCharacterCount = (text: string): number =>
    Array.from(text).filter((character) => /[\p{L}\p{N}]/u.test(character)).length;

const lexicalWordCount = (text: string): number =>
    text.match(/[\p{L}\p{N}]+(?:['’\-][\p{L}\p{N}]+)*/gu)?.length || 0;

type RequestLabelKind = 'bracket' | 'parenthesis' | 'period' | 'colon' | 'hyphen';

const requestLabelKind = (text: string, requestId: number): RequestLabelKind | null => {
    const labels: Array<[RequestLabelKind, RegExp]> = [
        ['bracket', new RegExp(`^\\s*\\[\\s*${requestId}\\s*\\]`)],
        ['parenthesis', new RegExp(`^\\s*\\(\\s*${requestId}\\s*\\)`) ],
        ['period', new RegExp(`^\\s*${requestId}\\s*\\.(?:\\s+|$)`) ],
        ['colon', new RegExp(`^\\s*${requestId}\\s*:(?:\\s+|$)`) ],
        ['hyphen', new RegExp(`^\\s*${requestId}\\s*-(?:\\s+|$)`) ],
    ];
    return labels.find(([, pattern]) => pattern.test(text))?.[0] || null;
};

export const validateTranslationOutput = (
    sourceCue: Cue,
    value: unknown,
    requestId: number,
    enableEnglishAdequacyCheck = false
): TranslationValidationResult => {
    if (typeof value !== 'string') return { valid: false, reason: 'not-string' };
    const text = value.trim();
    if (!text) return { valid: false, reason: 'empty' };
    if (/^\[?\s*truncated(?:\s+output)?\s*\]?$/i.test(text)) {
        return { valid: false, reason: 'truncated-marker' };
    }

    const contextLabelLeak = /^\s*\[\s*[ST]\d+\s*\]/i.test(text);
    const outputRequestLabel = requestLabelKind(text, requestId);
    const requestLabelLeak = outputRequestLabel !== null &&
        requestLabelKind(sourceCue.text || '', requestId) !== outputRequestLabel;
    if (contextLabelLeak || requestLabelLeak) {
        return {
            valid: false,
            reason: 'label-leak',
            qualityFlag: { reason: 'label-leak' },
        };
    }

    if (enableEnglishAdequacyCheck) {
        const sourceInformationCharacters = informationCharacterCount(sourceCue.text || '');
        const sourceClauseBoundaries = (sourceCue.text || '').match(/[，。！？；：,.!?;:]/gu)?.length || 0;
        const targetInformationCharacters = informationCharacterCount(text);
        const targetWords = lexicalWordCount(text);
        const substantialSource = sourceInformationCharacters >= 24 ||
            (sourceInformationCharacters >= 18 && sourceClauseBoundaries >= 2);
        if (substantialSource && targetWords <= 3 && targetInformationCharacters <= 18) {
            return {
                valid: false,
                reason: 'extreme-under-translation',
                qualityFlag: {
                    reason: 'extreme-under-translation',
                    sourceInformationCharacters,
                    targetInformationCharacters,
                    targetWords,
                },
            };
        }
    }

    return { valid: true, text };
};

export const isUsableTranslation = (value: unknown): value is string =>
    validateTranslationOutput({ startMs: 0, endMs: 1, text: '' }, value, -1).valid;

export const recoverTranslationBatch = async (
    options: RecoverTranslationBatchOptions
): Promise<{ cues: Cue[]; stats: TranslationRecoveryStats }> => {
    const stats: TranslationRecoveryStats = {
        calls: 0,
        retries: 0,
        repairCalls: 0,
        salvagedPositions: 0,
        qualityRepairs: 0,
        unresolvedQualityFlags: 0,
    };
    const qualityRepairAttempted = new Set<number>();

    const describeSplit = (count: number): string => {
        const left = Math.ceil(count / 2);
        return `${count} -> ${left}+${count - left}`;
    };

    const emitStatus = (message: string): void => options.onStatus?.(message, { ...stats });

    const translateGroup = async (
        cues: Cue[],
        groupStart: number,
        label: string,
        depth = 0,
        sameGroupAttempt = 0,
        kind: TranslationAttemptContext['kind'] = 'initial',
        recoveryReason?: string
    ): Promise<Cue[]> => {
        if (stats.calls >= options.maxCalls) {
            throw new Error(
                `Exceeded the recovery limit of ${options.maxCalls} model calls; ` +
                `last group ${label} had ${cues.length} cues.`
            );
        }

        stats.calls++;
        if (kind !== 'initial') stats.retries++;
        if (kind === 'repair') stats.repairCalls++;
        const attempt: TranslationAttemptContext = {
            call: stats.calls,
            maxCalls: options.maxCalls,
            groupStart,
            cueCount: cues.length,
            depth,
            kind,
            label,
            recoveryReason,
        };
        options.onAttempt?.(attempt);

        const retryOrSplit = async (reason: string): Promise<Cue[]> => {
            const allowSameSizeRetry = sameGroupAttempt < 1 && (depth === 0 || cues.length <= 3);
            if (allowSameSizeRetry && stats.calls < options.maxCalls) {
                emitStatus(`malformed output; retrying ${cues.length} cue${cues.length === 1 ? '' : 's'}`);
                return translateGroup(
                    cues,
                    groupStart,
                    label,
                    depth,
                    sameGroupAttempt + 1,
                    kind === 'repair' ? 'repair' : 'retry',
                    reason
                );
            }

            if (
                cues.length > 1 &&
                depth < options.maxSplitDepth &&
                stats.calls < options.maxCalls
            ) {
                const midpoint = Math.ceil(cues.length / 2);
                emitStatus(`malformed output persists; splitting ${describeSplit(cues.length)}`);
                const left = await translateGroup(
                    cues.slice(0, midpoint),
                    groupStart,
                    `${label}.1`,
                    depth + 1,
                    0,
                    'split',
                    reason
                );
                const right = await translateGroup(
                    cues.slice(midpoint),
                    groupStart + midpoint,
                    `${label}.2`,
                    depth + 1,
                    0,
                    'split',
                    reason
                );
                return left.concat(right);
            }

            throw new Error(
                `Could not recover ${label} after ${stats.calls}/${options.maxCalls} model calls: ${reason}`
            );
        };

        let translations: unknown[];
        try {
            translations = await options.request(cues, groupStart, attempt);
        } catch (error) {
            if (error instanceof TranslationRequestError && error.recoverable) {
                return retryOrSplit(error.message);
            }
            throw error;
        }

        if (translations.length > cues.length) {
            return retryOrSplit(
                `${translations.length}/${cues.length} translations returned; positional alignment is ambiguous`
            );
        }

        const resolved: Array<Cue | undefined> = new Array(cues.length);
        const invalidIndexes: number[] = [];
        const issues = new Map<number, InvalidTranslationValidationResult>();
        const commonLength = Math.min(cues.length, translations.length);
        for (let i = 0; i < commonLength; i++) {
            const absoluteIndex = groupStart + i;
            const output = translations[i];
            const validation = validateTranslationOutput(
                cues[i],
                output,
                i,
                options.enableEnglishAdequacyCheck
            );
            if (!validation.valid) {
                const qualityFlag = validation.qualityFlag
                    ? { cueIndex: absoluteIndex, ...validation.qualityFlag }
                    : null;
                if (qualityFlag) options.onQualityFlag?.(qualityFlag);
                if (
                    validation.reason === 'extreme-under-translation' &&
                    qualityRepairAttempted.has(absoluteIndex) &&
                    typeof output === 'string'
                ) {
                    stats.unresolvedQualityFlags++;
                    if (qualityFlag) options.onUnresolvedQuality?.(qualityFlag);
                    const cue = {
                        startMs: cues[i].startMs,
                        endMs: cues[i].endMs,
                        text: output.trim(),
                    };
                    resolved[i] = cue;
                    options.onResolved?.(absoluteIndex, cue);
                    continue;
                }
                invalidIndexes.push(i);
                issues.set(i, validation);
                continue;
            }
            const cue = {
                startMs: cues[i].startMs,
                endMs: cues[i].endMs,
                text: validation.text,
            };
            resolved[i] = cue;
            options.onResolved?.(absoluteIndex, cue);
        }
        for (let i = commonLength; i < cues.length; i++) {
            invalidIndexes.push(i);
            issues.set(i, { valid: false, reason: 'empty' });
        }

        if (invalidIndexes.length === 0 && translations.length === cues.length) {
            return resolved as Cue[];
        }

        const issueSummary = invalidIndexes
            .map((index) => `${index}:${issues.get(index)?.reason || 'missing'}`)
            .join(',');
        const reason = `${translations.length}/${cues.length} translations returned; issues=${issueSummary}`;
        const hasNewQualityRepair = invalidIndexes.some((index) =>
            issues.get(index)?.reason === 'extreme-under-translation' &&
            !qualityRepairAttempted.has(groupStart + index)
        );
        if (invalidIndexes.length === cues.length && !hasNewQualityRepair) {
            return retryOrSplit(reason);
        }

        const salvaged = cues.length - invalidIndexes.length;
        stats.salvagedPositions += salvaged;
        if (salvaged > 0) options.onSalvage?.(salvaged);
        emitStatus(salvaged > 0
            ? `salvaged ${salvaged}/${cues.length} cues; repairing ${invalidIndexes.length}`
            : `repairing ${invalidIndexes.length} suspicious cue${invalidIndexes.length === 1 ? '' : 's'}`
        );

        const badRuns: Array<{ start: number; end: number }> = [];
        for (const index of invalidIndexes) {
            const previous = badRuns[badRuns.length - 1];
            if (previous && index === previous.end + 1) previous.end = index;
            else badRuns.push({ start: index, end: index });
        }

        for (let i = 0; i < badRuns.length; i++) {
            const run = badRuns[i];
            const repairStart = groupStart + run.start;
            let qualityRepairs = 0;
            const recoveryReasons = new Set<string>();
            for (let index = run.start; index <= run.end; index++) {
                const issue = issues.get(index);
                if (issue) recoveryReasons.add(issue.reason);
                const absoluteIndex = groupStart + index;
                if (
                    issue?.reason === 'extreme-under-translation' &&
                    !qualityRepairAttempted.has(absoluteIndex)
                ) {
                    qualityRepairAttempted.add(absoluteIndex);
                    qualityRepairs++;
                }
            }
            if (qualityRepairs > 0) {
                stats.qualityRepairs += qualityRepairs;
                options.onQualityRepair?.(qualityRepairs);
            }
            const repaired = await translateGroup(
                cues.slice(run.start, run.end + 1),
                repairStart,
                `${label}.repair-${i + 1}`,
                Math.min(depth + 1, options.maxSplitDepth),
                0,
                'repair',
                Array.from(recoveryReasons).join(', ')
            );
            for (let j = 0; j < repaired.length; j++) resolved[run.start + j] = repaired[j];
        }

        const unresolved = resolved
            .map((cue, index) => cue ? -1 : index)
            .filter((index) => index >= 0);
        if (unresolved.length > 0) {
            throw new Error(`Repair finished with unresolved indexes=${unresolved.join(',')}.`);
        }
        return resolved as Cue[];
    };

    const cues = await translateGroup(options.cues, options.startIndex, 'batch');
    return { cues, stats };
};
