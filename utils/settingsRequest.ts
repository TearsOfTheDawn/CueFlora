/** Settings deadlines never retry writes. A timed-out write must be reconciled. */
export class SettingsTimeout extends Error {
    constructor() { super('Settings request timed out. Reload saved state before trying again.'); }
}
export const accountRequest=<T=any>(message:import('./types').AccountMessage)=>settingsRequest<T>(message);
export const updateRequest=<T=any>(message:import('./types').UpdateMessage)=>settingsRequest<T>(message);
export async function settingsRequest<T = any>(message: Record<string, unknown>): Promise<T> {
    let timer: ReturnType<typeof setTimeout> | undefined;
    try {
        return await Promise.race([
            browser.runtime.sendMessage(message) as Promise<T>,
            new Promise<never>((_, reject) => { timer = setTimeout(() => reject(new SettingsTimeout()), 15000); }),
        ]);
    } finally { if (timer !== undefined) clearTimeout(timer); }
}
