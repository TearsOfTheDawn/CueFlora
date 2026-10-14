import {describe,it,expect,vi} from 'vitest';
import {createProviderService,providerDefaults,PROVIDERS_KEY,LEGACY_PROVIDERS_KEY,validateProvider,providerSummary} from '../providers';
import {validCredential,type ProtectedCredential} from '../credentials';
import {privateDiagnostic,publicNativeResponse,validNativeResponse} from '../nativeResponse';
const cipher:ProtectedCredential={schema:1,method:'windows-dpapi-v1',blob:'QUJDRA=='};
function fixture(){
    const data:Record<string,unknown>={};
    const storage={get:vi.fn(async()=>structuredClone(data)),set:vi.fn(async(items:Record<string,unknown>)=>{Object.assign(data,structuredClone(items));}),remove:vi.fn(async(key:string)=>{delete data[key];})};
    const retained:string[]=[], protect=vi.fn(async()=>({...cipher}));
    const service=createProviderService(storage,{protect,retain:async()=>retained});
    const initial=providerDefaults(); initial.translation={...initial.translation,baseUrl:'https://service.invalid/v1',model:'synthetic',apiKey:'synthetic-only',keyAction:'replace'};
    return {data,storage,retained,protect,service,initial};
}
describe('protected provider production service',()=>{
    it('persists only encrypted material; settings and summaries have no keys, blobs or references',async()=>{
        const f=fixture(), saved=await f.service.save(f.initial);
        expect(saved.translation.keySaved).toBe(true); expect(saved.translation.credentialId).toBeUndefined(); expect(saved.translation.apiKey).toBe('');
        expect(JSON.stringify(saved)).not.toContain(cipher.blob); expect(JSON.stringify(f.data)).not.toContain('synthetic-only');
        const bound=await f.service.read(); expect(bound.translation.credentialId).toBeTruthy();
        expect(JSON.stringify(bound)).not.toContain(cipher.blob); expect(JSON.stringify(providerSummary(bound))).not.toContain('credential');
        expect(await f.service.materialize(bound.translation)).toMatchObject({credential:cipher,apiKey:''});
    });
    it('keeps keys without new protection, and requires explicit address reuse',async()=>{
        const f=fixture(), saved=await f.service.save(f.initial); f.protect.mockClear();
        const next=await f.service.save({...saved,translation:{...saved.translation,keyAction:'keep'}}); expect(f.protect).not.toHaveBeenCalled();
        const changed={...next,translation:{...next.translation,baseUrl:'https://new.invalid/v1',keyAction:'keep' as const}};
        await expect(f.service.save(changed)).rejects.toThrow('explicitly confirm');
        await f.service.save({...changed,translation:{...changed.translation,reuseKey:true}});
        expect(f.protect).toHaveBeenCalledWith({stage:'translation',baseUrl:'https://new.invalid/v1',credential:cipher,previousBaseUrl:'https://service.invalid/v1'});
    });
    it('retains old Run references through removal, then retires them',async()=>{
        const f=fixture(), saved=await f.service.save(f.initial), bound=await f.service.read(); f.retained.push(bound.translation.credentialId!);
        const removed=await f.service.save({...saved,translation:{...saved.translation,keyAction:'remove'}}); expect(removed.translation.keySaved).toBe(false);
        expect(await f.service.materialize(bound.translation)).toHaveProperty('credential'); f.retained.length=0; await f.service.prune();
        await expect(f.service.materialize(bound.translation)).rejects.toThrow('unavailable');
    });
    it('migrates once, never exposes legacy secrets, and retries failed cleanup',async()=>{
        const f=fixture(); f.data[LEGACY_PROVIDERS_KEY]={...f.initial,revision:'legacy'};
        expect(JSON.stringify(await f.service.read())).not.toContain('synthetic-only'); f.storage.remove.mockRejectedValueOnce(Error('quota'));
        const partial=await f.service.migrate(); expect(partial.warning).toContain('cleanup failed');
        expect(f.data[LEGACY_PROVIDERS_KEY]).toBeTruthy(); expect(f.data[PROVIDERS_KEY]).toBeTruthy(); f.protect.mockClear();
        const complete=await f.service.migrate(); expect(complete.warning).toBeUndefined(); expect(f.protect).not.toHaveBeenCalled(); expect(f.data[LEGACY_PROVIDERS_KEY]).toBeUndefined();
    });
    it('retains legacy data after protection/persistence failure and permits retry',async()=>{
        const f=fixture(); f.data[LEGACY_PROVIDERS_KEY]={...f.initial,revision:'legacy'}; f.protect.mockRejectedValueOnce(Error('unavailable'));
        expect((await f.service.migrate()).warning).toContain('retained'); expect(f.data[PROVIDERS_KEY]).toBeUndefined(); f.storage.set.mockRejectedValueOnce(Error('quota'));
        expect((await f.service.migrate()).warning).toContain('retained'); expect(f.data[LEGACY_PROVIDERS_KEY]).toBeTruthy(); expect((await f.service.migrate()).translation.keySaved).toBe(true);
    });
    it('serializes overlapping saves and rejects stale revisions before protecting again',async()=>{
        const f=fixture(), results=await Promise.allSettled([f.service.save(f.initial),f.service.save(f.initial)]);
        expect(results.filter(result=>result.status==='fulfilled')).toHaveLength(1); expect(f.protect).toHaveBeenCalledTimes(1);
    });
    it('cannot silently persist keys without a protector',async()=>{
        const f=fixture(), service=createProviderService(f.storage); await expect(service.save(f.initial)).rejects.toThrow('Upgrade/Repair'); expect(f.data[PROVIDERS_KEY]).toBeUndefined();
    });
    it('rejects malformed blobs and narrowly projects correlated protection/health replies',()=>{
        expect(validCredential({...cipher,extra:'secret'})).toBe(false); const request={type:'CREDENTIAL_PROTECT',requestId:'id',apiKey:'synthetic-only'};
        expect(validNativeResponse({requestId:'old',credential:cipher},request)).toBe(false);
        expect(publicNativeResponse({requestId:'id',credential:cipher,extra:'secret'},request)).not.toHaveProperty('extra');
        expect(publicNativeResponse({status:'PONG',tools:{},capabilities:{credentialProtection:'windows-dpapi-v1',extra:'secret'}},{type:'PING'}).capabilities).toEqual({credentialProtection:'windows-dpapi-v1'});
        expect(privateDiagnostic('synthetic-only '+cipher.blob,{...request,credential:cipher})).toBe('[redacted] [redacted]');
    });
    it('enforces store HTTPS and rejects deceptive loopback forms while preserving preview HTTP',()=>{
        const provider={...providerDefaults().translation,model:'synthetic',allowRemoteHttp:true};
        for(const baseUrl of ['http://remote.invalid','http://localhost.evil','http://127.0.0.1.evil','http://127.1','http://2130706433','http://0x7f000001']) expect(()=>validateProvider({...provider,baseUrl},'https-remote')).toThrow();
        for(const baseUrl of ['http://localhost:8000','http://127.0.0.1:8000','http://[::1]:8000']) expect(validateProvider({...provider,baseUrl},'https-remote')).toHaveProperty('baseUrl');
        expect(validateProvider({...provider,baseUrl:'http://remote.invalid'},'preview')).toHaveProperty('baseUrl');
    });
});
