import { sameRunContext, validRunContext, type RunContext } from './runIdentity';

/** Browser URL and a fresh, document-targeted challenge must agree. sender.url is only provenance. */
export async function verifyRunDocument(
    tabId: number, documentId: string | undefined, jobId: string, context: RunContext,
    tabs: Pick<typeof browser.tabs, 'get' | 'sendMessage'> = browser.tabs,
): Promise<void> {
    if (!validRunContext(context)) throw Error('Invalid Run document context. Reload YouTube and start again.');
    const requestId = crypto.randomUUID();
    let timeout: ReturnType<typeof setTimeout> | undefined;
    try {
        await Promise.race([ (async () => {
            const before = await tabs.get(tabId);
            const currentVideo = (url?: string) => {
                if (!url) return null;
                try { const parsed = new URL(url); return parsed.origin === 'https://www.youtube.com' && parsed.pathname === '/watch' ? parsed.searchParams.get('v') : null; }
                catch { return null; }
            };
            if (currentVideo(before.url) !== context.videoId) throw Error('Run video changed. Start a new Run.');
            const reply = await tabs.sendMessage(tabId, { type: 'RUN_DOCUMENT_CHECK', requestId, jobId, context },
                documentId ? { documentId } : { frameId: 0 });
            if (reply?.requestId !== requestId || reply.current !== true || !validRunContext(reply.context) ||
                !sameRunContext(reply.context, context)) throw Error('Run document changed. Reload YouTube and start again.');
            if (currentVideo((await tabs.get(tabId)).url) !== context.videoId) throw Error('Run video changed. Start a new Run.');
        })(), new Promise<never>((_, reject) => { timeout = setTimeout(() => reject(Error('YouTube did not confirm the current Run. Reload the tab and try again.')), 2500); }) ]);
    } finally { if (timeout) clearTimeout(timeout); }
}
