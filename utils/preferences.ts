import { validateAppearance } from './appearance';
export const PREFERENCES_KEY = 'cueflora_owned_preferences_v1';
export function validatePreference(key: string, value: unknown): string | null {
    if (typeof value !== 'string') return null;
    if (key === 'cueflora_appearance_v1') {
        try { const raw = JSON.parse(value); return raw?.version === 1 ? JSON.stringify(validateAppearance(raw)) : null; } catch { return null; }
    }
    if (/^cueflora_(show_transcription|show_translation|highlight_current_word|ruby_zh)$/.test(key)) return ['0','1'].includes(value) ? value : null;
    if (/^cueflora_(transcription_lang|translation_lang)$/.test(key)) return /^(?:(?:transcription|translation):)?[a-zA-Z0-9-]{1,40}$/.test(value) ? value : null;
    const ranges: Record<string, [number,number]> = {
        cueflora_sub_bg_opacity: [0,100], cueflora_overlay_bottom: [0,10000],
        cueflora_translation_batch_size: [10,60], cueflora_translation_max_parallel: [1,1],
        cueflora_transcription_max_parallel: [1,16], cueflora_transcription_mb_per_req: [1,25],
    };
    const range = ranges[key];
    return range && value.trim() && Number.isFinite(Number(value)) ? String(Math.max(range[0], Math.min(range[1], Number(value)))) : null;
}
export function createPreferencesService(storage: {
    get: (key: string) => Promise<Record<string, unknown>>;
    set: (items: Record<string, unknown>) => Promise<void>;
}) {
    let queue: Promise<unknown> = Promise.resolve();
    const transact = <T>(work: () => Promise<T>): Promise<T> => { const result = queue.then(work); queue = result.catch(() => {}); return result; };
    const read = async () => {
        const raw = (await storage.get(PREFERENCES_KEY))[PREFERENCES_KEY];
        if (!raw || typeof raw !== 'object' || !('migrated' in raw) || raw.migrated !== true) return;
        const values: Record<string, string> = {};
        if ('values' in raw && raw.values && typeof raw.values === 'object' && !Array.isArray(raw.values)) {
            for (const [key, value] of Object.entries(raw.values)) {
                const valid = validatePreference(key, value);
                if (valid !== null) values[key] = valid;
            }
        }
        // Never reimport page data after a completed migration, including when
        // individual persisted fields are corrupted or unexpected.
        return { migrated: true, values };
    };
    const saveMany = (input: Record<string,string>) => transact(async () => {
        const updates: Record<string,string> = {};
        for (const [key,value] of Object.entries(input)) {
            const valid = validatePreference(key,value);
            if (valid === null) throw Error('Invalid preference.');
            updates[key] = valid;
        }
        const previous = await read();
        if (!previous?.migrated) throw Error('Preferences have not been initialized.');
        await storage.set({ [PREFERENCES_KEY]: { migrated: true, values: { ...previous.values, ...updates } } });
        return updates;
    });
    return {
        readValues: async () => (await read())?.values || {},
        initialize: (legacy: Record<string,unknown>) => transact(async () => {
            const existing = await read();
            if (existing?.migrated) return existing.values;
            const values: Record<string,string> = {};
            for (const [key,value] of Object.entries(legacy || {})) { const valid = validatePreference(key,value); if (valid !== null) values[key] = valid; }
            await storage.set({ [PREFERENCES_KEY]: { migrated: true, values } });
            return values;
        }),
        saveMany,
        save: async (key: string, value: string) => (await saveMany({ [key]:value }))[key],
    };
}
