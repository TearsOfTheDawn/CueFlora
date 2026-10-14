import type { CacheRecord } from './cacheRepository';
import type { Cue } from './types';
export async function readCache(key: string): Promise<CacheRecord | null> {
    try {
        const result = await browser.runtime.sendMessage({ type: 'CACHE_GET', key });
        return result?.version === 1 ? result : null;
    } catch { return null; }
}
export async function listCaches(): Promise<CacheRecord[]> {
    try { const result = await browser.runtime.sendMessage({ type: 'CACHE_LIST' }); return Array.isArray(result) ? result : []; }
    catch { return []; }
}
export async function writeCache(key: string, cues: Cue[], metadata: Record<string, unknown> = {}): Promise<void> {
    try {
        const result = await browser.runtime.sendMessage({ type: 'CACHE_PUT', key, cues, metadata });
        if (result?.error || result?.version !== 1) throw Error('Subtitle cache could not be saved.');
    } catch {
        console.warn('[cueflora] Subtitle cache could not be saved; current subtitles remain usable.');
        document.dispatchEvent(new CustomEvent('cueflora-cache-warning'));
    }
}
export async function removeCache(key: string): Promise<void> {
    await browser.runtime.sendMessage({ type: 'CACHE_REMOVE', key }).catch(() => {});
}
