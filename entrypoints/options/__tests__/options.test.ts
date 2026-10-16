import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fakeBrowser } from 'wxt/testing/fake-browser';
import { providerDefaults } from '../../../utils/providers';

describe('production options Save/Cancel interactions', () => {
    const send = vi.fn();
    const button = (id: string) => document.getElementById(id) as HTMLButtonElement;
    const field = (name: string) => document.querySelector(`[name="${name}"]`) as HTMLInputElement;
    const settings = () => { const value = { ...providerDefaults(), revision: 'saved' }; for (const stage of ['transcription','translation'] as const) Object.assign(value[stage], { baseUrl: 'https://fixture.example/v1', model: 'fixture' }); return value; };
    beforeEach(() => {
        vi.resetModules(); fakeBrowser.reset(); send.mockReset();
        vi.spyOn(fakeBrowser.runtime, 'sendMessage').mockImplementation(send);
        document.body.innerHTML = '<form id="providers"></form><p id="status"></p><button id="save"></button><button id="cancel"></button><button id="health"></button><p id="health-status"></p>';
    });
    const open = async () => { await import('../main'); await vi.waitFor(() => expect(button('save').disabled).toBe(false)); };
    it('does not allow saving before loading and Cancel never writes', async () => {
        let resolve!: (value: unknown) => void;
        send.mockReturnValueOnce(new Promise(done => { resolve = done; }));
        await import('../main');
        expect(button('save').disabled).toBe(true);
        button('save').click(); expect(send).toHaveBeenCalledTimes(1);
        resolve(settings());
        await vi.waitFor(() => expect(button('save').disabled).toBe(false));
        const original = field('translation.model').value;
        field('translation.model').value = 'unsaved'; button('cancel').click();
        expect(field('translation.model').value).toBe(original);
        expect(send).toHaveBeenCalledTimes(1);
    });
    it('locks pending Save and updates the rollback point only after persistence', async () => {
        send.mockResolvedValueOnce(settings()); await open();
        let resolve!: (value: unknown) => void;
        send.mockReturnValueOnce(new Promise(done => { resolve = done; }));
        field('translation.model').value = 'new-model'; button('save').click();
        const submitted = send.mock.calls[1][0].settings;
        expect(submitted.translation.model).toBe('new-model');
        expect(field('translation.model').disabled).toBe(true);
        expect(button('cancel').disabled).toBe(true);
        button('save').click(); expect(send).toHaveBeenCalledTimes(2);
        resolve({ ...submitted, revision: 'new' });
        await vi.waitFor(() => expect(button('save').disabled).toBe(false));
        field('translation.model').value = 'another-draft'; button('cancel').click();
        expect(field('translation.model').value).toBe('new-model');
    });
    it('retains a failed-save draft and restores the original on Cancel', async () => {
        send.mockResolvedValueOnce(settings()); await open();
        const original = field('translation.model').value;
        send.mockResolvedValueOnce({ error: 'Persistence failed' });
        field('translation.model').value = 'draft'; button('save').click();
        await vi.waitFor(() => expect(document.getElementById('status')!.textContent).toBe('Persistence failed'));
        expect(field('translation.model').value).toBe('draft');
        button('cancel').click(); expect(field('translation.model').value).toBe(original);
    });
    it('performs only user-triggered health requests and distinguishes missing tools', async () => {
        send.mockResolvedValueOnce(settings()); await open();
        expect(send).toHaveBeenCalledTimes(1);
        send.mockResolvedValueOnce({ status: 'PONG', version: '0.1.0', tools: { 'yt-dlp': { available: true }, ffmpeg: { available: false }, ffprobe: { available: true } } });
        button('health').click();
        await vi.waitFor(() => expect(button('health').disabled).toBe(false));
        expect(send.mock.calls[1][0]).toEqual({ type: 'PING' });
        expect(document.getElementById('health-status')!.textContent).toContain('ffmpeg: missing');
    });
    it('offers Upgrade for an older helper rather than reporting it ready', async () => {
        send.mockResolvedValueOnce(settings()); await open();
        send.mockResolvedValueOnce({status:'PONG',version:'0.1.0',helperUpgradeRequired:true,tools:{'yt-dlp':{available:true},ffmpeg:{available:true},ffprobe:{available:true},deno:{available:false}}});
        button('health').click();
        await vi.waitFor(()=>expect(button('health').disabled).toBe(false));
        expect(document.getElementById('health-status')!.textContent).toContain('latest CueFlora Setup and Upgrade');
        expect(document.getElementById('health-status')!.textContent).not.toContain('connected and ready');
    });
    it('never fills saved keys, and snapshots explicit replacement/removal/reuse actions',async()=>{
        const value=settings(); value.translation.keySaved=true; value.translation.apiKey='synthetic-return-must-not-fill';
        send.mockResolvedValueOnce(value); await open();
        expect(field('translation.apiKey').value).toBe(''); expect(document.getElementById('translation-key-status')!.textContent).toContain('API key saved');
        field('translation.apiKey').value='synthetic-replacement'; field('translation.apiKey').dispatchEvent(new Event('input'));
        field('translation.reuseKey').checked=true;
        send.mockResolvedValueOnce({error:'protection failed'}); button('save').click();
        await vi.waitFor(()=>expect(button('save').disabled).toBe(false));
        expect(send.mock.calls.at(-1)![0].settings.translation).toMatchObject({apiKey:'synthetic-replacement',keyAction:'replace',reuseKey:true});
        expect(field('translation.apiKey').value).toBe('synthetic-replacement'); button('cancel').click();
        expect(field('translation.apiKey').value).toBe(''); expect(field('translation.reuseKey').checked).toBe(false);
        (document.querySelector('[name="translation.keyAction"][value="remove"]') as HTMLInputElement).click();
        send.mockResolvedValueOnce({error:'quota'}); button('save').click();
        await vi.waitFor(()=>expect(button('save').disabled).toBe(false));
        expect(send.mock.calls.at(-1)![0].settings.translation).toMatchObject({apiKey:'',keyAction:'remove'});
    });
    it('shows migration failures and permits retry without false success',async()=>{
        const value=settings(); value.warning='Stored API keys need protected migration. Reload to retry.'; value.translation.migrationRequired=true;
        send.mockResolvedValueOnce(value); await open();
        expect(document.getElementById('status')!.textContent).toContain('migration'); expect(document.getElementById('translation-key-status')!.textContent).toContain('incomplete');
        expect(field('translation.apiKey').value).toBe(''); expect(document.activeElement).toBe(document.getElementById('status'));
    });
});
