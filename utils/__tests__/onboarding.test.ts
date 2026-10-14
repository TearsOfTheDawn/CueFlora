import { describe, expect, it, vi } from 'vitest';
import { createOnboardingService, ONBOARDING_KEY } from '../onboarding';
import { createPreferencesService, PREFERENCES_KEY } from '../preferences';
import { providerDefaults } from '../providers';

async function setup() {
    const data:Record<string,unknown> = {};
    const storage = {get:vi.fn(async (key:string)=>({[key]:data[key]})),set:vi.fn(async (value:Record<string,unknown>)=>{Object.assign(data,value);})};
    const preferences = createPreferencesService(storage); await preferences.initialize({cueflora_show_translation:'0'});
    const settings = providerDefaults(); settings.revision='current';
    const service = createOnboardingService(storage,preferences,{read:async()=>settings});
    const finish = (languages={transcription:'zh-CN',translation:'en'},revision='current')=>service.finish({type:'ONBOARDING_FINISH',revision,languages});
    return {data,storage,preferences,settings,service,finish};
}
describe('production onboarding persistence',()=>{
    it('writes both languages in one preference record and retains unrelated preferences',async()=>{
        const {storage,finish,preferences}=await setup(); storage.set.mockClear();
        expect(await finish()).toEqual({step:3,complete:true,languagesSaved:true});
        expect(storage.set.mock.calls.filter(([value])=>PREFERENCES_KEY in value)).toHaveLength(1);
        expect(await preferences.initialize({})).toEqual({cueflora_show_translation:'0',cueflora_transcription_lang:'zh-CN',cueflora_translation_lang:'en'});
    });
    it.each(['translation:en','invented','transcription:en'])('rejects invalid/unconfigured source %s before writing',async value=>{
        const {storage,finish}=await setup(); storage.set.mockClear();
        expect(await finish({transcription:value,translation:'en'})).toMatchObject({languagesSaved:false,reason:'languages'});
        expect(storage.set).not.toHaveBeenCalled();
    });
    it('rejects stale provider revisions without persistence',async()=>{
        const {storage,finish}=await setup(); storage.set.mockClear();
        expect(await finish(undefined,'old')).toMatchObject({languagesSaved:false,reason:'revision'});
        expect(storage.set).not.toHaveBeenCalled();
    });
    it('reports language failure without marking completion or leaking storage errors',async()=>{
        const {storage,data,finish}=await setup(); storage.set.mockRejectedValueOnce(Error('secret https://private.invalid'));
        const result=await finish(); expect(result).toMatchObject({languagesSaved:false,reason:'languages'});
        expect(data[ONBOARDING_KEY]).toBeUndefined(); expect(JSON.stringify(result)).not.toContain('private');
    });
    it('reports the separate progress failure honestly after languages are saved',async()=>{
        const {storage,finish,preferences,data}=await setup();
        storage.set.mockImplementation(async value=>{if(ONBOARDING_KEY in value)throw Error('quota'); Object.assign(data,value);});
        expect(await finish()).toMatchObject({languagesSaved:true,reason:'progress'});
        expect(await preferences.initialize({})).toHaveProperty('cueflora_translation_lang','en');
        expect(data[ONBOARDING_KEY]).toBeUndefined();
    });
    it('retains completion when navigating and reads legacy records unchanged',async()=>{
        const {data,service}=await setup(); data[ONBOARDING_KEY]={step:3,complete:true};
        expect(await service.read()).toEqual({step:3,complete:true});
        expect(await service.save(1,false)).toEqual({step:1,complete:true});
    });
    it('permits configured AI and translation Off without replacing native selections',async()=>{
        const {settings,finish}=await setup(); Object.assign(settings.transcription,{baseUrl:'https://fixture.invalid',model:'fixture'});
        expect(await finish({transcription:'transcription:zh-CN',translation:'none'})).toHaveProperty('complete',true);
        expect(await finish({transcription:'zh-CN',translation:'en'})).toHaveProperty('complete',true);
    });
    it('retains actual saved caption codes outside the catalogue and existing ASR ISO codes',async()=>{
        const {settings,finish,preferences}=await setup(); await preferences.save('cueflora_transcription_lang','zh-Hans');
        expect(await finish({transcription:'zh-Hans',translation:'none'})).toHaveProperty('complete',true);
        Object.assign(settings.transcription,{baseUrl:'https://fixture.invalid',model:'chosen'});
        expect(await finish({transcription:'transcription:zh',translation:'en'})).toHaveProperty('complete',true);
    });
});
