import { validatePreference } from './preferences';
import { settingsRequest } from './settingsRequest';
const values = new Map<string,string>();
const writes = new Map<string,number>();
const pending = new Map<string,number>();
let initialized = false;
let refreshSequence = 0;
/** Read through the background; newer local edits and stale navigation win. */
export async function refreshPreferences(canApply:()=>boolean = ()=>true, keys?:readonly string[]): Promise<string[]> {
    const sequence = ++refreshSequence, versions = new Map(writes), inFlight = new Set(pending.keys());
    const response = await settingsRequest({type:'PREFERENCES_INIT',legacy:{}});
    if (!response || response.error) throw Error('Could not load extension preferences.');
    if (sequence !== refreshSequence || !canApply()) return [];
    const changed:string[] = [];
    const selected = keys || [...new Set([...values.keys(),...Object.keys(response)])];
    for (const key of selected) {
        if (inFlight.has(key) || pending.has(key) || writes.get(key) !== versions.get(key)) continue;
        const valid = validatePreference(key,response[key]);
        if (values.get(key) === (valid ?? undefined)) continue;
        if (valid === null) values.delete(key); else values.set(key,valid);
        changed.push(key);
    }
    return changed;
}
export async function initializePreferences(): Promise<void> {
    if (initialized) return;
    const legacy: Record<string,string> = {};
    // Fresh independent product: do not import any page-origin preferences.
    const response = await browser.runtime.sendMessage({ type: 'PREFERENCES_INIT', legacy });
    if (!response || response.error) throw Error('Could not load extension preferences.');
    values.clear();
    for (const [key,value] of Object.entries(response)) { const valid = validatePreference(key,value); if (valid !== null) values.set(key,valid); }
    initialized = true;
}
export async function savePreference(key: string, value: string): Promise<void> {
    const sequence = (writes.get(key) || 0) + 1;
    writes.set(key, sequence);
    pending.set(key,sequence);
    try {
        const response = await settingsRequest({ type: 'PREFERENCES_SAVE', key, value });
        if (response?.error || typeof response?.value !== 'string') throw Error('Could not save preference.');
        if (writes.get(key) === sequence) values.set(key,response.value);
    } finally { if (pending.get(key) === sequence) pending.delete(key); }
}
/** Synchronous view for existing rendering callers; persistence is background-owned. */
export const preferences: Pick<Storage,'getItem'|'setItem'> = {
    getItem: key => values.get(key) ?? null,
    setItem: (key,value) => {
        const valid = validatePreference(key,value);
        if (valid === null) throw Error('Invalid preference.');
        values.set(key,valid);
        void savePreference(key,valid).catch(() => document.dispatchEvent(new Event('cueflora-preference-warning')));
    },
};
