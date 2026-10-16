import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fakeBrowser } from 'wxt/testing/fake-browser';
import background from '../background';
import { providerDefaults } from '../../utils/providers';
import { beginWorkflow } from '../../utils/workflow';
import { messageTab } from './browserFixture';

describe('background provider trust boundary', () => {
    const health={status:'PONG',tools:{},capabilities:{credentialProtection:'windows-dpapi-v1'}};
    beforeEach(() => {
        fakeBrowser.reset(); vi.spyOn(fakeBrowser.storage.local,'setAccessLevel').mockResolvedValue(); vi.spyOn(fakeBrowser.action.onClicked, 'addListener').mockImplementation(() => {}); vi.spyOn(fakeBrowser.runtime.onInstalled, 'addListener').mockImplementation(() => {});
        vi.spyOn(fakeBrowser.runtime,'connectNative').mockImplementation(()=>{
            let listener:(value:unknown)=>void=()=>{};
            return {onMessage:{addListener:(fn:typeof listener)=>{listener=fn;}},onDisconnect:{addListener:()=>{}},disconnect:()=>{},
                postMessage:(message:any)=>queueMicrotask(()=>listener({requestId:message.requestId,credential:{schema:1,method:'windows-dpapi-v1',blob:'QUJDRA=='}}))} as any;
        });
        background.main();
    });
    const player = () => ({ id: fakeBrowser.runtime.id, url: 'https://www.youtube.com/watch?v=U_V6Jqg7PV4', frameId: 0, tab: messageTab });
    const options = () => ({ id: fakeBrowser.runtime.id, url: fakeBrowser.runtime.getURL('/options.html') });
    const call = async (message: object, sender = player()) => (await fakeBrowser.runtime.onMessage.trigger(message, sender, vi.fn()))[0];
    const configure = async () => {
        const settings = providerDefaults(); settings.transcription.apiKey = 'secret'; settings.translation.apiKey = 'secret';
        for (const stage of ['transcription','translation'] as const) { settings[stage].baseUrl = 'https://fixture.example/v1'; settings[stage].model = 'fixture'; }
        return call({ type: 'PROVIDERS_SAVE', settings }, options() as ReturnType<typeof player>);
    };
    it('rejects private reads and edits from the player', async () => {
        expect(await call({ type: 'PROVIDERS_GET' })).toHaveProperty('error');
        expect(await call({ type: 'PROVIDERS_SAVE', settings: providerDefaults() })).toHaveProperty('error');
        expect(await call({ type: 'PROVIDERS_CHECK', requestId:'check', provider:providerDefaults().translation })).toHaveProperty('error');
        expect(await call({ type:'ONBOARDING_SAVE', step:3, complete:true })).toHaveProperty('error');
    });
    it('binds fresh caption-only Runs but blocks unconfigured AI without native dispatch', async () => {
        const connect = vi.spyOn(fakeBrowser.runtime, 'connectNative');
        const summary = await call({ type:'PROVIDERS_SUMMARY' });
        expect(summary.transcription.label).toBe('Not configured');
        expect(await call({ type:'PROVIDERS_BIND', jobId:'fresh', revision:'' })).not.toHaveProperty('error');
        expect(await call({ type:'TRANSCRIBE_NATIVE', jobId:'fresh', videoId:'U_V6Jqg7PV4' })).toHaveProperty('error');
        expect(await call({ type:'TRANSLATE_NATIVE', jobId:'fresh', cues:[{text:'Hello'}], systemPrompt:'Translate' })).toHaveProperty('error');
        expect(connect).not.toHaveBeenCalled();
    });
    it('rejects stale metadata replies and never forwards arbitrary response fields', async () => {
        let listener: (value: unknown) => void = () => {};
        const postMessage = vi.fn(() => queueMicrotask(() => listener({ requestId:'old', status:'connected', models:[], reason:'ok', secret:'private' })));
        vi.spyOn(fakeBrowser.runtime, 'connectNative').mockReturnValue({ onMessage:{addListener:(fn:typeof listener)=>{listener=fn;}}, onDisconnect:{addListener:()=>{}}, postMessage, disconnect:()=>{} } as any);
        const response = await call({ type:'PROVIDERS_CHECK', requestId:'new', provider:{ ...providerDefaults().translation, baseUrl:'https://fixture.invalid/v1', model:'metadata-only' } }, options() as ReturnType<typeof player>);
        expect(response.error).toContain('stale'); expect(JSON.stringify(response)).not.toContain('private');
        expect(postMessage.mock.calls[0]).toBeTruthy();
    });
    it('persists onboarding only from settings and reports write failure', async () => {
        const sender = options() as ReturnType<typeof player>;
        expect(await call({ type:'ONBOARDING_GET' },sender)).toEqual({step:1,complete:false});
        expect(await call({ type:'ONBOARDING_SAVE',step:2,complete:false },sender)).toEqual({step:2,complete:false});
        vi.spyOn(fakeBrowser.storage.local, 'set').mockRejectedValueOnce(Error('quota'));
        expect(await call({ type:'ONBOARDING_SAVE',step:3,complete:true },sender)).toHaveProperty('error');
        expect(await call({ type:'ONBOARDING_GET' },sender)).toEqual({step:2,complete:false});
    });
    it('binds actual workflow-generated Run IDs including video underscores and separator', async () => {
        const saved = await configure();
        const jobId = beginWorkflow('U_V6Jqg7PV4', true);
        expect(jobId).toContain('U_V6Jqg7PV4:');
        expect(await call({ type: 'PROVIDERS_BIND', jobId, revision: saved.revision })).not.toHaveProperty('error');
        expect(await call({ type: 'PROVIDERS_RELEASE', jobId })).toMatchObject({ released: true });
    });
    it('binds exact revisions and never returns secrets', async () => {
        const settings = await configure();
        expect(settings.revision).toBeTruthy();
        expect(await call({ type: 'PROVIDERS_BIND', jobId: 'job', revision: 'stale' })).toHaveProperty('error');
        const bound = await call({ type: 'PROVIDERS_BIND', jobId: 'job', revision: settings.revision });
        expect(JSON.stringify(bound)).not.toContain('secret');
        expect(bound.revision).toBe(settings.revision);
        expect(await call({ type: 'PROVIDERS_BIND', jobId: 'job', revision: settings.revision })).toHaveProperty('error');
    });
    it('uses the frozen provider, not page-supplied credentials or later settings', async () => {
        const saved = await configure();
        await call({ type: 'PROVIDERS_BIND', jobId: 'job', revision: saved.revision });
        await call({ type: 'PROVIDERS_SAVE', settings: { ...saved, transcription: { ...saved.transcription, apiKey: 'new-key' } } }, options() as ReturnType<typeof player>);
        let listener: (value: unknown) => void = () => {};
        const postMessage = vi.fn((message: any) => { queueMicrotask(() => listener(message.type === 'PING' ? health : { jobId: 'job', cues: [] })); });
        vi.spyOn(fakeBrowser.runtime, 'connectNative').mockReturnValue({
            onMessage: { addListener: (fn: typeof listener) => { listener = fn; } },
            onDisconnect: { addListener: () => {} }, postMessage, disconnect: () => {},
        } as any);
        expect(await call({ type: 'TRANSCRIBE_NATIVE', jobId: 'job', videoId: 'U_V6Jqg7PV4', whisperConfig: { apiKey: 'attacker', baseUrl: 'https://evil.example' } })).not.toHaveProperty('error');
        expect(postMessage.mock.calls.find(([request])=>request.type==='TRANSCRIBE_NATIVE')![0]).toMatchObject({ whisperConfig: { apiKey: '', credential:{schema:1,method:'windows-dpapi-v1',blob:'QUJDRA=='}, baseUrl: saved.transcription.baseUrl } });
        expect(JSON.stringify(await fakeBrowser.storage.session.get(null))).not.toContain('secret');
        expect(JSON.stringify(await fakeBrowser.storage.session.get(null))).not.toContain('QUJDRA==');
        await expect(call({ type: 'TRANSCRIBE_NATIVE', jobId: 'job', videoId: 'U_V6Jqg7PV4' }, { ...player(), tab: { ...messageTab, id: 2 } })).resolves.toHaveProperty('error');
    });
    it('freezes processing controls per Run rather than trusting page values or later edits', async () => {
        const saved = await configure();
        await call({type:'PREFERENCES_INIT',legacy:{}},options() as ReturnType<typeof player>);
        await call({type:'PREFERENCES_SAVE',key:'cueflora_transcription_max_parallel',value:'2'},options() as ReturnType<typeof player>);
        const bound = await call({type:'PROVIDERS_BIND',jobId:'processing',revision:saved.revision});
        expect(bound.processing.transcriptionMaxParallel).toBe(2);
        await call({type:'PREFERENCES_SAVE',key:'cueflora_transcription_max_parallel',value:'8'},options() as ReturnType<typeof player>);
        let listener:(value:unknown)=>void=()=>{};
        const postMessage=vi.fn((message:any)=>queueMicrotask(()=>listener(message.type==='PING' ? health : {jobId:'processing',cues:[]})));
        vi.spyOn(fakeBrowser.runtime,'connectNative').mockReturnValue({onMessage:{addListener:(fn:typeof listener)=>{listener=fn;}},onDisconnect:{addListener:()=>{}},postMessage,disconnect:()=>{}} as any);
        await call({type:'TRANSCRIBE_NATIVE',jobId:'processing',videoId:'U_V6Jqg7PV4',whisperConfig:{maxParallel:16}});
        expect(postMessage.mock.calls.find(([request])=>request.type==='TRANSCRIBE_NATIVE')![0]).toMatchObject({whisperConfig:{maxParallel:2,mbPerReq:25}});
    });
    it('serializes duplicate bindings and removes snapshots when a tab closes', async () => {
        const settings = await configure();
        const responses = await Promise.all([1, 2].map(() => call({ type: 'PROVIDERS_BIND', jobId: 'same', revision: settings.revision })));
        expect(responses.filter((response: { error?: string }) => response.error)).toHaveLength(1);
        await fakeBrowser.tabs.onRemoved.trigger(1, { windowId: 1, isWindowClosing: false });
        await vi.waitFor(async () => expect(await fakeBrowser.storage.session.get(null)).toEqual({}));
    });
    it('rejects requests after same-tab document changes and prunes expired snapshots', async () => {
        await fakeBrowser.storage.session.set({ cueflora_run_provider_9_old: { expires: 0 } });
        const saved = await configure();
        await call({ type: 'PROVIDERS_BIND', jobId: 'job', revision: saved.revision });
        expect(await fakeBrowser.storage.session.get('cueflora_run_provider_9_old')).toEqual({});
        const response = await call({ type: 'TRANSCRIBE_NATIVE', jobId: 'job', videoId: 'zEpLJgf_4u0' },
            { ...player(), url: 'https://www.youtube.com/watch?v=zEpLJgf_4u0' });
        expect(response.error).toContain('different document');
    });
    it('handles malformed native responses without leaking payloads or losing request accounting', async () => {
        const saved = await configure();
        await call({ type: 'PROVIDERS_BIND', jobId: 'job', revision: saved.revision });
        let listener: (value: unknown) => void = () => {};
        vi.spyOn(fakeBrowser.runtime, 'connectNative').mockReturnValue({
            onMessage: { addListener: (fn: typeof listener) => { listener = fn; } },
            onDisconnect: { addListener: () => {} },
            postMessage: (message:any) => queueMicrotask(() => listener(message.type==='PING' ? health : null)), disconnect: () => {},
        } as any);
        expect(await call({ type: 'TRANSLATE_NATIVE', jobId: 'job', cues: [{ text: 'Hello' }], systemPrompt: 'Translate' }))
            .toMatchObject({ error: 'Native host returned an invalid or stale response.', requestCount: 1 });
    });
    it('redacts provider details from actual native error responses', async () => {
        const saved = await configure();
        await call({ type: 'PROVIDERS_BIND', jobId: 'job', revision: saved.revision });
        let listener: (value: unknown) => void = () => {};
        vi.spyOn(fakeBrowser.runtime, 'connectNative').mockReturnValue({
            onMessage: { addListener: (fn: typeof listener) => { listener = fn; } },
            onDisconnect: { addListener: () => {} },
            postMessage: (message:any) => queueMicrotask(() => listener(message.type==='PING' ? health : { jobId: 'job', error: 'secret ' + saved.translation.baseUrl, requestCount: 1 })),
            disconnect: () => {},
        } as any);
        const result = await call({ type: 'TRANSLATE_NATIVE', jobId: 'job', cues: [{ text: 'Hello' }], systemPrompt: 'Translate' });
        expect(JSON.stringify(result)).not.toContain('secret');
        expect(JSON.stringify(result)).not.toContain(saved.translation.baseUrl);
        expect(result.requestCount).toBe(1);
    });
});
