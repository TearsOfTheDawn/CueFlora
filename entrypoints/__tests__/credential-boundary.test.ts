import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest';
import {fakeBrowser} from 'wxt/testing';
vi.mock('../../utils/releasePolicy',()=>({transportPolicy:'https-remote'}));
import background from '../background';
import {providerDefaults,LEGACY_PROVIDERS_KEY} from '../../utils/providers';

describe('store-candidate credential/transport background boundary',()=>{
    const options=()=>({id:fakeBrowser.runtime.id,url:fakeBrowser.runtime.getURL('/options.html')});
    const player=()=>({id:fakeBrowser.runtime.id,url:'https://www.youtube.com/watch?v=U_V6Jqg7PV4',frameId:0,tab:{id:1}});
    const call=async(message:object,sender=options())=>(await fakeBrowser.runtime.onMessage.trigger(message,sender))[0];
    beforeEach(()=>{fakeBrowser.reset(); vi.spyOn(fakeBrowser.action.onClicked,'addListener').mockImplementation(()=>{}); vi.spyOn(fakeBrowser.runtime.onInstalled,'addListener').mockImplementation(()=>{}); background.main();});
    afterEach(()=>vi.useRealTimers());
    const bindKeyedRun=async()=>{
        vi.spyOn(fakeBrowser.runtime,'connectNative').mockImplementation(()=>{
            let listener:(value:unknown)=>void=()=>{};
            return {onMessage:{addListener:(fn:typeof listener)=>{listener=fn;}},onDisconnect:{addListener:()=>{}},disconnect:()=>{},
                postMessage:(message:any)=>queueMicrotask(()=>listener({requestId:message.requestId,credential:{schema:1,method:'windows-dpapi-v1',blob:'QUJDRA=='}}))} as any;
        });
        const settings=providerDefaults(); settings.translation={...settings.translation,baseUrl:'https://service.invalid',model:'synthetic',apiKey:'synthetic-private'};
        const saved=await call({type:'PROVIDERS_SAVE',settings}); expect(saved).not.toHaveProperty('error');
        expect(await call({type:'PROVIDERS_BIND',jobId:'keyed',revision:saved.revision},player())).not.toHaveProperty('error');
    };
    const translate=()=>call({type:'TRANSLATE_NATIVE',jobId:'keyed',cues:[{text:'synthetic'}],systemPrompt:'Translate'},player());
    it('rejects player key protection/migration and remote HTTP before native dispatch',async()=>{
        const native=vi.spyOn(fakeBrowser.runtime,'connectNative');
        expect(await call({type:'CREDENTIAL_PROTECT',requestId:'id',stage:'translation',baseUrl:'https://service.invalid',apiKey:'synthetic'},player())).toHaveProperty('error');
        expect(await call({type:'PROVIDERS_MIGRATE'},player())).toHaveProperty('error');
        const settings=providerDefaults(); settings.translation={...settings.translation,baseUrl:'http://remote.invalid',model:'synthetic',allowRemoteHttp:true};
        expect((await call({type:'PROVIDERS_SAVE',settings})).error).toContain('HTTPS');
        expect((await call({type:'PROVIDERS_CHECK',requestId:'id',stage:'translation',provider:settings.translation})).error).toContain('HTTPS');
        expect(native).not.toHaveBeenCalled();
    });
    it('rereads uncertain state without repeating migration/protection or exposing legacy keys',async()=>{
        const settings=providerDefaults(); settings.revision='legacy'; settings.translation={...settings.translation,baseUrl:'https://service.invalid',model:'synthetic',apiKey:'synthetic-legacy-key'};
        await fakeBrowser.storage.local.set({[LEGACY_PROVIDERS_KEY]:settings}); const native=vi.spyOn(fakeBrowser.runtime,'connectNative');
        const result=await call({type:'SETTINGS_RECONCILE'});
        expect(JSON.stringify(result)).not.toContain('synthetic-legacy-key'); expect(result.providers.warning).toContain('migration'); expect(native).not.toHaveBeenCalled();
        expect((await fakeBrowser.storage.local.get(LEGACY_PROVIDERS_KEY))[LEGACY_PROVIDERS_KEY]).toEqual(settings);
    });
    it('rejects malformed/stale protection replies and unsupported helpers without plaintext persistence',async()=>{
        let listener:(value:unknown)=>void=()=>{};
        vi.spyOn(fakeBrowser.runtime,'connectNative').mockReturnValue({onMessage:{addListener:(fn:typeof listener)=>{listener=fn;}},onDisconnect:{addListener:()=>{}},disconnect:()=>{},
            postMessage:()=>queueMicrotask(()=>listener({requestId:'stale',credential:{schema:1,method:'windows-dpapi-v1',blob:'QUJDRA=='},apiKey:'synthetic'}))} as any);
        const settings=providerDefaults(); settings.translation={...settings.translation,baseUrl:'https://service.invalid',model:'synthetic',apiKey:'synthetic-private'};
        const result=await call({type:'PROVIDERS_SAVE',settings}); expect(result.error).toContain('Upgrade/Repair');
        expect(JSON.stringify(await fakeBrowser.storage.local.get(null))).not.toContain('synthetic-private');
    });
    it.each(['older helper','disconnect','timeout'] as const)('stops a keyed Run before inference on %s',async failure=>{
        await bindKeyedRun(); if(failure==='timeout')vi.useFakeTimers();
        let listener:(value:unknown)=>void=()=>{}, disconnected:()=>void=()=>{};
        const postMessage=vi.fn(()=>{
            if(failure==='older helper')queueMicrotask(()=>listener({status:'PONG',version:'0.1.1',tools:{}}));
            if(failure==='disconnect')queueMicrotask(()=>disconnected());
        });
        vi.spyOn(fakeBrowser.runtime,'connectNative').mockReturnValue({onMessage:{addListener:(fn:typeof listener)=>{listener=fn;}},onDisconnect:{addListener:(fn:typeof disconnected)=>{disconnected=fn;}},disconnect:()=>{},postMessage} as any);
        const pending=translate(); if(failure==='timeout')await vi.advanceTimersByTimeAsync(10000);
        const response=await pending; expect(response.requestCount).toBe(0); expect(response.error).toContain('Upgrade/Repair');
        expect(postMessage.mock.calls).toHaveLength(1); expect(postMessage.mock.calls[0]).toEqual([{type:'PING'}]);
    });
    it('checks capabilities on the very same connection, then sends one protected request',async()=>{
        await bindKeyedRun(); let listener:(value:unknown)=>void=()=>{};
        const postMessage=vi.fn((message:any)=>queueMicrotask(()=>listener(message.type==='PING'
            ? {status:'PONG',version:'0.1.2',tools:{},capabilities:{credentialProtection:'windows-dpapi-v1'}}
            : {jobId:'keyed',translations:['literal'],requestCount:1})));
        const connect=vi.spyOn(fakeBrowser.runtime,'connectNative').mockReturnValue({onMessage:{addListener:(fn:typeof listener)=>{listener=fn;}},onDisconnect:{addListener:()=>{}},disconnect:()=>{},postMessage} as any);
        connect.mockClear();
        const response=await translate(); expect(response).toMatchObject({translations:['literal'],requestCount:1});
        expect(connect).toHaveBeenCalledTimes(1); expect(postMessage).toHaveBeenCalledTimes(2);
        expect(postMessage.mock.calls[1][0]).toMatchObject({translateConfig:{apiKey:'',credential:{schema:1,method:'windows-dpapi-v1',blob:'QUJDRA=='}},transportPolicy:'https-remote'});
        expect(JSON.stringify(await fakeBrowser.storage.session.get(null))).not.toContain('QUJDRA==');
    });
});
