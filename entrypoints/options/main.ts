import { providerDefaults, providerConfigured, type Provider, type ProviderSettings } from '../../utils/providers';
import { LANGUAGES, DEFAULT_TRANSCRIPTION_MAX_PARALLEL, DEFAULT_TRANSCRIPTION_MB_PER_REQ, DEFAULT_TRANSLATION_BATCH_SIZE } from '../../utils/constants';
import './style.css';
import { settingsRequest, SettingsTimeout } from '../../utils/settingsRequest';
import { privateDiagnostic } from '../../utils/nativeResponse';
import type { OnboardingFinishMessage, OnboardingFinishResult } from '../../utils/types';
import { renderReleaseGuidance } from '../../utils/publicLinks';

renderReleaseGuidance(document);

const form = document.getElementById('providers')!, status = document.getElementById('status')!;
const saveButton = document.getElementById('save') as HTMLButtonElement, cancelButton = document.getElementById('cancel') as HTMLButtonElement;
const wizard = document.getElementById('setup');
const fields = new Map<string, HTMLInputElement>(), checks = new Map<string, number>(), outputs = new Map<string, HTMLElement>();
const processing = new Map<string, { input:HTMLInputElement; saved:string }>();
let saved = providerDefaults(), loaded = false, busy = false, blocked = false, step = 1, complete = false;
let providerBaseline = '';
const reload = document.getElementById('reload') as HTMLButtonElement || document.createElement('button');
if (!reload.id) { reload.id = 'reload'; reload.type = 'button'; status.after(reload); }
const retryMigration=document.createElement('button'); retryMigration.id='retry-key-migration'; retryMigration.type='button'; retryMigration.textContent='Retry protected key migration'; retryMigration.hidden=true; reload.after(retryMigration);
status.tabIndex = -1;
const checking = new Set<string>();
const button = (label: string, handler: () => void) => {
    const element = document.createElement('button'); element.type = 'button'; element.textContent = label;
    element.addEventListener('click', handler); return element;
};
for (const stage of ['transcription', 'translation'] as const) {
    const section = document.createElement('fieldset'), legend = document.createElement('legend');
    legend.textContent = stage === 'transcription' ? 'Transcribe audio' : 'Translate subtitles'; section.append(legend);
    const enable = document.createElement('input'); enable.type = 'checkbox'; enable.name = stage + '.enabled'; fields.set(enable.name, enable);
    const enableLabel = document.createElement('label'); enableLabel.append(enable, document.createTextNode(' Configure this AI stage (optional)')); section.append(enableLabel);
    const choice = document.createElement('div'); choice.className = 'choices';
    for (const kind of ['hosted','local']) {
        const label = document.createElement('label'), radio = document.createElement('input'); radio.type = 'radio'; radio.name = stage + '.connectionKind'; radio.value = kind;
        label.append(radio, document.createTextNode(kind === 'hosted' ? 'Hosted service' : 'Existing local service'));
        radio.addEventListener('change', () => { enable.checked = true; invalidate(stage); }); choice.append(label);
    }
    section.append(choice);
    const advanced = document.createElement('details'), summary = document.createElement('summary'); summary.textContent = 'Advanced'; advanced.append(summary);
    for (const [key, title] of Object.entries({ baseUrl: 'Service address', apiKey: 'API key (if required)', model: 'Model name', label: 'Display label', allowRemoteHttp: 'Allow unencrypted non-loopback HTTP' })) {
        const label = document.createElement('label'); label.textContent = title;
        const input = document.createElement('input'); input.name = stage + '.' + key; input.autocomplete = 'off';
        input.type = key === 'allowRemoteHttp' ? 'checkbox' : key === 'apiKey' ? 'password' : 'text';
        if (key === 'model') { const list = document.createElement('datalist'); list.id = stage + '-models'; input.setAttribute('list', list.id); section.append(list); }
        fields.set(input.name, input); label.append(input); (key === 'label' || key === 'allowRemoteHttp' ? advanced : section).append(label);
        input.addEventListener('input', () => invalidate(stage));
        if (key === 'apiKey') input.addEventListener('input', () => {
            const replace = form.querySelector<HTMLInputElement>(`input[name="${stage}.keyAction"][value="replace"]`);
            if (replace) replace.checked = true;
        });
    }
    const keyStatus = document.createElement('p'); keyStatus.id = stage + '-key-status'; keyStatus.textContent = 'No API key saved.'; section.append(keyStatus);
    const keyChoices = document.createElement('div'); keyChoices.className='choices';
    for (const [value,title] of [['keep','Keep saved key'],['replace','Replace key'],['remove','Remove key']]) {
        const label=document.createElement('label'), radio=document.createElement('input'); radio.type='radio'; radio.name=stage+'.keyAction'; radio.value=value; radio.checked=value==='keep';
        label.append(radio,document.createTextNode(title)); keyChoices.append(label);
        radio.addEventListener('change',()=>{if(value!=='replace') fields.get(stage+'.apiKey')!.value=''; invalidate(stage);});
    }
    section.append(keyChoices);
    const reuseLabel=document.createElement('label'), reuse=document.createElement('input'); reuse.type='checkbox'; reuse.name=stage+'.reuseKey'; fields.set(reuse.name,reuse);
    reuseLabel.append(reuse,document.createTextNode('I confirm reuse of the saved key if I change this service address.'));
    advanced.append(reuseLabel); reuse.addEventListener('change',()=>invalidate(stage));
    const output = document.createElement('p'); output.setAttribute('role', 'status'); output.textContent = 'Not checked.'; outputs.set(stage, output);
    const controls = stage === 'transcription' ? [
        ['cueflora_transcription_max_parallel','Concurrent audio uploads',DEFAULT_TRANSCRIPTION_MAX_PARALLEL,1,16],
        ['cueflora_transcription_mb_per_req','Maximum upload size (MiB)',DEFAULT_TRANSCRIPTION_MB_PER_REQ,1,25],
    ] as const : [['cueflora_translation_batch_size','Cues per translation batch',DEFAULT_TRANSLATION_BATCH_SIZE,10,60]] as const;
    for (const [key,title,value,min,max] of controls) {
        const label = document.createElement('label'); label.textContent = title;
        const input = document.createElement('input'); input.type = 'number'; input.name = key; input.min=String(min); input.max=String(max); input.step='1'; input.value=String(value);
        processing.set(key,{input,saved:input.value}); label.append(input); advanced.append(label);
    }
    const check = button('Check connection / Load models', () => void checkProvider(stage, check)); check.dataset.check = stage;
    section.append(advanced, check, output); form.append(section); enable.addEventListener('change', () => invalidate(stage));
}
function invalidate(stage: string) {
    checks.set(stage, (checks.get(stage) || 0) + 1); outputs.get(stage)!.textContent = 'Not checked. Changes invalidate earlier results.';
    document.getElementById(stage + '-models')!.replaceChildren();
    checking.delete(stage);
    if (loaded && !busy) (form.querySelector(`[data-check="${stage}"]`) as HTMLButtonElement).disabled = false;
}
function draftProvider(stage: 'transcription' | 'translation', forCheck = false): Provider {
    const get = (key: string) => fields.get(stage + '.' + key)!;
    const kind = form.querySelector<HTMLInputElement>(`input[name="${stage}.connectionKind"]:checked`)?.value;
    if (!get('enabled').checked && !forCheck) return { ...providerDefaults()[stage] };
    return { label: get('label').value || (kind === 'local' ? 'Local service' : kind === 'hosted' ? 'Hosted service' : 'Custom provider'),
        baseUrl: get('baseUrl').value.trim(), apiKey: get('apiKey').value, model: get('model').value.trim() || (forCheck ? 'metadata-only' : ''),
        allowRemoteHttp: get('allowRemoteHttp').checked,
        keyAction:(form.querySelector<HTMLInputElement>(`input[name="${stage}.keyAction"]:checked`)?.value || 'keep') as Provider['keyAction'],
        reuseKey:get('reuseKey').checked,
        ...(kind === 'hosted' || kind === 'local' ? { connectionKind: kind } : {}) };
}
async function checkProvider(stage: 'transcription' | 'translation', check: HTMLButtonElement) {
    if (!loaded || busy || check.disabled) return;
    const sequence = (checks.get(stage) || 0) + 1; checks.set(stage, sequence); const requestId = crypto.randomUUID(); check.disabled = true;
    checking.add(stage);
    const output = outputs.get(stage)!; output.textContent = 'Checking metadata only; no transcription or translation is generated…';
    try {
        const result = await settingsRequest({ type: 'PROVIDERS_CHECK', requestId, stage, revision:saved.revision, provider: draftProvider(stage, true) });
        if (checks.get(stage) !== sequence) return;
        if (result?.error) throw Error(result.error);
        if (result?.requestId !== requestId) throw Error('Invalid or stale connection-check response.');
        if (result.status === 'connected') {
            output.textContent = 'Connection verified; subtitle-generation compatibility is not tested. Select or enter your model.';
            const list = document.getElementById(stage + '-models')!; list.replaceChildren();
            for (const model of result.models || []) { const option = document.createElement('option'); option.value = model; list.append(option); }
        } else if (result.status === 'unsupported') output.textContent = 'Model listing is unavailable. Enter the model manually; generation is not verified.';
        else output.textContent = ({auth:'Authentication failed. Check the API key and service permissions.',
            network:'Service unreachable. Check the address and that your service is running.',
            http:'The service rejected the metadata request. Check its API base address and access permissions.',
            oversized:'The model list was too large. Enter your model name manually.',
            'invalid-response':'The service returned an invalid model list. Check API compatibility or enter your model manually.'} as Record<string,string>)[result.reason] || 'Connection could not be verified. Enter your model manually or retry.';
    } catch (error) {
        if (checks.get(stage) === sequence) {
            const detail=safeError(error);
            output.textContent = /timed out/i.test(detail) ? 'Connection check timed out. Check that the helper and AI service are available, then retry.' :
                /native host|helper/i.test(detail) ? 'Connection check could not reach the helper. Use Step 1 to check it, then Install or Repair CueFlora if needed.' :
                /invalid url/i.test(detail) ? 'Enter the service API base address before checking the connection.' : detail;
        }
    }
    finally { if (checks.get(stage) === sequence) { checking.delete(stage); check.disabled = busy || !loaded; } }
}
function syncControls() {
    for (const input of form.querySelectorAll<HTMLInputElement | HTMLButtonElement>('input,button')) input.disabled = busy || !loaded;
    for (const stage of checking) (form.querySelector(`[data-check="${stage}"]`) as HTMLButtonElement).disabled = true;
    saveButton.disabled = busy || !loaded || blocked; cancelButton.disabled = busy || !loaded;
    for (const control of document.querySelectorAll<HTMLButtonElement | HTMLSelectElement>('[data-next],#finish,[data-language]')) control.disabled = busy || !loaded || blocked;
    reload.disabled = busy; reload.textContent = loaded ? 'Reload saved state (keep edits)' : 'Retry loading settings';
    retryMigration.disabled=busy || !loaded || blocked;
    form.setAttribute('aria-busy',String(busy));
}
function safeError(error: unknown) {
    let text = error instanceof Error ? error.message : 'Settings operation failed. Retry or reload saved state.';
    for (const stage of ['transcription','translation'] as const) text = privateDiagnostic(text,{provider:draftProvider(stage,true)});
    return text;
}
function report(error:unknown) { status.textContent = safeError(error); status.focus(); }
function rawFields() {
    return Array.from(form.querySelectorAll<HTMLInputElement>('input')).filter(input=>!processing.has(input.name)).map(input=>
        [input.name,input.type === 'radio' ? input.value : '',['checkbox','radio'].includes(input.type) ? input.checked : input.value]);
}
function hasDraft() { return JSON.stringify(rawFields()) !== providerBaseline || Array.from(processing.values()).some(field=>field.input.value !== field.saved); }
async function action(work:()=>Promise<void>, write = false) {
    if (busy || (write && (!loaded || blocked))) return;
    busy = true; syncControls();
    // A metadata response must not repaint a saved/cancelled/hidden draft.
    for (const stage of ['transcription','translation']) invalidate(stage);
    try { await work(); }
    catch (error) {
        if (error instanceof SettingsTimeout || /changed elsewhere|settings changed/i.test(safeError(error))) blocked = true;
        report(error);
    } finally { busy = false; syncControls(); }
}
function display(value: ProviderSettings) {
    saved = value;
    retryMigration.hidden=!value.warning;
    for (const stage of ['transcription','translation'] as const) {
        fields.get(stage + '.enabled')!.checked = providerConfigured(saved[stage]);
        for (const key of ['label','baseUrl','apiKey','model','allowRemoteHttp']) {
            const input = fields.get(stage + '.' + key)!, value = saved[stage][key as keyof Provider];
            if (typeof value === 'boolean') input.checked = value; else input.value = typeof value === 'string' ? value : '';
        }
        for (const radio of form.querySelectorAll<HTMLInputElement>(`input[name="${stage}.connectionKind"]`)) radio.checked = radio.value === saved[stage].connectionKind;
        fields.get(stage+'.apiKey')!.value='';
        fields.get(stage+'.apiKey')!.placeholder = saved[stage].keySaved ? 'Type a replacement key, or keep the saved key' : 'Optional: your service API key';
        fields.get(stage+'.reuseKey')!.checked=false;
        for(const radio of form.querySelectorAll<HTMLInputElement>(`input[name="${stage}.keyAction"]`)) radio.checked=radio.value==='keep';
        document.getElementById(stage+'-key-status')!.textContent = saved[stage].migrationRequired ? 'API key migration incomplete. Upgrade/Repair and Reload, or Replace/Remove it.' : saved[stage].keySaved ? 'API key saved — protected by your Windows account.' : 'No API key saved.';
        invalidate(stage);
    }
    providerBaseline = JSON.stringify(rawFields());
}
syncControls(); status.textContent = 'Loading settings…'; form.addEventListener('submit', event => event.preventDefault());
async function load() {
    const response = await settingsRequest({ type: 'PROVIDERS_GET' });
    if (response?.error || !response?.transcription) throw Error(response?.error || 'Could not load settings.');
    display(response); if (wizard) await loadWizard(); loaded = true; blocked = false; status.textContent = response.warning || '';
    if (response.warning) status.focus();
}
cancelButton.addEventListener('click', () => { if (loaded && !busy) { display(saved); for (const field of processing.values()) field.input.value=field.saved; status.textContent = 'Unapplied changes discarded.'; } });
saveButton.addEventListener('click', () => void action(async () => {
    status.textContent = 'Saving provider settings…';
    const settings = { revision:saved.revision,transcription:draftProvider('transcription'),translation:draftProvider('translation') };
    const controls = Array.from(processing,([key,field])=>({key,value:field.input.value,valid:field.input.validity.valid,saved:field.saved}));
    let providerSaved = false;
    try {
        for (const input of controls) if (!input.valid || !input.value) throw Error('Enter a whole number within each Advanced processing range.');
        const response = await settingsRequest({ type: 'PROVIDERS_SAVE', settings });
        if (response?.error || !response?.revision) throw Error(response?.error || 'Save failed.');
        display(response); providerSaved = true;
        if (wizard) for (const {key,value,saved:original} of controls) {
            if (value === original) continue;
            const result = await settingsRequest({type:'PREFERENCES_SAVE',key,value});
            if (result?.error || typeof result?.value !== 'string') throw Error('Could not save Advanced processing settings.');
            const field = processing.get(key)!;
            field.saved = result.value; field.input.value = result.value;
        }
        status.textContent = response.warning || 'Saved. Active Runs keep their previous configuration.';
    } catch (error) {
        if (error instanceof SettingsTimeout || /changed elsewhere|settings changed/i.test(safeError(error))) blocked = true;
        report(Error((providerSaved ? 'AI settings saved; ' : '') + safeError(error)));
    }
},true));
document.getElementById('health')!.addEventListener('click', async () => {
    const check = document.getElementById('health') as HTMLButtonElement, output = document.getElementById('health-status')!;
    if (check.disabled) return; check.disabled = true; output.textContent = 'Checking helper connection…';
    try {
        const result = await settingsRequest({ type: 'PING' }); if (result?.status !== 'PONG') throw Error('Helper unavailable.');
        const missing = ['yt-dlp','ffmpeg','ffprobe','deno'].filter(name=>!result.tools?.[name]?.available);
        output.textContent = (missing.length ? 'Helper connected, but not ready. ' : 'Helper connected and ready. ') + 'Version ' + (result.version || 'unavailable') + '.\n' +
            ['yt-dlp','ffmpeg','ffprobe','deno'].map(name=>name + ': ' + (missing.includes(name) ? 'missing' : 'available')).join('\n') +
            (result.helperUpgradeRequired ? '\nThis older helper does not report Deno. Run the latest CueFlora Setup and Upgrade.' : missing.length ? '\nOpen CueFlora Setup and choose Repair, then check again.' : '\nAI-service compatibility has not been tested.');
        output.textContent += result.capabilities?.credentialProtection === 'windows-dpapi-v1' ? '\nWindows-protected key storage available.' : '\nSaved-key protection requires the latest Windows helper. Run CueFlora Setup and Upgrade. Caption-only and services without keys remain available.';
    } catch(error) { output.textContent = (/timed out/i.test(safeError(error)) ? 'Helper connection timed out. ' : 'Helper unavailable. ') + 'Run CueFlora Setup, select Chrome, and Install or Repair. Do not repair Substrata.'; }
    finally { check.disabled = false; }
});
function showStep() {
    for (const section of document.querySelectorAll<HTMLElement>('[data-step]')) section.hidden = Number(section.dataset.step) !== step;
    document.getElementById('setup-progress')!.textContent = complete ? 'Setup saved. You can revisit any step.' : `Step ${step} of 3`;
}
async function persistStep(next: number) {
    const result = await settingsRequest({ type: 'ONBOARDING_SAVE', step: next, complete });
    if (result?.error || result?.step !== next || typeof result.complete !== 'boolean') throw Error(result?.error || 'Could not save setup progress.');
    step = next; complete = result.complete; showStep();
    const heading = document.querySelector<HTMLElement>(`[data-step="${step}"] h2`); if (heading) { heading.tabIndex=-1; heading.focus(); }
}
async function loadWizard() {
    const result = await settingsRequest({ type: 'ONBOARDING_GET' }); if (result?.error) throw Error(result.error);
    step = result?.step || 1; complete = result?.complete === true;
    const prefs = await settingsRequest({ type: 'PREFERENCES_INIT', legacy: {} }); if (!prefs || prefs.error) throw Error('Could not load language preferences.');
    displayPreferences(prefs); showStep();
}
function displayPreferences(prefs:Record<string,string>) {
    for (const [key,field] of processing) { field.saved = prefs[key] || field.saved; field.input.value = field.saved; }
    for (const stage of ['transcription','translation']) {
        const select = document.getElementById(stage + '-language') as HTMLSelectElement;
        select.replaceChildren();
        for (const language of LANGUAGES) { if (!language.bcp47) continue; const option = document.createElement('option'); option.value = language.bcp47; option.textContent = language.name; select.append(option); }
        const fallback = stage === 'transcription' ? 'zh-CN' : 'en';
        const value = prefs['cueflora_' + stage + '_lang'];
        const code = value?.replace(/^(transcription|translation):/, '');
        if (code && code !== 'none' && /^[a-zA-Z0-9-]{1,40}$/.test(code) && !Array.from(select.options).some(option=>option.value===code)) {
            select.add(new Option('Saved language ('+code+')',code));
        }
        select.value = code || fallback;
        if (!select.value) select.value = fallback;
        const mode = document.getElementById(stage + '-mode') as HTMLSelectElement | null;
        if (mode) mode.value = value === 'none' ? 'off' : value ? (value.startsWith(stage + ':') ? 'ai' : 'caption') : providerConfigured(saved[stage as 'transcription'|'translation']) ? 'ai' : 'caption';
    }
}
for (const control of document.querySelectorAll<HTMLButtonElement>('[data-next]')) control.addEventListener('click', () => void action(async () => {
        if (step === 2 && control.dataset.next === '3') {
            if (hasDraft()) throw Error('Save your AI settings or Cancel edits before continuing. Blank stages can be postponed.');
        }
        await persistStep(Number(control.dataset.next)); status.textContent = '';
},true));
document.getElementById('finish')?.addEventListener('click', () => void action(async () => {
    const languages = {} as OnboardingFinishMessage['languages'];
    for (const stage of ['transcription','translation'] as const) {
        const code = (document.getElementById(stage+'-language') as HTMLSelectElement).value;
        const mode = (document.getElementById(stage+'-mode') as HTMLSelectElement | null)?.value || (providerConfigured(saved[stage]) ? 'ai' : 'caption');
        if (!code) throw Error('Choose an available language for each stage.');
        languages[stage] = mode === 'off' ? 'none' : mode === 'ai' ? stage+':'+code : code;
    }
    const message:OnboardingFinishMessage = {type:'ONBOARDING_FINISH',revision:saved.revision,languages};
    const result = await settingsRequest<OnboardingFinishResult>(message as unknown as Record<string,unknown>);
    if (result?.error) { if (result.reason === 'revision' || result.reason === 'progress') blocked = true; throw Error(result.error); }
    if (result?.languagesSaved !== true || result.step !== 3 || result.complete !== true) { blocked = true; throw Error('Could not verify setup completion. Reload saved state.'); }
    step=3; complete=true; showStep(); status.textContent='Setup saved. On YouTube, open the flower button and press Run when you choose. No subtitles were generated.';
},true));
reload.addEventListener('click', () => void action(async () => {
    if (!loaded) { await load(); return; }
    const inputs = Array.from(document.querySelectorAll<HTMLInputElement | HTMLSelectElement>('#providers input,[data-language]'),input=>({input,value:input.value,checked:'checked' in input ? input.checked : undefined}));
    const result = await settingsRequest({type:'SETTINGS_RECONCILE'});
    if (result?.error || !result?.providers || !result?.preferences || !result?.onboarding) throw Error('Could not reload saved state. Edits are retained; retry loading.');
    display(result.providers); if (wizard) displayPreferences(result.preferences);
    step=result.onboarding.step; complete=result.onboarding.complete;
    for (const {input,value,checked} of inputs) { input.value=value; if (checked !== undefined && input instanceof HTMLInputElement) input.checked=checked; }
    blocked=false; if (wizard) showStep(); status.textContent=result.providers.warning || 'Saved state reloaded; your edits were kept. Review them before Save or Finish, or Cancel to restore saved AI settings.';
}));
retryMigration.addEventListener('click',()=>void action(async()=>{
    const draft=Array.from(form.querySelectorAll<HTMLInputElement>('input'),input=>({input,value:input.value,checked:input.checked}));
    const result=await settingsRequest({type:'PROVIDERS_MIGRATE'});
    if(result?.error || !result?.transcription) throw Error('Could not retry protected migration. Drafts are retained.');
    display(result);
    for(const item of draft){item.input.value=item.value; item.input.checked=item.checked;}
    status.textContent=result.warning || 'Protected key migration verified; your edits were kept. Save or Cancel them explicitly.';
},true));
void action(load);
