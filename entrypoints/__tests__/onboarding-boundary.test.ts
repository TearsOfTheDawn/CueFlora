import { beforeEach, expect, it, vi } from 'vitest';
import { fakeBrowser } from 'wxt/testing';
import background from '../background';
import { providerDefaults } from '../../utils/providers';
beforeEach(()=>{fakeBrowser.reset();vi.spyOn(fakeBrowser.action.onClicked,'addListener').mockImplementation(()=>{});vi.spyOn(fakeBrowser.runtime.onInstalled,'addListener').mockImplementation(()=>{});background.main();});
const options=()=>({id:fakeBrowser.runtime.id,url:fakeBrowser.runtime.getURL('/options.html')});
const call=async(message:object,sender:object=options())=>(await fakeBrowser.runtime.onMessage.trigger(message,sender))[0];
it('restricts Finish/reconciliation to options and validates shapes before mutation',async()=>{
    const player={id:fakeBrowser.runtime.id,url:'https://www.youtube.com/watch?v=U_V6Jqg7PV4',frameId:0,tab:{id:1}};
    expect(await call({type:'SETTINGS_RECONCILE'},player)).toHaveProperty('error');
    expect(await call({type:'ONBOARDING_FINISH',revision:'',languages:{transcription:'en',translation:'none'}},player)).toHaveProperty('error');
    expect(await call({type:'ONBOARDING_FINISH',revision:'',languages:{transcription:[]}})).toHaveProperty('error');
});
it('finishes without native dispatch and preserves the legacy preference record',async()=>{
    const connect=vi.spyOn(fakeBrowser.runtime,'connectNative');
    await call({type:'PREFERENCES_INIT',legacy:{}});
    expect(await call({type:'ONBOARDING_FINISH',revision:'',languages:{transcription:'zh-CN',translation:'none'}})).toEqual({step:3,complete:true,languagesSaved:true});
    const result=await call({type:'SETTINGS_RECONCILE'}); expect(result.onboarding.complete).toBe(true);
    expect(result.preferences.cueflora_translation_lang).toBe('none'); expect(connect).not.toHaveBeenCalled();
});
it('queues reconciliation behind an outstanding write rather than returning the old state',async()=>{
    const original=fakeBrowser.storage.local.set.bind(fakeBrowser.storage.local);
    let release!:()=>void;
    const set=vi.spyOn(fakeBrowser.storage.local,'set').mockImplementationOnce(async (value:Record<string,unknown>)=>{await new Promise<void>(resolve=>{release=resolve;});await original(value);});
    const saved=call({type:'PROVIDERS_SAVE',settings:providerDefaults()}); await vi.waitFor(()=>expect(set).toHaveBeenCalled());
    let reconciled=false; const reread=call({type:'SETTINGS_RECONCILE'}).then(value=>{reconciled=true;return value;});
    await Promise.resolve(); expect(reconciled).toBe(false); release();
    const value=await saved; expect((await reread).providers.revision).toBe(value.revision);
});
