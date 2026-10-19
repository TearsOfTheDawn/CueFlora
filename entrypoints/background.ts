import { createProviderService, providerSummaryWithIdentity, validateProvider, providerConfigured, type ProviderSettings } from '../utils/providers';
import { createCacheRepository } from '../utils/cacheRepository';
import { createPreferencesService } from '../utils/preferences';
import { createOnboardingService } from '../utils/onboarding';
import { privateDiagnostic, publicNativeResponse, validNativeResponse } from '../utils/nativeResponse';
import { validateRequest } from '../utils/requestValidation';
import type { Browser } from 'wxt/browser';
import type { ExtensionMessage, NativeTranscribeResult, NativeTranslateResult, ProgressMessage } from '../utils/types';
import { validCredential } from '../utils/credentials';
import { transportPolicy } from '../utils/releasePolicy';
import { verifyRunDocument } from '../utils/documentBinding';
import { validRunContext, type RunContext } from '../utils/runIdentity';
import { createNativeTasks } from '../utils/nativeTasks';
import { createRunLeases } from '../utils/runLeases';

interface NativeProgressResponse {
    type: 'progress';
    jobId: string;
    stage: string;
    percent?: number;
    speed?: string;
    message?: string;
    raw?: unknown;
}

type NativeResponse = NativeProgressResponse | NativeTranscribeResult | NativeTranslateResult;
class NativePreflightError extends Error {}

