import { providerDefaults, providerSummary, type ProviderSummary } from './providers';
import { navigationGuard } from './navigation';
import { settingsRequest } from './settingsRequest';
let next = providerSummary(providerDefaults());
let current: ProviderSummary | null = null;
let currentJob: string | null = null;
let bindSequence = 0;
let pendingJob: string | null = null;
let refreshSequence = 0;
export const getProviderSummary = () => ({ next, current });
export async function refreshProviderSummary(canApply:()=>boolean = ()=>true): Promise<void> {
    const sequence = ++refreshSequence;
    const sameNavigation = navigationGuard();
    const response = await settingsRequest({ type: 'PROVIDERS_SUMMARY' });
    if (sequence !== refreshSequence || !sameNavigation() || !canApply()) return;
    if (response?.error || typeof response?.revision !== 'string') throw Error(response?.error || 'Could not load provider configuration.');
    next = response;
    document.dispatchEvent(new Event('cueflora-providers-changed'));
}
export async function bindRunProviders(jobId: string): Promise<void> {
    const sequence = ++bindSequence;
    pendingJob = jobId;
    const sameNavigation = navigationGuard();
    const response = await browser.runtime.sendMessage({ type: 'PROVIDERS_BIND', jobId, revision: next.revision });
    if (sequence !== bindSequence || !sameNavigation()) return;
    pendingJob = null;
    if (response?.error) {
        await refreshProviderSummary().catch(() => {});
        throw Error(response.error);
    }
    if (typeof response?.revision !== 'string') throw Error('Provider configuration is unavailable.');
    current = response;
    currentJob = jobId;
    document.dispatchEvent(new Event('cueflora-providers-changed'));
}
export async function releaseRunProviders(jobId: string): Promise<void> {
    if (pendingJob === jobId) {
        ++bindSequence;
        pendingJob = null;
    }
    if (currentJob === jobId) {
        current = null;
        currentJob = null;
        document.dispatchEvent(new Event('cueflora-providers-changed'));
    }
    await browser.runtime.sendMessage({ type: 'PROVIDERS_RELEASE', jobId }).catch(() => {});
}
