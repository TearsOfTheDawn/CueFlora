import { CACHE_POLICY } from './cachePolicy';
import type { Cue } from './types';
export interface CacheRecord {
    version: 1;
    key: string;
    cues: Cue[];
    metadata: Record<string, unknown>;
    accessed: number;
    checksum: string;
}
export const CACHE_PREFIX = 'cueflora_owned_cache_v1:';
export async function sha256(value: unknown): Promise<string> {
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(value)));
    return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
}
export function validCues(value: unknown): value is Cue[] {
    if (!Array.isArray(value) || value.length > 100000) return false;
    let previous = -1;
    return value.every(cue => {
        if (!cue || typeof cue.text !== 'string' || !Number.isFinite(cue.startMs) || !Number.isFinite(cue.endMs) || cue.startMs < 0 || cue.endMs < cue.startMs || cue.startMs < previous) return false;
        previous = cue.startMs;
        let wordStart = -1;
        return cue.words === undefined || (Array.isArray(cue.words) && cue.words.every((word: any) => {
            if (!word || typeof word.text !== 'string' || (word.prefix !== undefined && typeof word.prefix !== 'string') || !Number.isFinite(word.startMs) || !Number.isFinite(word.endMs) || word.startMs < wordStart || word.startMs < 0 || word.endMs < word.startMs) return false;
            wordStart = word.startMs; return true;
        }));
    });
}
export function createCacheRepository(storage: {
    get: (keys: null) => Promise<Record<string, unknown>>;
    set: (items: Record<string, unknown>) => Promise<void>;
    remove: (keys: string[]) => Promise<void>;
}) {
    let queue: Promise<unknown> = Promise.resolve();
    const serial = <T>(work: () => Promise<T>): Promise<T> => { const next = queue.then(work); queue = next.catch(() => {}); return next; };
    const size = (value: unknown) => new TextEncoder().encode(JSON.stringify(value)).length;
    const list = async (purgeInvalid = false) => {
        const items = await storage.get(null);
        const records: CacheRecord[] = [];
        const invalid: string[] = [];
        for (const [key, value] of Object.entries(items)) {
            if (!key.startsWith(CACHE_PREFIX)) continue;
            const record = value as CacheRecord;
            if (record?.version !== 1 || key !== CACHE_PREFIX + record.key || !validCues(record.cues) ||
                !record.metadata || typeof record.metadata !== 'object' || Array.isArray(record.metadata) || !Number.isFinite(record.accessed) ||
                size({ [key]: record }) > CACHE_POLICY.maxBytes || record.checksum !== await sha256(record.cues)) {
                invalid.push(key); continue;
            }
            records.push(record);
        }
        // Invalid owned cache records otherwise occupy quota indefinitely.
        // Never touch provider/preferences or legacy page-origin data.
        if (purgeInvalid && invalid.length) await storage.remove(invalid);
        return records;
    };
    return {
        list: () => serial(list),
        get: (key: string) => serial(async () => {
            const record = (await list()).find(item => item.key === key);
            if (!record) return null;
            record.accessed = Date.now();
            try { await storage.set({ [CACHE_PREFIX + key]: record }); } catch { /* A failed LRU touch must not prevent reading. */ }
            return record;
        }),
        remove: (key: string) => serial(() => storage.remove([CACHE_PREFIX + key])),
        put: (key: string, cues: Cue[], metadata: Record<string, unknown>) => serial(async () => {
            if (typeof key !== 'string' || key.length > 256 || !validCues(cues) || !metadata || typeof metadata !== 'object' || Array.isArray(metadata)) throw Error('Invalid cache record.');
            const record: CacheRecord = { version: 1, key, cues, metadata, accessed: Date.now(), checksum: await sha256(cues) };
            const bytes = size({ [CACHE_PREFIX + key]: record });
            if (bytes > CACHE_POLICY.maxBytes) throw Error('Subtitle record exceeds cache budget; subtitles remain usable.');
            const records = (await list(true)).filter(item => item.key !== key).sort((a,b) => a.accessed - b.accessed || a.key.localeCompare(b.key));
            let total = bytes + records.reduce((sum,item) => sum + size({ [CACHE_PREFIX + item.key]: item }), 0);
            const evicted: string[] = [];
            while (records.length >= CACHE_POLICY.maxRecords || total > CACHE_POLICY.maxBytes) {
                const victim = records.shift()!; total -= size({ [CACHE_PREFIX + victim.key]: victim }); evicted.push(CACHE_PREFIX + victim.key);
            }
            if (evicted.length) await storage.remove(evicted);
            await storage.set({ [CACHE_PREFIX + key]: record });
            return record;
        }),
    };
}
