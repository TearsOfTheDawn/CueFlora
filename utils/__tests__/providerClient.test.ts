import { beforeEach, expect, it, vi } from 'vitest';

beforeEach(() => { vi.resetModules(); window.history.replaceState({}, '', '/watch?v=U_V6Jqg7PV4'); });

it('rejects summary refreshes after navigation or while the caller is busy', async () => {
    const client = await import('../providerClient');
    let resolve!:(value:unknown)=>void;
    vi.spyOn(browser.runtime,'sendMessage').mockImplementation(()=>new Promise(done=>{resolve=done;}));
    const first=client.refreshProviderSummary(); (await import('../navigation')).invalidateNavigation();
    resolve({revision:'stale'}); await first; expect(client.getProviderSummary().next.revision).toBe('');
    const busy=client.refreshProviderSummary(()=>false); resolve({revision:'busy'}); await busy;
    expect(client.getProviderSummary().next.revision).toBe('');
});

it('does not let an older binding replace a newer Run summary', async () => {
    const client = await import('../providerClient');
    const pending: Array<(value: unknown) => void> = [];
    const send = vi.spyOn(browser.runtime, 'sendMessage').mockImplementation(() => new Promise(resolve => pending.push(resolve)));
    try {
        const old = client.bindRunProviders('old'); const recent = client.bindRunProviders('recent');
        pending[1]({ revision: 'recent' }); await recent;
        pending[0]({ revision: 'old' }); await old;
        expect(client.getProviderSummary().current?.revision).toBe('recent');
    } finally { send.mockRestore(); }
});

it('does not restore a released pending binding', async () => {
    const client = await import('../providerClient');
    let resolve!: (value: unknown) => void;
    const send = vi.spyOn(browser.runtime, 'sendMessage').mockImplementationOnce(() => new Promise(done => { resolve = done; }))
        .mockResolvedValue(undefined);
    try {
        const binding = client.bindRunProviders('old');
        await client.releaseRunProviders('old');
        resolve({ revision: 'old' }); await binding;
        expect(client.getProviderSummary().current).toBeNull();
    } finally { send.mockRestore(); }
});

it('ignores a binding response after navigation', async () => {
    const client = await import('../providerClient');
    let resolve!: (value: unknown) => void;
    const send = vi.spyOn(browser.runtime, 'sendMessage').mockImplementation(() => new Promise(done => { resolve = done; }));
    try {
        const binding = client.bindRunProviders('old');
        const { invalidateNavigation } = await import('../navigation');
        invalidateNavigation(); // Same-video navigation must also invalidate the response.
        resolve({ revision: 'old' }); await binding;
        expect(client.getProviderSummary().current).toBeNull();
    } finally { send.mockRestore(); }
});

it('keeps the newest requested Next Run summary when replies arrive out of order', async () => {
    const client = await import('../providerClient');
    const pending: Array<(value: unknown) => void> = [];
    const send = vi.spyOn(browser.runtime, 'sendMessage').mockImplementation(() => new Promise(resolve => pending.push(resolve)));
    try {
        const old = client.refreshProviderSummary(); const recent = client.refreshProviderSummary();
        pending[1]({ revision: 'recent' }); await recent;
        pending[0]({ revision: 'old' }); await old;
        expect(client.getProviderSummary().next.revision).toBe('recent');
    } finally { send.mockRestore(); }
});
