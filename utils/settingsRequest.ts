/** Settings deadlines never retry writes. A timed-out write must be reconciled. */
export class SettingsTimeout extends Error {
    constructor() { super('Settings request timed out. Reload saved state before trying again.'); }
}
export async function settingsRequest<T = any>(message: Record<string, unknown>): Promise<T> {
    let timer: ReturnType<typeof setTimeout> | undefined;
    try {
        return await Promise.race([
            browser.runtime.sendMessage(message) as Promise<T>,
            new Promise<never>((_, reject) => { timer = setTimeout(() => reject(new SettingsTimeout()), 15000); }),
        ]);
    } finally { if (timer !== undefined) clearTimeout(timer); }
}