export default defineBackground(() => {
    console.log('[cueflora] Background service worker loaded.');

    const NATIVE_HOST = 'cueflora_host';
    const tasks = createNativeTasks(() => browser.runtime.connectNative(NATIVE_HOST));
    const leases = createRunLeases(() => browser.runtime.connectNative(NATIVE_HOST));
    const nativeCancellations=new Map<string,Set<()=>void>>();
    const cancelNative=(tab:number,job?:string)=>{for(const [key,cancellations] of nativeCancellations)
        if(key.startsWith(tab+'_')&&(job===undefined||key===tab+'_'+job))for(const cancel of [...cancellations])cancel();};
    const providers = createProviderService(browser.storage.local, {
        policy:transportPolicy,
        validateAccount:async(accountRef,model)=>{
            const result=await sendNativeMessage({type:'CHATGPT_MODELS_CACHED',requestId:crypto.randomUUID(),accountRef},null) as unknown as {error?:string;models?:{id:string}[]};
            if(result.error||!result.models?.some(item=>item.id===model))throw Error('Select an eligible model from this connected ChatGPT account.');
        },
        protect:async input => {
            try {
                const response = await sendNativeMessage({type:'CREDENTIAL_PROTECT', requestId:crypto.randomUUID(), ...input}, null) as unknown as Record<string,unknown>;
                if (!validCredential(response.credential)) throw Error('Invalid protection response');
                return response.credential;
            } catch { throw Error('Windows key protection requires the latest CueFlora helper. Upgrade/Repair or re-enter the key; no plaintext was saved.'); }
        },
        retain:async () => {
            const records = await browser.storage.session.get(null);
            return Object.entries(records).flatMap(([key,value])=> {
                const record = value as {expires?:number;settings?:ProviderSettings};
                return key.startsWith('cueflora_run_provider_') && typeof record?.expires === 'number' && record.expires > Date.now()
                    ? [record.settings?.transcription.credentialId, record.settings?.translation.credentialId].filter((id):id is string=>!!id) : [];
            });
        },
    });
    const caches = createCacheRepository(browser.storage.local);
    const preferences = createPreferencesService(browser.storage.local);
    const onboarding = createOnboardingService(browser.storage.local, preferences, providers);
    // Reconciliation is queued behind settings writes, including timed-out clients.
    let settingsQueue: Promise<unknown> = Promise.resolve();
    const serializeSettings = <T>(work: () => Promise<T>): Promise<T> => {
        const result = settingsQueue.then(work); settingsQueue = result.catch(() => {}); return result;
    };
    const session = browser.storage.session;
    browser.action?.onClicked?.addListener(() => { void browser.runtime.openOptionsPage(); });
    browser.runtime.onInstalled?.addListener(details => {
        if (details.reason === 'install') void browser.runtime.openOptionsPage();
    });
    // Some browsers do not expose this API. Call it only where supported;
    // all player storage operations already go through this background listener.
    const storageAccess = typeof browser.storage.local.setAccessLevel === 'function'
        ? browser.storage.local.setAccessLevel({ accessLevel: 'TRUSTED_CONTEXTS' })
            .then(() => true, () => false)
        : Promise.resolve(true);
    const runKey = (tab: number, job: string) => 'cueflora_run_provider_' + tab + '_' + job;
    // One queue protects both provider-vault retirement and Run-reference binding.
    const serializeBinding = serializeSettings;
    browser.tabs.onRemoved.addListener(tabId => {
        leases.releaseTab(tabId);
        cancelNative(tabId);
        void serializeBinding(async () => {
            const records = await session.get(null);
            const keys = Object.keys(records).filter(key => key.startsWith('cueflora_run_provider_' + tabId + '_'));
            if (keys.length) { await session.remove(keys); await providers.prune(); }
        }).catch(() => {});
    });
    const trustedOptions = (sender: Browser.runtime.MessageSender) =>
        sender.id === browser.runtime.id && sender.url?.split('?')[0] === browser.runtime.getURL('/options.html');
    const trustedPlayer = (sender: Browser.runtime.MessageSender) =>
        sender.id === browser.runtime.id && sender.tab?.id != null && sender.frameId === 0 &&
        !!sender.url && new URL(sender.url).origin === 'https://www.youtube.com';


    async function sendNativeMessage(msg: Record<string, unknown>, tabId: number | null, guard?: () => Promise<void>): Promise<NativeResponse> {
        if (guard) await guard();
        return new Promise((resolve, reject) => {
            let port: ReturnType<typeof browser.runtime.connectNative>;
            try { port = browser.runtime.connectNative(NATIVE_HOST); }
            catch { reject(new NativePreflightError('CueFlora helper could not be started. Install or Upgrade/Repair the helper.')); return; }
            let settled = false;
            const requiredCapability=String(msg.type).startsWith('CHATGPT_')?'chatgpt':String(msg.type).startsWith('UPDATES_')?'updates':null;
            let awaitingCapabilities = !!requiredCapability || ['whisperConfig','translateConfig','provider'].some(field=>!!(msg[field] as {credential?:unknown}|undefined)?.credential);
            const boundedRequest=['PING', 'PROVIDERS_CHECK', 'CREDENTIAL_PROTECT','CHATGPT_STATUS','CHATGPT_MODELS','CHATGPT_MODELS_CACHED','CHATGPT_DISCONNECT','CHATGPT_ACK_USAGE','UPDATES_STATUS','UPDATES_INSTALL'].includes(String(msg.type));
            let timeout = boundedRequest || awaitingCapabilities ? setTimeout(() => {
                settled = true;
                port.disconnect();
                reject(awaitingCapabilities ? new NativePreflightError('Saved keys require the latest Windows helper. Upgrade/Repair CueFlora; capability check timed out.') : Error('Native health check timed out.'));
            }, 10000) : null;
            const cancellationKey=tabId!==null&&typeof msg.jobId==='string'?tabId+'_'+msg.jobId:null;
            const cancel=()=>{if(!settled){settled=true;if(timeout)clearTimeout(timeout);port.disconnect();reject(Error('Run cancelled after navigation or release.'));}};
            if(cancellationKey){const set=nativeCancellations.get(cancellationKey)||new Set();set.add(cancel);nativeCancellations.set(cancellationKey,set);}

            port.onMessage.addListener((incoming: unknown) => {
                if (settled) return;
                if (awaitingCapabilities) {
                    if (!validNativeResponse(incoming,{type:'PING'}) ||
                        (requiredCapability
                            ? (incoming.capabilities as Record<string,unknown>|undefined)?.[requiredCapability] !== (requiredCapability==='chatgpt'?'chatgpt-translation-v1':'paired-updates-v1')
                            : (incoming.capabilities as {credentialProtection?:unknown}|undefined)?.credentialProtection !== 'windows-dpapi-v1')) {
                        settled=true; if(timeout) clearTimeout(timeout); port.disconnect();
                        reject(new NativePreflightError('Saved keys require the latest Windows helper. Upgrade/Repair CueFlora before running a keyed AI stage.'));
                        return;
                    }
                    awaitingCapabilities=false;
                    if (!boundedRequest && timeout) {clearTimeout(timeout); timeout=null;}
                    void (async () => { try { if (guard) await guard(); if (!settled) port.postMessage(msg); }
                        catch { settled=true; if(timeout)clearTimeout(timeout); port.disconnect(); reject(new NativePreflightError('Run document changed before dispatch. Start a new Run.')); } })();
                    return;
                }
                if (!validNativeResponse(incoming, msg)) {
                    settled = true;
                    if (timeout) clearTimeout(timeout);
                    port.disconnect();
                    reject(Error('Native host returned an invalid or stale response.'));
                    return;
                }
                const response = publicNativeResponse(incoming, msg) as NativeResponse;
                if ('error' in response && typeof response.error === 'string') response.error = privateDiagnostic(response.error, msg);
                // Progress updates (non-final)
                if ('type' in response && response.type === 'progress') {
                    if (response.message) response.message = privateDiagnostic(response.message, msg);
                    if (response.speed) response.speed = privateDiagnostic(response.speed, msg);
                    const detail = response.percent != null
                        ? `[${response.stage}] ${response.percent}% ${response.speed || ''}`
                        : `[${response.stage}] ${response.message || ''}`;
                    console.log('[cueflora] Native progress:', detail);

                    if (tabId) {
                        const progressMsg: ProgressMessage = {
                            type: 'NATIVE_PROGRESS',
                            jobId: response.jobId,
                            stage: response.stage,
                            percent: response.percent,
                            speed: response.speed,
                            message: response.message,
                        };
                        void (async () => { try { if (guard) await guard(); if (!settled) await browser.tabs.sendMessage(tabId, progressMsg); }
                            catch { if (!settled) { settled=true; port.disconnect(); reject(Error('Run document changed. Start a new Run.')); } } })();
                    }
                    return;
                }

                // Final result
                settled = true;
                if (timeout) clearTimeout(timeout);
                port.disconnect();
                if (guard) void guard().then(() => resolve(response), () => reject(Error('Run document changed; stale result discarded.')));
                else resolve(response);
            });

            port.onDisconnect.addListener(() => {
                if(cancellationKey){const set=nativeCancellations.get(cancellationKey);set?.delete(cancel);if(!set?.size)nativeCancellations.delete(cancellationKey);}
                if (timeout) clearTimeout(timeout);
                if (!settled) {
                    const err = browser.runtime.lastError;
                    settled = true;
                    reject(awaitingCapabilities
                        ? new NativePreflightError('Saved keys require the latest Windows helper. Upgrade/Repair CueFlora; the capability check disconnected.')
                        : new Error(privateDiagnostic(err?.message || 'Native host disconnected without response', msg)));
                }
            });

            try { port.postMessage(awaitingCapabilities ? {type:'PING'} : msg); }
            catch (error) {
                settled = true;
                if (timeout) clearTimeout(timeout);
                port.disconnect();
                reject(awaitingCapabilities
                    ? new NativePreflightError('Saved keys require the latest Windows helper. Upgrade/Repair CueFlora; the capability check could not be sent.')
                    : new Error(privateDiagnostic(error instanceof Error ? error.message : 'Native dispatch failed.', msg)));
            }
        });
    }

    browser.runtime.onMessage.addListener(async (message: ExtensionMessage | any, sender: Browser.runtime.MessageSender) => {
        if (!message || typeof message.type !== 'string') return;
        const known = ['PING','CREDENTIAL_PROTECT','PROVIDERS_MIGRATE','PROVIDERS_CHECK','ONBOARDING_GET','ONBOARDING_SAVE','ONBOARDING_FINISH','SETTINGS_RECONCILE','TRANSCRIBE_NATIVE','TRANSLATE_NATIVE','CAPTURE_PRESENTATION','PROVIDERS_GET','PROVIDERS_SAVE','PROVIDERS_SUMMARY','PROVIDERS_BIND','PROVIDERS_RELEASE','OPEN_OPTIONS','CACHE_LIST','CACHE_GET','CACHE_PUT','CACHE_REMOVE','PREFERENCES_INIT','PREFERENCES_SAVE'];
        const authentication = ['CHATGPT_LOGIN','CHATGPT_STATUS','CHATGPT_MODELS','CHATGPT_DISCONNECT','CHATGPT_ACK_USAGE','TASK_STATUS','TASK_CANCEL','UPDATES_CHECK','UPDATES_DOWNLOAD','UPDATES_INSTALL','UPDATES_STATUS','RESTART_CUEFLORA'].includes(message.type);
        if (!known.includes(message.type) && !authentication) return;
        try {
        if (!await storageAccess) throw Error('Private storage access could not be restricted. Reload the extension.');
        const options = trustedOptions(sender);
        if (!options && !trustedPlayer(sender)) throw Error('Unauthorized sender.');
        validateRequest(message);
        if(authentication) {
            if(!options)throw Error('Account operations are restricted to extension settings.');
            if(message.type==='TASK_STATUS')return tasks.status(message.taskId);
            if(message.type==='TASK_CANCEL')return tasks.cancel(message.taskId);
            if(message.type==='UPDATES_CHECK'){
                if(browser.runtime.id!=='akcolbcdfnjcahhhodnpablekjagfadf')throw Error('In-app updates require the GitHub release identity. Development previews must use their matching manual package.');
                return tasks.start('update-check');
            }
            if(message.type==='UPDATES_DOWNLOAD'||message.type==='UPDATES_INSTALL') {
                if(typeof message.selectionRef!=='string'||!/^[a-f0-9-]{36}$/.test(message.selectionRef))throw Error('Invalid update selection.');
                if(message.type==='UPDATES_DOWNLOAD')return tasks.start('update-download',undefined,message.selectionRef);
                if(message.confirmation!=='install'||leases.busy())throw Error('Confirm installation after all CueFlora Runs finish.');
                return sendNativeMessage({type:'UPDATES_INSTALL',requestId:crypto.randomUUID(),selectionRef:message.selectionRef},null);
            }
            if(message.type==='UPDATES_STATUS')return sendNativeMessage({type:'UPDATES_STATUS',requestId:crypto.randomUUID()},null);
            if(message.type==='RESTART_CUEFLORA') {
                if(leases.busy()||message.confirmation!=='restart')throw Error('Finish all Runs before restarting CueFlora.');
                const result=await sendNativeMessage({type:'UPDATES_STATUS',requestId:crypto.randomUUID()},null) as unknown as {managed?:boolean;installedVersion?:string;extensionVersion?:string};
                if(!result.managed||result.installedVersion!==message.version||result.extensionVersion!==message.version)throw Error('The matching extension/helper update has not completed. Use Setup, then Chrome Reload manually.');
                browser.runtime.reload();return {restarting:true};
            }
            if(message.accountRef!==undefined && (typeof message.accountRef!=='string'||!/^[a-f0-9-]{36}$/.test(message.accountRef)))throw Error('Invalid account reference.');
            if(message.type==='CHATGPT_LOGIN')return tasks.start('chatgpt-login',message.accountRef);
            if(message.type!=='CHATGPT_STATUS'&&!message.accountRef)throw Error('Choose an account.');
            if(message.type==='CHATGPT_MODELS')return tasks.start('chatgpt-models',message.accountRef);
            if(message.type==='CHATGPT_DISCONNECT')return tasks.start('chatgpt-disconnect',message.accountRef);
            return sendNativeMessage({type:message.type,requestId:crypto.randomUUID(),...(message.accountRef?{accountRef:message.accountRef}: {})},null);
        }
        if (message.type === 'SETTINGS_RECONCILE') {
            if (!options) throw Error('Saved settings are restricted to extension settings.');
            return await serializeSettings(async () => ({ providers:await providers.settings(),
                preferences:await preferences.initialize({}), onboarding:await onboarding.read() }));
        }
        if (message.type === 'ONBOARDING_FINISH') {
            if (!options) throw Error('Setup is restricted to extension settings.');
            return await serializeSettings(() => onboarding.finish(message));
        }
        if (message.type === 'ONBOARDING_GET' || message.type === 'ONBOARDING_SAVE') {
            if (!options) throw Error('Setup is restricted to extension settings.');
            if (message.type === 'ONBOARDING_SAVE') {
                if (!Number.isInteger(message.step) || message.step < 1 || message.step > 3 || typeof message.complete !== 'boolean') throw Error('Invalid setup state.');
                return await serializeSettings(() => onboarding.save(message.step,message.complete));
            }
            return await serializeSettings(() => onboarding.read());
        }
        if (message.type === 'PROVIDERS_CHECK') {
            if (!options) throw Error('Connection checks are restricted to extension settings.');
            const stage = message.stage ?? 'transcription';
            const provider = await serializeSettings(async () => {
                if (message.revision !== undefined && message.revision !== (await providers.read()).revision) throw Error('Settings changed elsewhere. Reload before checking.');
                return providers.check(message.provider, stage);
            });
            if (!providerConfigured(provider)) throw Error('Enter a service address and model first.');
            return await sendNativeMessage({ type: 'PROVIDERS_CHECK', requestId: message.requestId, stage, provider, transportPolicy }, null);
        }
        if (message.type === 'CREDENTIAL_PROTECT') {
            if (!options) throw Error('Key protection is restricted to extension settings.');
            const provider = validateProvider({label:'Key protection', model:'metadata-only', baseUrl:message.baseUrl, apiKey:message.apiKey, allowRemoteHttp:message.allowRemoteHttp === true});
            return await sendNativeMessage({type:'CREDENTIAL_PROTECT', requestId:message.requestId, stage:message.stage, baseUrl:provider.baseUrl, apiKey:provider.apiKey}, null);
        }
        if (message.type === 'PROVIDERS_MIGRATE') {
            if (!options) throw Error('Key migration is restricted to extension settings.');
            return await serializeSettings(()=>providers.migrate());
        }
        if (message.type === 'PREFERENCES_INIT') return await preferences.initialize(message.legacy);
        if (message.type === 'PREFERENCES_SAVE') return { value: await (options
            ? serializeSettings(() => preferences.save(message.key, message.value)) : preferences.save(message.key, message.value)) };
        if (message.type === 'CACHE_LIST') return await caches.list();
        if (message.type === 'CACHE_GET') return await caches.get(message.key);
        if (message.type === 'CACHE_PUT') return await caches.put(message.key, message.cues, message.metadata);
        if (message.type === 'CACHE_REMOVE') { if (typeof message.key !== 'string') throw Error('Invalid cache key.'); await caches.remove(message.key); return { removed: true }; }
        if (message.type === 'OPEN_OPTIONS') { await browser.runtime.openOptionsPage(); return { opened: true }; }
        if (message.type === 'PROVIDERS_GET' || message.type === 'PROVIDERS_SAVE') {
            if (!options) throw Error('Provider editing is restricted to extension settings.');
            if (message.type === 'PROVIDERS_SAVE') return await serializeSettings(() => providers.save(message.settings));
            return await serializeSettings(() => providers.migrate());
        }
        if (message.type === 'PROVIDERS_SUMMARY') return providerSummaryWithIdentity(await providers.read());
        if (message.type === 'PROVIDERS_BIND') {
            if (!trustedPlayer(sender) || typeof message.jobId !== 'string' || !/^[a-zA-Z0-9_:-]{1,100}$/.test(message.jobId)) throw Error('Invalid Run identity.');
            if (!validRunContext(message.context)) throw Error('Invalid Run document context. Reload YouTube.');
            const context = { ...message.context };
            await verifyRunDocument(sender.tab!.id!, sender.documentId, message.jobId, context);
            return await serializeBinding(async () => {
            const existing = await session.get(null);
            const expired = Object.entries(existing).filter(([key, value]) => {
                if (!key.startsWith('cueflora_run_provider_')) return false;
                const expires = value && typeof value === 'object' && 'expires' in value ? value.expires : null;
                return typeof expires !== 'number' || !Number.isFinite(expires) || expires <= Date.now();
            }).map(([key]) => key);
            if (expired.length) await session.remove(expired);
            const settings = await providers.read();
            if (settings.revision !== message.revision) throw Error('Provider settings changed. Review the summary and click Run again.');
            const key = runKey(sender.tab!.id!, message.jobId);
            if ((await session.get(key))[key]) throw Error('Run configuration is already bound.');
            const savedPreferences = await preferences.initialize({});
            const processing = { transcriptionMaxParallel:Number(savedPreferences.cueflora_transcription_max_parallel)||4,
                transcriptionMbPerReq:Number(savedPreferences.cueflora_transcription_mb_per_req)||25,
                translationBatchSize:Number(savedPreferences.cueflora_translation_batch_size)||30 };
            await verifyRunDocument(sender.tab!.id!, sender.documentId, message.jobId, context);
            await leases.acquire(key);
            try { await session.set({ [key]: { settings, processing, context, documentId: sender.documentId,
                expires: Date.now() + 24 * 60 * 60 * 1000 } }); }
            catch(error){leases.release(key);throw error;}
            return { ...await providerSummaryWithIdentity(settings), processing };
            });
        }
        if (message.type === 'PROVIDERS_RELEASE') {
            if (trustedPlayer(sender) && typeof message.jobId === 'string') await serializeBinding(async () => {
                leases.release(runKey(sender.tab!.id!,message.jobId));
                cancelNative(sender.tab!.id!,message.jobId);
                await session.remove(runKey(sender.tab!.id!, message.jobId)); await providers.prune();
            });
            return { released: true };
        }
        let runGuard: (() => Promise<void>) | undefined;
        if (['TRANSCRIBE_NATIVE','TRANSLATE_NATIVE','CAPTURE_PRESENTATION'].includes(message.type)) {
            if (!trustedPlayer(sender) || typeof message.jobId !== 'string') throw Error('Invalid Run sender.');
            const record = (await session.get(runKey(sender.tab!.id!, message.jobId)))[runKey(sender.tab!.id!, message.jobId)] as { settings: ProviderSettings; processing?: {transcriptionMaxParallel:number;transcriptionMbPerReq:number}; expires: number; context?: RunContext; documentId?: string } | undefined;
            if (!record || record.expires < Date.now()) throw Error('Run configuration expired. Start a new Run.');
            if (record.documentId !== sender.documentId || !validRunContext(record.context)) throw Error('Run belongs to a different document. Start a new Run.');
            const context = record.context, jobId = message.jobId;
            runGuard = async () => {
                if(!leases.valid(runKey(sender.tab!.id!,jobId)))throw Error('Run tracking expired. Start a new Run.');
                if (!(await session.get(runKey(sender.tab!.id!, jobId)))[runKey(sender.tab!.id!, jobId)]) throw Error('Run was released.');
                await verifyRunDocument(sender.tab!.id!, sender.documentId, jobId, context);
            };
            await runGuard();
            const settings = record.settings;
            const stage = message.type === 'TRANSCRIBE_NATIVE' ? 'transcription' : 'translation';
            if (message.type !== 'CAPTURE_PRESENTATION' && !providerConfigured(settings[stage])) throw Error(stage + ' is not configured. Open CueFlora settings.');
            if (message.type === 'TRANSCRIBE_NATIVE') {
                if (typeof message.videoId !== 'string' || !/^[a-zA-Z0-9_-]{11}$/.test(message.videoId)) throw Error('Invalid video ID.');
                if (context.videoId !== message.videoId) throw Error('Run video does not match its document.');
                const input = message.whisperConfig || {};
                message = { ...message, whisperConfig: { ...await providers.materialize(settings.transcription),
                    language: typeof input.language === 'string' ? input.language : null,
                    prompt: typeof input.prompt === 'string' ? input.prompt.slice(0,20000) : '',
                    maxParallel: record.processing?.transcriptionMaxParallel ?? 4,
                    mbPerReq: record.processing?.transcriptionMbPerReq ?? 25 } };
            }
            if (message.type === 'TRANSLATE_NATIVE') {
                if (!Array.isArray(message.cues) || !message.cues.length || message.cues.length > 60 ||
                    !message.cues.every((cue: any) => cue && typeof cue.text === 'string') ||
                    typeof message.systemPrompt !== 'string') throw Error('Invalid translation request.');
                message = { ...message, translateConfig: await providers.materialize(settings.translation) };
            }
        }
        if (message.type === 'PING') {
            return await sendNativeMessage({ type: 'PING' }, sender.tab?.id ?? null);
        }

        if (message.type === 'TRANSCRIBE_NATIVE') {
            const tabId = sender.tab?.id ?? null;
            console.log(`[cueflora] Sending to native host: videoId=${message.videoId}, tabId=${tabId}`);
            return sendNativeMessage({
                type: 'TRANSCRIBE_NATIVE',
                jobId: message.jobId,
                videoId: message.videoId,
                whisperConfig: message.whisperConfig,
                transportPolicy,
            }, tabId, runGuard)
                .then((result) => {
                    const r = result as NativeTranscribeResult;
                    console.log('[cueflora] Native host result:', r.error || (r.cues ? r.cues.length + ' cues' : 'unknown'));
                    return result;
                })
                .catch((err: Error) => {
                    console.error('[cueflora] Native messaging failed:', err);
                    return { jobId: message.jobId, error: err.message };
                });
        }

        if (message.type === 'TRANSLATE_NATIVE') {
            const tabId = sender.tab?.id ?? null;
            console.log(`[cueflora] Sending translate to native host, tabId=${tabId}`);
            return sendNativeMessage({
                type: 'TRANSLATE_NATIVE',
                jobId: message.jobId,
                cues: message.cues,
                systemPrompt: message.systemPrompt,
                translateConfig: message.translateConfig,
                transportPolicy,
                ...(message.captureId ? { captureId: message.captureId,
                    sourceIndexes: message.sourceIndexes } : {}),
            }, tabId, runGuard)
                .then((result) => {
                    const r = result as NativeTranslateResult;
                    console.log('[cueflora] Native translate result:', r.error || (r.translations ? r.translations.length + ' outputs' : 'unknown'));
                    return result;
                })
                .catch((err: Error) => {
                    console.error('[cueflora] Native translate failed:', err);
                    // The host may disconnect after sending HTTP. Count the dispatched
                    // request conservatively; never interpret missing evidence as zero.
                    return { jobId: message.jobId, error: err.message, errorKind: 'protocol', requestCount: err instanceof NativePreflightError ? 0 : 1 };
                });
        }
        if (message.type === 'CAPTURE_PRESENTATION') {
            return sendNativeMessage({ ...message }, sender.tab?.id ?? null, runGuard);
        }
        } catch (_) {
            return { jobId: typeof message.jobId === 'string' ? message.jobId : undefined,
                error: _ instanceof Error ? _.message : 'Provider request failed.', requestCount: 0 };
        }
    });
});
