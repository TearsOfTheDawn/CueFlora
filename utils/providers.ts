import { DEFAULT_TRANSCRIPTION_URL, DEFAULT_TRANSCRIPTION_MODEL, DEFAULT_TRANSLATION_URL, DEFAULT_TRANSLATION_MODEL } from './constants';
import { sha256 } from './cacheRepository';
import { validCredential, type ProtectedCredential, type CredentialStage, type KeyAction } from './credentials';
import { transportPolicy, type TransportPolicy } from './releasePolicy';

export interface Provider {
    backend?: 'api' | 'chatgpt';
    accountRef?: string;
    label: string;
    model: string;
    baseUrl: string;
    apiKey: string;
    allowRemoteHttp: boolean;
    connectionKind?: 'hosted' | 'local';
    credentialId?: string; // Opaque reference only; never a key or encrypted payload.
    keySaved?: boolean;
    migrationRequired?: boolean;
    keyAction?: KeyAction;
    reuseKey?: boolean;
}
export interface ProviderSettings {
    revision: string;
    transcription: Provider;
    translation: Provider;
    warning?: string;
}
export interface ProviderSummary {
    processing?: { transcriptionMaxParallel:number; transcriptionMbPerReq:number; translationBatchSize:number };
    cacheIdentities?: { transcription: string; translation: string };
    revision: string;
    transcription: { label: string; model: string; configured?: boolean };
    translation: { label: string; model: string; configured?: boolean };
}
export const LEGACY_PROVIDERS_KEY = 'cueflora_private_providers_v1';
export const PROVIDERS_KEY = 'cueflora_private_providers_v2';
export const providerDefaults = (): ProviderSettings => ({
    revision: '',
    transcription: { label: 'Custom provider', model: DEFAULT_TRANSCRIPTION_MODEL, baseUrl: DEFAULT_TRANSCRIPTION_URL, apiKey: '', allowRemoteHttp: false },
    translation: { label: 'Custom provider', model: DEFAULT_TRANSLATION_MODEL, baseUrl: DEFAULT_TRANSLATION_URL, apiKey: '', allowRemoteHttp: false },
});
export function validateProvider(value: unknown, policy: TransportPolicy = transportPolicy): Provider {
    if (!value || typeof value !== 'object') throw Error('Invalid provider settings.');
    const p = value as Record<string, unknown>;
    if (p.backend !== undefined && p.backend !== 'api' && p.backend !== 'chatgpt') throw Error('Unsupported translation backend.');
    if (p.backend === 'chatgpt') {
        if (typeof p.accountRef !== 'string' || !/^[a-f0-9-]{36}$/.test(p.accountRef) ||
            typeof p.model !== 'string' || !/^[\w.:/\-]{1,200}$/.test(p.model) || p.apiKey || p.baseUrl || p.credentialId)
            throw Error('Choose a connected ChatGPT account and an eligible model.');
        return {backend:'chatgpt',accountRef:p.accountRef,label:'Using ChatGPT plan',model:p.model,baseUrl:'',apiKey:'',allowRemoteHttp:false};
    }
    for (const key of ['label', 'model', 'baseUrl', 'apiKey']) {
        if (typeof p[key] !== 'string' || (p[key] as string).length > (key === 'apiKey' ? 8192 : 2048)) throw Error('Invalid provider field.');
    }
    if (!p.baseUrl && !p.model && !p.apiKey) return { label: 'Not configured', model: '', baseUrl: '', apiKey: '', allowRemoteHttp: false };
    const url = new URL(p.baseUrl as string);
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) throw Error('Use an HTTP(S) base URL without credentials, query or fragment.');
    const local = ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname);
    const authority = (p.baseUrl as string).match(/^https?:\/\/([^/?#]+)/i)?.[1]?.toLowerCase();
    const literalHost = authority?.startsWith('[') ? authority.slice(0, authority.indexOf(']') + 1) : authority?.split(':')[0];
    if (local && !['localhost', '127.0.0.1', '[::1]'].includes(literalHost || '')) throw Error('Use an explicit loopback address.');
    if (url.protocol === 'http:' && !local && policy === 'https-remote') throw Error('Remote services require HTTPS in store candidates.');
    if (url.protocol === 'http:' && !local && p.allowRemoteHttp !== true) throw Error('Acknowledge unencrypted non-loopback HTTP first.');
    if (!(p.model as string).trim()) throw Error('Model name is required.');
    return { label: (p.label as string).trim() || 'Custom provider', model: (p.model as string).trim(),
        baseUrl: url.href.replace(/\/+$/, ''), apiKey: p.apiKey as string, allowRemoteHttp: p.allowRemoteHttp === true,
        ...(p.connectionKind === 'hosted' || p.connectionKind === 'local' ? { connectionKind: p.connectionKind } : {}) };
}
export const providerConfigured = (provider: Provider) => provider.backend === 'chatgpt' ? !!provider.accountRef && !!provider.model : !!provider.baseUrl && !!provider.model;
export function providerSummary(settings: ProviderSettings): ProviderSummary {
    const summary = (provider: Provider) => ({ label: providerConfigured(provider) ? provider.label : 'Not configured',
        model: provider.model, configured: providerConfigured(provider) });
    return { revision: settings.revision,
        transcription: summary(settings.transcription), translation: summary(settings.translation) };
}

/** Opaque cache identity; raw endpoints and keys never enter player messages. */
export async function providerSummaryWithIdentity(settings: ProviderSettings): Promise<ProviderSummary> {
    const identity = (provider: Provider) => providerConfigured(provider) ? sha256(provider.backend === 'chatgpt'
        ? { backend:'chatgpt', account:provider.accountRef, model:provider.model }
        : { endpoint: provider.baseUrl.replace(/\/+$/, ''), model: provider.model }) : Promise.resolve('');
    const [transcription, translation] = await Promise.all([identity(settings.transcription), identity(settings.translation)]);
    return { ...providerSummary(settings), cacheIdentities: { transcription, translation } };
}

interface ProviderRecord {
    schema: 2; revision: string; transcription: Omit<Provider, 'apiKey'>; translation: Omit<Provider, 'apiKey'>;
    vault: Record<string, ProtectedCredential>;
}
type Protector = (message: {stage: CredentialStage; baseUrl: string; apiKey?: string; credential?: ProtectedCredential; previousBaseUrl?: string}) => Promise<ProtectedCredential>;
/** Background-only. Run snapshots have references, never plaintext/ciphertext. */
export function createProviderService(storage: {
    get: (keys: string | string[]) => Promise<Record<string, unknown>>;
    set: (items: Record<string, unknown>) => Promise<void>;
    remove?: (key: string) => Promise<void>;
}, options: { protect?: Protector; retain?: () => Promise<string[]>; policy?: TransportPolicy; validateAccount?:(ref:string,model:string)=>Promise<void> } = {}) {
    let queue: Promise<unknown> = Promise.resolve();
    const serial = <T>(work: () => Promise<T>): Promise<T> => {
        const result = queue.then(work); queue = result.catch(() => {}); return result;
    };
    const raw = () => storage.get([PROVIDERS_KEY, LEGACY_PROVIDERS_KEY]);
    const decode = (data: Record<string, unknown>): { settings: ProviderSettings; vault: Record<string, ProtectedCredential> } => {
        const record = data[PROVIDERS_KEY] as ProviderRecord | undefined;
        if (record) {
            if (record.schema !== 2 || typeof record.revision !== 'string' || !record.revision || !record.vault || typeof record.vault !== 'object' || Array.isArray(record.vault) || Object.keys(record.vault).length > 1000 ||
                !Object.entries(record.vault).every(([id, value]) => /^[a-f0-9-]{36}$/.test(id) && validCredential(value))) throw Error('Invalid protected provider record.');
            const settings = providerDefaults(); settings.revision = record.revision;
            for (const stage of ['transcription', 'translation'] as const) {
                const item = record[stage];
                if (stage === 'transcription' && item?.backend === 'chatgpt') throw Error('ChatGPT plan does not support transcription.');
                if (!item || 'apiKey' in item || (item.credentialId !== undefined && !record.vault[item.credentialId])) throw Error('Invalid protected provider reference.');
                settings[stage] = { ...validateProvider({...item, apiKey:''}, 'preview'),
                    ...(item.credentialId ? {credentialId:item.credentialId} : {}), keySaved:!!item.credentialId };
            }
            return {settings, vault:record.vault};
        }
        const legacy = data[LEGACY_PROVIDERS_KEY] as ProviderSettings | undefined;
        if (!legacy) return {settings:providerDefaults(), vault:{}};
        if (typeof legacy.revision !== 'string' || !legacy.revision) throw Error('Invalid stored provider revision.');
        const settings = providerDefaults(); settings.revision = legacy.revision;
        for (const stage of ['transcription','translation'] as const) {
            const item = validateProvider(legacy[stage], 'preview');
            settings[stage] = {...item, apiKey:'', keySaved:!!item.apiKey, migrationRequired:!!item.apiKey};
        }
        return {settings, vault:{}};
    };
    const read = async () => decode(await raw()).settings;
    const view = (settings: ProviderSettings): ProviderSettings => {
        const result = {...settings};
        for (const stage of ['transcription','translation'] as const) {
            const {credentialId: _reference, ...item} = settings[stage]; result[stage] = {...item, apiKey:''};
        }
        return result;
    };
    const protect = async (input: Parameters<Protector>[0]) => {
        if (!options.protect) throw Error('Windows key protection requires the latest CueFlora helper. Upgrade/Repair before saving a key.');
        const result = await options.protect(input);
        if (!validCredential(result)) throw Error('Invalid credential-protection response; no plaintext was saved.');
        return result;
    };
    const cleanup = async (settings: ProviderSettings) => {
        if ((await raw())[LEGACY_PROVIDERS_KEY]) {
            try {
                if (!storage.remove) throw Error('Storage removal unavailable');
                await storage.remove(LEGACY_PROVIDERS_KEY);
                if ((await raw())[LEGACY_PROVIDERS_KEY]) throw Error('Cleanup not verified');
            } catch { return {...settings, warning:'Protected settings saved; legacy plaintext cleanup failed. Reload saved state to retry cleanup.'}; }
        }
        return settings;
    };
    const persist = async (settings: ProviderSettings, vault: Record<string, ProtectedCredential>) => {
        const retained = new Set([...(await options.retain?.() || []), settings.transcription.credentialId, settings.translation.credentialId]);
        const kept = Object.fromEntries(Object.entries(vault).filter(([id])=>retained.has(id)));
        const stored = (provider: Provider) => {
            const {apiKey:_key, keySaved:_saved, keyAction:_action, reuseKey:_reuse, migrationRequired:_migration, ...fields} = provider;
            return fields;
        };
        const expected = {schema:2, revision:settings.revision, transcription:stored(settings.transcription), translation:stored(settings.translation), vault:kept};
        await storage.set({[PROVIDERS_KEY]: expected});
        const reread = await raw();
        if (JSON.stringify(reread[PROVIDERS_KEY]) !== JSON.stringify(expected)) throw Error('Protected settings could not be verified. Reload saved state.');
        const verified = decode(reread);
        if (verified.settings.revision !== settings.revision || JSON.stringify(verified.vault) !== JSON.stringify(kept)) throw Error('Protected settings could not be verified. Reload saved state.');
        return view(await cleanup(verified.settings));
    };
    const prepare = async (input: Provider, stage: CredentialStage, previous: Provider, vault: Record<string, ProtectedCredential>, seal: boolean) => {
        const provider = validateProvider(input, options.policy ?? transportPolicy);
        if (provider.backend === 'chatgpt') {
            if (stage !== 'translation') throw Error('ChatGPT plan does not support transcription.');
            if(seal && (previous.backend!=='chatgpt'||previous.accountRef!==provider.accountRef||previous.model!==provider.model)) {
                if(!options.validateAccount)throw Error('ChatGPT account validation unavailable. Reconnect in settings.');
                await options.validateAccount(provider.accountRef!,provider.model);
            }
            return provider;
        }
        const action = input.keyAction ?? (input.apiKey ? 'replace' : 'keep');
        if (!['keep','replace','remove'].includes(action) || (action !== 'replace' && !!input.apiKey)) throw Error('Invalid API key action.');
        if (!providerConfigured(provider) || action === 'remove') return {...provider, apiKey:'', keySaved:false};
        if (action === 'replace') {
            if (!input.apiKey) throw Error('Enter a replacement API key.');
            if (!seal) return provider;
            const id = crypto.randomUUID(); vault[id] = await protect({stage, baseUrl:provider.baseUrl, apiKey:input.apiKey});
            return {...provider, apiKey:'', credentialId:id, keySaved:true};
        }
        if (previous.migrationRequired) throw Error('Stored key migration is incomplete. Upgrade/Repair the helper and reload settings, or explicitly Replace/Remove the key.');
        if (!previous.credentialId) return {...provider, apiKey:'', keySaved:false};
        const credential = vault[previous.credentialId];
        if (!credential) throw Error('Saved key is unavailable. Replace it in settings.');
        if (provider.baseUrl !== previous.baseUrl) {
            if (input.reuseKey !== true) throw Error('Service address changed. Replace the key or explicitly confirm reuse.');
            const replacement = await protect({stage, baseUrl:provider.baseUrl, credential, previousBaseUrl:previous.baseUrl});
            if (!seal) return {...provider, credential:replacement};
            const id = crypto.randomUUID(); vault[id] = replacement;
            return {...provider, apiKey:'', credentialId:id, keySaved:true};
        }
        return seal ? {...provider, apiKey:'', credentialId:previous.credentialId, keySaved:true} : {...provider, credential};
    };
    return {
        read,
        settings: async () => {
            const data=await raw(), settings=decode(data).settings;
            return view(data[LEGACY_PROVIDERS_KEY] ? {...settings, warning:'Stored keys or legacy cleanup need protected migration. Use Retry protected key migration with the latest Windows helper.'} : settings);
        },
        prune: () => serial(async () => {
            const data = await raw();
            const record = data[PROVIDERS_KEY] as ProviderRecord | undefined;
            if (!record) return;
            const {settings,vault} = decode(data);
            const keep = new Set([...(await options.retain?.() || []),settings.transcription.credentialId,settings.translation.credentialId]);
            const retained = Object.fromEntries(Object.entries(vault).filter(([id])=>keep.has(id)));
            if (Object.keys(retained).length !== Object.keys(vault).length) await storage.set({[PROVIDERS_KEY]:{...record,vault:retained}});
        }),
        migrate: () => serial(async () => {
            const data = await raw(), decoded = decode(data);
            if (!data[LEGACY_PROVIDERS_KEY]) return view(decoded.settings);
            if (data[PROVIDERS_KEY]) return view(await cleanup(decoded.settings));
            try {
                const settings = {...decoded.settings, revision:crypto.randomUUID()}, vault = {...decoded.vault};
                const legacy = data[LEGACY_PROVIDERS_KEY] as ProviderSettings;
                for (const stage of ['transcription','translation'] as const) {
                    const item = validateProvider(legacy[stage], 'preview');
                    settings[stage] = {...item, apiKey:'', keySaved:!!item.apiKey};
                    if (item.apiKey) {
                        const id = crypto.randomUUID(); vault[id] = await protect({stage, baseUrl:item.baseUrl, apiKey:item.apiKey});
                        settings[stage].credentialId = id;
                    }
                }
                return await persist(settings, vault);
            } catch { return {...view(await read()), warning:'Stored API keys need protected migration. The original record is retained. Upgrade/Repair CueFlora and Reload to retry; no plaintext was returned.'}; }
        }),
        check: async (input: Provider, stage: CredentialStage) => {
            const {settings, vault} = decode(await raw());
            return prepare(input, stage, settings[stage], vault, false);
        },
        materialize: async (provider: Provider) => {
            const validated = validateProvider({...provider, apiKey:''}, options.policy ?? transportPolicy);
            if (provider.apiKey || provider.migrationRequired) throw Error('Stored keys require migration in settings.');
            if (!provider.credentialId) return validated;
            const credential = decode(await raw()).vault[provider.credentialId];
            if (!credential) throw Error('Run key reference is unavailable. Start a new Run or replace the key.');
            return {...validated, credential};
        },
        save: (input: ProviderSettings) => serial(async () => {
            const {settings:previous, vault:storedVault} = decode(await raw());
            if (input.revision !== previous.revision) throw Error('Settings changed elsewhere. Reload before saving.');
            const vault = {...storedVault};
            const value = {revision:crypto.randomUUID(),
                transcription:await prepare(input.transcription, 'transcription', previous.transcription, vault, true),
                translation:await prepare(input.translation, 'translation', previous.translation, vault, true)};
            return persist(value, vault);
        }),
    };
}
