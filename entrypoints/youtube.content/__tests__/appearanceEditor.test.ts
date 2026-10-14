vi.mock('../../../utils/preferenceClient', () => ({
    preferences: { getItem: (key: string) => window.localStorage.getItem(key), setItem: (key: string, value: string) => window.localStorage.setItem(key,value) },
    initializePreferences: async () => {},
    savePreference: vi.fn(async (key: string, value: string) => window.localStorage.setItem(key,value)),
}));
import { beforeEach, afterEach, describe, it, expect, vi } from 'vitest';
import { mountAppearanceEditor } from '../appearanceEditor';
import { savePreference } from '../../../utils/preferenceClient';
import { APPEARANCE_KEY, defaults, getEffectiveAppearance } from '../../../utils/appearance';
describe('appearance draft lifecycle',()=>{
    let cleanup:()=>void; let panel:HTMLElement; let player:HTMLElement;
    const click=(id:string)=>(document.getElementById(id) as HTMLElement).click();
    const change=()=>{const input=document.getElementById('cueflora-appearance-sourceSize') as HTMLInputElement;input.value='35';input.dispatchEvent(new Event('input'));};
    beforeEach(()=>{
        localStorage.clear();localStorage.setItem(APPEARANCE_KEY,JSON.stringify(defaults()));
        document.body.innerHTML='<div id="movie_player"><div id="cueflora-panel"><button id="cueflora-nav-home"></button><button id="cueflora-nav-settings"></button><div id="cueflora-view-home" class="cueflora-view active"></div></div><div id="cueflora-overlay"><div class="cueflora-line-container">Original cue</div></div></div>';
        panel=document.getElementById('cueflora-panel')!; player=document.getElementById('movie_player')!;
        Object.defineProperty(player,'clientHeight',{value:720,configurable:true});
        cleanup=mountAppearanceEditor(panel,player,document.getElementById('cueflora-overlay')!);
    });
    afterEach(()=>{cleanup();vi.restoreAllMocks();vi.unstubAllGlobals();});
    it('previews without changing playback text or persisted settings and cancels',()=>{
        click('cueflora-nav-appearance');change();expect(getEffectiveAppearance()?.sourceSize).toBe(35);
        expect(JSON.parse(localStorage.getItem(APPEARANCE_KEY)!).sourceSize).toBe(22);
        expect(document.getElementById('cueflora-overlay')!.textContent).toBe('Original cue');
        click('cueflora-appearance-cancel');expect(getEffectiveAppearance()?.sourceSize).toBe(22);
    });
    it('Apply persists and later cancellation restores the new rollback point',async ()=>{
        click('cueflora-nav-appearance');change();click('cueflora-appearance-apply');await vi.waitFor(()=>expect(document.getElementById('cueflora-appearance-message')!.textContent).toBe('Appearance saved'));click('cueflora-appearance-reset');click('cueflora-appearance-cancel');
        expect(getEffectiveAppearance()?.sourceSize).toBe(35);expect(JSON.parse(localStorage.getItem(APPEARANCE_KEY)!).sourceSize).toBe(35);
    });
    it('close discards draft and cleanup drops effective session state',()=>{
        click('cueflora-nav-appearance');change();panel.dispatchEvent(new Event('cueflora-panel-close'));
        expect(getEffectiveAppearance()?.sourceSize).toBe(22);cleanup();expect(getEffectiveAppearance()).toBeNull();
    });
    it('save failure retains the draft and reports failure',async ()=>{
        click('cueflora-nav-appearance');change();vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw Error('quota');});click('cueflora-appearance-apply');
        await vi.waitFor(()=>expect(document.getElementById('cueflora-appearance-message')!.textContent).toContain('Could not save'));expect(getEffectiveAppearance()?.sourceSize).toBe(35);click('cueflora-appearance-cancel');expect(getEffectiveAppearance()?.sourceSize).toBe(22);
    });
    it('does not overwrite newer edits when a pending Apply finishes', async () => {
        let finish!: () => void;
        vi.mocked(savePreference).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
        click('cueflora-nav-appearance'); change(); click('cueflora-appearance-apply');
        expect((document.getElementById('cueflora-appearance-apply') as HTMLButtonElement).disabled).toBe(true);
        const input = document.getElementById('cueflora-appearance-sourceSize') as HTMLInputElement;
        input.value = '40'; input.dispatchEvent(new Event('input'));
        finish();
        await vi.waitFor(() => expect(document.getElementById('cueflora-appearance-message')!.textContent).toContain('not yet applied'));
        expect(getEffectiveAppearance()?.sourceSize).toBe(40);
        click('cueflora-appearance-cancel'); expect(getEffectiveAppearance()?.sourceSize).toBe(35);
    });
    it('does not recreate a cancelled draft when an accepted Apply finishes', async () => {
        let finish!: () => void;
        vi.mocked(savePreference).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
        click('cueflora-nav-appearance'); change(); click('cueflora-appearance-apply'); click('cueflora-appearance-cancel');
        finish();
        await vi.waitFor(() => expect(getEffectiveAppearance()?.sourceSize).toBe(35));
        expect(document.getElementById('cueflora-view-appearance')!.classList.contains('active')).toBe(false);
        expect((document.querySelector('.cueflora-appearance-drag') as HTMLElement).hidden).toBe(true);
    });
    it('does not persist migration while dimensions are unavailable',()=>{
        cleanup();localStorage.clear();Object.defineProperty(player,'clientHeight',{value:0});
        cleanup=mountAppearanceEditor(panel,player,document.getElementById('cueflora-overlay')!);
        expect(localStorage.getItem(APPEARANCE_KEY)).toBeNull();
    });
    it('waits two stable layout frames then migrates once',async ()=>{
        cleanup(); localStorage.clear(); localStorage.setItem('cueflora_overlay_bottom','80');
        const frames: FrameRequestCallback[]=[];
        vi.stubGlobal('requestAnimationFrame',(callback:FrameRequestCallback)=>{frames.push(callback);return frames.length;});
        Object.defineProperty(player,'clientWidth',{value:960,configurable:true});
        vi.spyOn(player,'getClientRects').mockReturnValue([new DOMRect(0,0,960,720)] as unknown as DOMRectList);
        const write=vi.spyOn(Storage.prototype,'setItem');
        cleanup=mountAppearanceEditor(panel,player,document.getElementById('cueflora-overlay')!);
        frames.shift()!(0);expect(localStorage.getItem(APPEARANCE_KEY)).toBeNull();
        frames.shift()!(16);await vi.waitFor(()=>expect(localStorage.getItem(APPEARANCE_KEY)).not.toBeNull());expect(JSON.parse(localStorage.getItem(APPEARANCE_KEY)!).position).toBeCloseTo(44/660*100);
        expect(write.mock.calls.filter(([key])=>key===APPEARANCE_KEY)).toHaveLength(1);
    });
});
