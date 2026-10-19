import { getVideoId } from './log';
import { navigationGeneration } from './navigation';
import { isCurrentJob } from './workflow';

/** Document instance plus SPA generation: returning to a video is a new context. */
const documentToken = crypto.randomUUID();
export interface RunContext { videoId: string; generation: number; documentToken: string }
export function runContext(): RunContext {
    return { videoId: getVideoId() || '', generation: navigationGeneration(), documentToken };
}
export function validRunContext(value: unknown): value is RunContext {
    if (!value || typeof value !== 'object') return false;
    const context = value as RunContext;
    return typeof context.videoId === 'string' && /^[A-Za-z0-9_-]{11}$/.test(context.videoId) &&
        Number.isSafeInteger(context.generation) && context.generation >= 0 &&
        typeof context.documentToken === 'string' && /^[a-f0-9-]{36}$/.test(context.documentToken);
}
export function sameRunContext(a: RunContext, b: RunContext): boolean {
    return a.videoId === b.videoId && a.generation === b.generation && a.documentToken === b.documentToken;
}
export function documentCheck(message: Record<string, unknown>): Record<string, unknown> | undefined {
    if (message.type !== 'RUN_DOCUMENT_CHECK') return;
    const current = runContext();
    return { requestId: message.requestId, context: current,
        current: validRunContext(message.context) && sameRunContext(current, message.context) &&
            typeof message.jobId === 'string' && isCurrentJob(message.jobId, current.videoId) };
}
