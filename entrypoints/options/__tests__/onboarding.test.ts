import { readFileSync } from 'node:fs';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fakeBrowser } from 'wxt/testing/fake-browser';
import { providerDefaults } from '../../../utils/providers';

const html = readFileSync('entrypoints/options/index.html', 'utf8');
describe('provider-neutral production onboarding', () => {
    const send = vi.fn();
    const click = (selector:string) => (document.querySelector(selector) as HTMLButtonElement).click();
    const field = (name:string) => document.querySelector(`[name="${name}"]`) as HTMLInputElement;
    beforeEach(() => {
        vi.resetModules(); fakeBrowser.reset(); send.mockReset();
        vi.spyOn(fakeBrowser.runtime,'getManifest').mockReturnValue({manifest_version:3,name:'CueFlora',version:'0.2.0'} as any);
        vi.spyOn(fakeBrowser.runtime, 'sendMessage').mockImplementation(send);
        document.body.innerHTML = new DOMParser().parseFromString(html,'text/html').body.innerHTML;
        send.mockImplementation(async message => {
            if (message.type === 'PROVIDERS_GET') return providerDefaults();
            if (message.type === 'ONBOARDING_GET') return {step:1,complete:false};
            if (message.type === 'PREFERENCES_INIT') return {};
            if (message.type === 'ONBOARDING_SAVE') return {step:message.step,complete:message.complete};
            if (message.type === 'PREFERENCES_SAVE') return {value:message.value};
            if (message.type === 'ONBOARDING_FINISH') return {step:3,complete:true,languagesSaved:true};
            throw Error('Unexpected request ' + message.type);
        });
    });
    afterEach(()=>vi.useRealTimers());
    const open = async () => { await import('../main'); await vi.waitFor(() => expect((document.getElementById('save') as HTMLButtonElement).disabled).toBe(false)); };
    it('opens blank, performs no checks, skips AI and finishes without inference', async () => {
        await open();
        expect(document.querySelector('input[name$=".connectionKind"]:checked')).toBeNull();
        for (const stage of ['transcription','translation']) { expect(field(stage+'.baseUrl').value).toBe(''); expect(field(stage+'.model').value).toBe(''); }
        click('[data-next="2"]'); await vi.waitFor(() => expect(document.getElementById('setup-progress')!.textContent).toBe('Step 2 of 3'));
        click('[data-next="3"]'); await vi.waitFor(() => expect(document.getElementById('setup-progress')!.textContent).toBe('Step 3 of 3'));
        click('#finish'); await vi.waitFor(() => expect(document.getElementById('setup-progress')!.textContent).toContain('Setup saved'));
        expect(send.mock.calls.some(([value])=>['PROVIDERS_CHECK','PING','TRANSCRIBE_NATIVE','TRANSLATE_NATIVE'].includes(value.type))).toBe(false);
        expect(send.mock.calls.filter(([value])=>value.type==='PREFERENCES_INIT')[0][0].legacy).toEqual({});
    });
    it('resumes an unfinished step and keeps completion false on persistence failure', async () => {
        send.mockImplementation(async message => {
            if(message.type==='PROVIDERS_GET')return providerDefaults();
            if(message.type==='ONBOARDING_GET')return {step:3,complete:false};
            if(message.type==='PREFERENCES_INIT')return {};
            return {error:'Could not save languages.',languagesSaved:false,reason:'languages'};
        });
        await open(); expect(document.getElementById('setup-progress')!.textContent).toBe('Step 3 of 3');
        click('#finish'); await vi.waitFor(() => expect(document.getElementById('status')!.textContent).toContain('Could not save languages'));
        expect(document.getElementById('setup-progress')!.textContent).not.toContain('Setup saved');
        expect(send.mock.calls.some(([value])=>value.type==='ONBOARDING_SAVE' && value.complete)).toBe(false);
    });
    it('ignores late checks after edits and always allows manual model entry', async () => {
        await open();
        let resolve!:(value:unknown)=>void;
        send.mockImplementationOnce(()=>new Promise(done=>{resolve=done;}));
        field('translation.baseUrl').value='http://localhost:1234/v1';
        click('[data-check="translation"]');
        const request = send.mock.calls.at(-1)![0]; expect(request.type).toBe('PROVIDERS_CHECK'); expect(request.provider.model).toBe('metadata-only');
        field('translation.model').value='manual-model'; field('translation.model').dispatchEvent(new Event('input'));
        resolve({requestId:request.requestId,status:'connected',models:['old-model']});
        await Promise.resolve(); await Promise.resolve();
        expect(document.querySelector('#translation-models option')).toBeNull();
        expect(field('translation.model').value).toBe('manual-model');
    });
    it('requires saving or cancelling drafts before advancing, and Cancel does not persist', async () => {
        await open(); click('[data-next="2"]'); await vi.waitFor(()=>expect(document.getElementById('setup-progress')!.textContent).toBe('Step 2 of 3'));
        field('translation.enabled').checked=true; field('translation.baseUrl').value='https://fixture.invalid/v1'; field('translation.model').value='chosen';
        click('[data-next="3"]'); await vi.waitFor(()=>expect(document.getElementById('status')!.textContent).toContain('Save your AI settings'));
        click('#cancel'); expect(field('translation.baseUrl').value).toBe('');
        click('[data-next="3"]'); await vi.waitFor(()=>expect(document.getElementById('setup-progress')!.textContent).toBe('Step 3 of 3'));
        expect(send.mock.calls.some(([value])=>value.type==='PROVIDERS_SAVE')).toBe(false);
    });
    it('keeps Advanced controls collapsed and reports partial persistence accurately', async () => {
        await open();
        const count = field('cueflora_translation_batch_size'); expect(count.closest('details')?.open).toBe(false);
        count.value='40';
        send.mockImplementation(async message=>{
            if(message.type==='PROVIDERS_SAVE')return {...message.settings,revision:'saved'};
            return {error:'quota'};
        });
        click('#save'); await vi.waitFor(()=>expect(document.getElementById('status')!.textContent).toContain('AI settings saved; Could not save Advanced'));
        expect(count.value).toBe('40'); click('#cancel'); expect(count.value).toBe('30');
        expect(send.mock.calls.some(([value])=>value.type==='PREFERENCES_SAVE' && value.key==='cueflora_translation_batch_size')).toBe(true);
    });
    it('selects only independently configured AI stages when saving languages', async () => {
        const configured=providerDefaults(); configured.revision='saved';
        Object.assign(configured.translation,{baseUrl:'http://localhost:1234/v1',model:'user-model',connectionKind:'local'});
        send.mockImplementation(async message=>{
            if(message.type==='PROVIDERS_GET')return configured;
            if(message.type==='ONBOARDING_GET')return {step:3,complete:false};
            if(message.type==='PREFERENCES_INIT')return {};
            if(message.type==='PREFERENCES_SAVE')return {value:message.value};
            if(message.type==='ONBOARDING_FINISH')return {step:3,complete:true,languagesSaved:true};
            return {step:message.step,complete:message.complete};
        });
        await open(); click('#finish'); await vi.waitFor(()=>expect(document.getElementById('setup-progress')!.textContent).toContain('Setup saved'));
        const languages=Object.values(send.mock.calls.find(([message])=>message.type==='ONBOARDING_FINISH')![0].languages);
        expect(languages).toEqual(['zh-CN','translation:en']);
        expect(send.mock.calls.some(([message])=>message.type==='TRANSLATE_NATIVE')).toBe(false);
    });
    it('detects label-only drafts, focuses the error and keeps Cancel non-mutating',async()=>{
        await open(); click('[data-next="2"]'); await vi.waitFor(()=>expect(document.querySelector('[data-step="2"]')!.hasAttribute('hidden')).toBe(false));
        field('translation.label').value='My service'; click('[data-next="3"]');
        await vi.waitFor(()=>expect(document.getElementById('status')!.textContent).toContain('Save your AI settings'));
        expect(document.activeElement).toBe(document.getElementById('status')); click('#cancel');
        expect(field('translation.label').value).toBe('Custom provider');
    });
    it('serializes navigation with Save and rejects a late check after navigation',async()=>{
        await open(); let resolve!:(value:unknown)=>void;
        send.mockImplementationOnce(()=>new Promise(done=>{resolve=done;})); click('[data-next="2"]');
        click('#save'); click('[data-next="3"]');
        expect(send.mock.calls.filter(([message])=>message.type==='ONBOARDING_SAVE')).toHaveLength(1);
        expect(send.mock.calls.some(([message])=>message.type==='PROVIDERS_SAVE')).toBe(false);
        resolve({step:2,complete:false}); await vi.waitFor(()=>expect(document.getElementById('setup-progress')!.textContent).toBe('Step 2 of 3'));
        let checkResolve!:(value:unknown)=>void; send.mockImplementationOnce(()=>new Promise(done=>{checkResolve=done;}));
        click('[data-check="translation"]'); const request=send.mock.calls.at(-1)![0];
        click('[data-next="1"]'); await vi.waitFor(()=>expect(document.getElementById('setup-progress')!.textContent).toBe('Step 1 of 3'));
        checkResolve({requestId:request.requestId,status:'connected',models:['late']}); await Promise.resolve(); await Promise.resolve();
        expect(document.querySelector('#translation-models option')).toBeNull();
    });
    it('keeps completed setup complete when navigating backward',async()=>{
        send.mockImplementation(async message=>{
            if(message.type==='PROVIDERS_GET')return providerDefaults();
            if(message.type==='ONBOARDING_GET')return {step:3,complete:true};
            if(message.type==='PREFERENCES_INIT')return {};
            return {step:message.step,complete:message.complete};
        });
        await open(); click('[data-next="2"]'); await vi.waitFor(()=>expect(document.querySelector('[data-step="2"]')!.hasAttribute('hidden')).toBe(false));
        expect(send.mock.calls.at(-1)![0]).toMatchObject({type:'ONBOARDING_SAVE',complete:true});
        expect(document.getElementById('setup-progress')!.textContent).toContain('Setup saved');
    });
    it('preserves native and Off selections with configured providers and snapshots Finish',async()=>{
        const configured=providerDefaults(); configured.revision='saved';
        for(const stage of ['transcription','translation'] as const)Object.assign(configured[stage],{baseUrl:'https://fixture.invalid',model:'chosen'});
        let resolve!:(value:unknown)=>void;
        send.mockImplementation(async message=>{
            if(message.type==='PROVIDERS_GET')return configured;
            if(message.type==='ONBOARDING_GET')return {step:3,complete:true};
            if(message.type==='PREFERENCES_INIT')return {cueflora_transcription_lang:'en',cueflora_translation_lang:'none'};
            return new Promise(done=>{resolve=done;});
        });
        await open(); click('#finish'); click('[data-next="2"]'); click('#save');
        const finish=send.mock.calls.at(-1)![0]; expect(finish).toMatchObject({type:'ONBOARDING_FINISH',revision:'saved',languages:{transcription:'en',translation:'none'}});
        const select=document.getElementById('transcription-language') as HTMLSelectElement; expect(select.disabled).toBe(true); select.value='ja';
        expect(finish.languages.transcription).toBe('en');
        resolve({step:3,complete:true,languagesSaved:true}); await vi.waitFor(()=>expect(select.disabled).toBe(false));
        expect(send.mock.calls.filter(([message])=>message.type==='ONBOARDING_FINISH')).toHaveLength(1);
    });
    it('offers Retry after initialization failure without duplicating listeners or languages',async()=>{
        send.mockRejectedValueOnce(Error('Storage unavailable')); await import('../main');
        await vi.waitFor(()=>expect(document.getElementById('status')!.textContent).toContain('Storage unavailable'));
        expect((document.getElementById('save') as HTMLButtonElement).disabled).toBe(true);
        click('#reload'); await vi.waitFor(()=>expect((document.getElementById('save') as HTMLButtonElement).disabled).toBe(false));
        const count=document.querySelectorAll('#translation-language option').length;
        click('[data-next="2"]'); await vi.waitFor(()=>expect(document.getElementById('setup-progress')!.textContent).toBe('Step 2 of 3'));
        expect(send.mock.calls.filter(([message])=>message.type==='ONBOARDING_SAVE')).toHaveLength(1); expect(count).toBeGreaterThan(0);
    });
    it('blocks uncertain writes until a user-triggered reconciled read and keeps the draft',async()=>{
        await open(); vi.useFakeTimers(); let late!:(value:unknown)=>void;
        send.mockImplementationOnce(()=>new Promise(done=>{late=done;}));
        field('translation.enabled').checked=true; field('translation.baseUrl').value='https://fixture.invalid'; field('translation.model').value='draft'; click('#save');
        await vi.advanceTimersByTimeAsync(15000);
        expect(document.getElementById('status')!.textContent).toContain('timed out'); expect((document.getElementById('save') as HTMLButtonElement).disabled).toBe(true);
        click('#save'); expect(send.mock.calls.filter(([message])=>message.type==='PROVIDERS_SAVE')).toHaveLength(1);
        late({...providerDefaults(),revision:'late'}); await vi.advanceTimersByTimeAsync(1);
        expect(field('translation.model').value).toBe('draft');
        const persisted=providerDefaults(); persisted.revision='persisted'; Object.assign(persisted.translation,{baseUrl:'https://fixture.invalid',model:'saved-model'});
        send.mockResolvedValueOnce({providers:persisted,preferences:{},onboarding:{step:1,complete:false}}); click('#reload');
        await vi.advanceTimersByTimeAsync(1); expect(field('translation.model').value).toBe('draft'); expect((document.getElementById('save') as HTMLButtonElement).disabled).toBe(false);
        click('#cancel'); expect(field('translation.model').value).toBe('saved-model');
    });
    it.each(['revision','progress'])('blocks Finish after %s failure while retaining language edits',async reason=>{
        await open(); const select=document.getElementById('translation-language') as HTMLSelectElement; select.value='ja';
        send.mockResolvedValueOnce({error:reason==='progress'?'Languages saved, setup progress not saved.':'AI settings changed elsewhere.',reason,languagesSaved:reason==='progress'});
        click('#finish'); await vi.waitFor(()=>expect((document.getElementById('finish') as HTMLButtonElement).disabled).toBe(true));
        await vi.waitFor(()=>expect(document.getElementById('status')!.textContent).toContain(reason==='progress'?'Languages saved':'changed elsewhere'));
        expect(select.value).toBe('ja'); expect((document.getElementById('reload') as HTMLButtonElement).disabled).toBe(false);
    });
    it('reports metadata errors privately and distinguishes helper availability from readiness',async()=>{
        await open(); field('translation.apiKey').value='private-secret'; field('translation.baseUrl').value='https://private.invalid';
        send.mockResolvedValueOnce({error:'private-secret https://private.invalid'}); click('[data-check="translation"]');
        await vi.waitFor(()=>expect(document.querySelector('[data-check="translation"]')!.hasAttribute('disabled')).toBe(false));
        const output=document.querySelector('[data-check="translation"]')!.nextElementSibling!.textContent; expect(output).not.toContain('private-secret'); expect(output).not.toContain('private.invalid');
        send.mockResolvedValueOnce({status:'PONG',version:'0.1.0',tools:{'yt-dlp':{available:true},ffmpeg:{available:false},ffprobe:{available:true}}}); click('#health');
        await vi.waitFor(()=>expect(document.getElementById('health-status')!.textContent).toContain('not ready'));
        expect(document.getElementById('health-status')!.textContent).toContain('Repair');
    });
});
