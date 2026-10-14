import { LANGUAGES } from './constants';
import { providerConfigured, type ProviderSettings } from './providers';
import type { OnboardingFinishMessage, OnboardingFinishResult, OnboardingState } from './types';

export const ONBOARDING_KEY = 'cueflora_onboarding_v1';
export function createOnboardingService(storage: {
    get: (key:string) => Promise<Record<string,unknown>>;
    set: (items:Record<string,unknown>) => Promise<void>;
}, preferences: { saveMany: (values:Record<string,string>) => Promise<Record<string,string>>; readValues:()=>Promise<Record<string,string>> },
providers: { read: () => Promise<ProviderSettings> }) {
    const read = async (): Promise<OnboardingState> => {
        const raw = (await storage.get(ONBOARDING_KEY))[ONBOARDING_KEY] as OnboardingState | undefined;
        return raw && Number.isInteger(raw.step) && raw.step >= 1 && raw.step <= 3 && typeof raw.complete === 'boolean'
            ? {step:raw.step,complete:raw.complete} : {step:1,complete:false};
    };
    return {
        read,
        save: async (step:number, complete:boolean) => {
            const previous = await read();
            const value = {step,complete:previous.complete || complete};
            await storage.set({[ONBOARDING_KEY]:value}); return value;
        },
        finish: async (message:OnboardingFinishMessage): Promise<OnboardingFinishResult> => {
            const settings = await providers.read();
            if (message.revision !== settings.revision) return {languagesSaved:false,reason:'revision',error:'AI settings changed elsewhere. Reload saved state, review your edits, and try again.'};
            const previous = await preferences.readValues();
            const updates: Record<string,string> = {};
            for (const stage of ['transcription','translation'] as const) {
                const value = message.languages[stage];
                const ai = value.startsWith(stage + ':');
                const code = ai ? value.slice(stage.length + 1) : value;
                const language = LANGUAGES.find(language => language.bcp47 === code || language.iso.code === code);
                const validCaption = /^[a-zA-Z0-9-]{1,40}$/.test(code) && (!!language || previous['cueflora_'+stage+'_lang'] === value);
                if (value !== 'none' && (ai ? (!language || !providerConfigured(settings[stage]) || (stage === 'transcription' && !language.iso.whisper)) : !validCaption)) {
                    return {languagesSaved:false,reason:'languages',error:'Choose available languages and configure any selected AI stage first.'};
                }
                updates['cueflora_' + stage + '_lang'] = value;
            }
            try { await preferences.saveMany(updates); }
            catch { return {languagesSaved:false,reason:'languages',error:'Could not save languages. Your selections are retained; retry when storage is available.'}; }
            try {
                const value = {step:3,complete:true};
                await storage.set({[ONBOARDING_KEY]:value});
                return {...value,languagesSaved:true};
            } catch { return {languagesSaved:true,reason:'progress',error:'Languages saved, setup progress not saved. Reload saved state before finishing again.'}; }
        },
    };
}
