import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { fakeBrowser } from 'wxt/testing/fake-browser';
import { providerDefaults, providerSummary } from '../../../utils/providers';
vi.mock('../render',async original=>({...await original<typeof import('../render')>(),startRenderLoop:vi.fn(),runSubtitleWorkflow:vi.fn()}));
let cleanup:(()=>void)|null=null;
beforeEach(()=>{vi.resetModules();fakeBrowser.reset();window.history.replaceState({},'','/watch?v=U_V6Jqg7PV4');document.body.innerHTML='<div id="movie_player"><video></video><div class="ytp-right-controls"></div></div>';});
afterEach(()=>{cleanup?.();cleanup=null;});
async function setup() {
    let prefs={cueflora_transcription_lang:'en',cueflora_translation_lang:'none'};
    const send=vi.spyOn(fakeBrowser.runtime,'sendMessage').mockImplementation(async (message:any)=>message.type==='PROVIDERS_SUMMARY'?providerSummary(providerDefaults()):message.type==='PREFERENCES_INIT'?prefs:{value:message.value});
    const {state}=await import('../../../utils/state'); state.availableTracks=[{languageCode:'en'},{languageCode:'ja'}];state.workflow=(await import('../../../utils/workflowState')).createIdleWorkflowState();state.isPanelOpen=false;
    const ui=await import('../ui');await ui.createUI();ui.populateDropdowns();cleanup=state._cleanupUI;
    return {send,state,ui,setPrefs:(value:typeof prefs)=>{prefs=value;}};
}
it('refreshes an idle player on focus/panel opening and clears only obsolete display',async()=>{
    const {ui,send,state,setPrefs}=await setup();
    state.transcriptionCues=[{startMs:0,endMs:1,text:'old'}];setPrefs({cueflora_transcription_lang:'ja',cueflora_translation_lang:'none'});
    ui.togglePanel();await vi.waitFor(()=>expect((document.getElementById('cueflora-transcription-lang') as HTMLSelectElement).value).toBe('ja'));
    expect(state.transcriptionCues).toEqual([]);setPrefs({cueflora_transcription_lang:'en',cueflora_translation_lang:'none'});window.dispatchEvent(new Event('focus'));
    await vi.waitFor(()=>expect((document.getElementById('cueflora-transcription-lang') as HTMLSelectElement).value).toBe('en'));
    expect(send.mock.calls.some(([message]:any[])=>['TRANSCRIBE_NATIVE','TRANSLATE_NATIVE'].includes(message.type))).toBe(false);
});
it('does not refresh an active Run or an open appearance draft',async()=>{
    const {send,state,setPrefs}=await setup();send.mockClear();state.workflow.status='transcribing';window.dispatchEvent(new Event('focus'));expect(send).not.toHaveBeenCalled();
    state.workflow.status='idle';(document.getElementById('cueflora-nav-appearance') as HTMLButtonElement).click();
    const size=document.getElementById('cueflora-appearance-sourceSize') as HTMLInputElement;size.value='30';size.dispatchEvent(new Event('input'));
    setPrefs({cueflora_transcription_lang:'ja',cueflora_translation_lang:'none'});send.mockClear();window.dispatchEvent(new Event('focus'));expect(send).not.toHaveBeenCalled();expect(size.value).toBe('30');
});
it('rejects a preference reply if Run starts during refresh',async()=>{
    const {send,state}=await setup();let reply!:(value:unknown)=>void;
    send.mockImplementation(async (message:any)=>message.type==='PROVIDERS_SUMMARY'?providerSummary(providerDefaults()):new Promise<unknown>(resolve=>{reply=resolve;}));
    window.dispatchEvent(new Event('focus'));await vi.waitFor(()=>expect(reply).toBeTypeOf('function'));
    state.workflow.status='transcribing';reply({cueflora_transcription_lang:'ja'});await Promise.resolve();await Promise.resolve();
    expect((document.getElementById('cueflora-transcription-lang') as HTMLSelectElement).value).toBe('en');
});
