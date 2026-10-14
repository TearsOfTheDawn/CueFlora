import { preferences as preferenceStorage, savePreference } from '../../utils/preferenceClient';
import { APPEARANCE_KEY, appearanceTop, defaults, loadAppearance, migrateAppearance, preset, ranges,
    setEffectiveAppearance, styleAppearance, validateAppearance, type SubtitleAppearanceSettings } from '../../utils/appearance';
import { createRubyNodes } from '../../utils/ruby';

/** Owns draft UI and geometry only; never imports workflow or cue state. */
export function mountAppearanceEditor(panel: HTMLElement, player: HTMLElement, overlay: HTMLElement): () => void {
    let saved = loadAppearance(preferenceStorage); let draft: SubtitleAppearanceSettings | null = null;
    let destroyed = false; let frame = 0; let lastHeight = 0; let lastWidth = 0;
    let saving = false; let migrating = false; let editRevision = 0;
    const view = document.createElement('div'); view.id = 'cueflora-view-appearance'; view.className = 'cueflora-view';
    view.innerHTML = `<div class="cueflora-appearance-scroll"><h2>Appearance</h2><label class="cueflora-appearance-field">Preset<select id="cueflora-appearance-preset">
        <option>Custom</option><option>Classic</option><option>Clean outline</option><option>High contrast</option><option>Language learning</option>
        </select></label><div class="cueflora-appearance-preview-label">Preview sample — changes are not saved until Apply</div>
        <div class="cueflora-appearance-preview"><div class="cueflora-line-container"><div class="cueflora-primary" lang="zh-CN"></div><div class="cueflora-secondary" lang="en">A clearer view, in both languages.</div></div></div><div class="cueflora-appearance-groups"></div></div>
        <div class="cueflora-appearance-footer"><div id="cueflora-appearance-message" role="status" aria-live="polite"></div><div class="cueflora-appearance-actions"><button type="button" id="cueflora-appearance-reset">Reset</button><button type="button" id="cueflora-appearance-cancel">Cancel</button><button type="button" id="cueflora-appearance-apply">Apply</button></div></div>`;
    panel.append(view);
    const nav = document.createElement('button'); nav.type='button'; nav.id='cueflora-nav-appearance'; nav.textContent='Appearance ›';
    panel.querySelector('#cueflora-view-home')!.append(nav);
    const groups = view.querySelector('.cueflora-appearance-groups')!;
    const controls = new Map<keyof SubtitleAppearanceSettings, HTMLInputElement|HTMLSelectElement>();
    const buildGroup = (title:string, fields: [keyof SubtitleAppearanceSettings,string,string?][]) => {
        const group = document.createElement('details'); const summary=document.createElement('summary'); summary.textContent=title; group.append(summary);
        for (const [key,label,options] of fields) {
            const row=document.createElement('label'); row.className='cueflora-appearance-field'; const caption=document.createElement('span'); caption.textContent=label; row.append(caption);
            const input=options?document.createElement('select'):document.createElement('input'); input.id='cueflora-appearance-'+key;
            if (input instanceof HTMLSelectElement) for (const option of options!.split('|')) { const [value,text]=option.split(':'); input.add(new Option(text||value,value)); }
            else if (typeof defaults()[key] === 'boolean') input.type='checkbox';
            else if (ranges[key]) { input.type='range'; const [min,max,step]=ranges[key]!; input.min=String(min); input.max=String(max); input.step=String(step); }
            else input.type='color';
            const output=document.createElement('output'); output.htmlFor=input.id;
            row.append(input,output); group.append(row); controls.set(key,input);
            input.addEventListener('input',()=>{
                if (!draft) return;
                editRevision++;
                Object.assign(draft,{[key]:input instanceof HTMLInputElement && input.type==='checkbox'?input.checked:ranges[key]?Number(input.value):input.value});
                (view.querySelector('#cueflora-appearance-preset') as HTMLSelectElement).value='Custom'; update();
            });
        }
        groups.append(group);
    };
    const fontOptions='sans:Sans-serif|serif:Serif|mono:Monospace';
    buildGroup('Source text', [['sourceFont','Font',fontOptions],['sourceSize','Size'],['sourceBold','Bold'],['sourceColor','Color']]);
    buildGroup('Translation text', [['translationFont','Font',fontOptions],['translationSize','Size'],['translationBold','Bold'],['translationColor','Color']]);
    buildGroup('Readability & background', [['outline','Outline width'],['outlineColor','Outline color'],['shadow','Shadow','off:Off|soft:Soft|strong:Strong'],['background','Background'],['opacity','Opacity'],['paddingX','Horizontal padding'],['paddingY','Vertical padding'],['radius','Corner radius']]);
    buildGroup('Layout & position', [['order','Order','source:Source first|translation:Translation first'],['align','Alignment','center:Centered|left:Left'],['width','Maximum width'],['lineHeight','Line height'],['gap','Track gap'],['position','Position (bottom → top)']]);
    buildGroup('Learning aids', [['highlight','Highlight spoken word'],['highlightColor','Highlight color'],['pinyin','Show Chinese pinyin'],['pinyinSize','Pinyin size']]);
    const handle=document.createElement('button'); handle.type='button'; handle.className='cueflora-appearance-drag'; handle.textContent='↕ Move subtitles'; handle.hidden=true;
    handle.setAttribute('aria-label','Drag to move subtitles; use the Position slider for keyboard adjustment'); player.append(handle);
    const message=view.querySelector('#cueflora-appearance-message') as HTMLElement;
    const apply=view.querySelector('#cueflora-appearance-apply') as HTMLButtonElement;
    const preview=view.querySelector('.cueflora-appearance-preview') as HTMLElement;
    const update = () => {
        const current=draft||saved;
        setEffectiveAppearance(saved ? current : null);
        if (!current) { apply.disabled=true; message.textContent='Waiting for player layout'; return; }
        const height=player.clientHeight;
        styleAppearance(preview,current,height);
        if (saved) styleAppearance(overlay,current,height);
        // Preview is presentation-only, never a synthetic playback cue.
        preview.querySelector('.cueflora-primary')!.replaceChildren(createRubyNodes('看得更清楚，学得更轻松。','zh'));
        const block=overlay.querySelector('.cueflora-line-container') as HTMLElement|null;
        if (saved) {
            overlay.style.top=`${appearanceTop(height,block?.getBoundingClientRect().height||0,current.position)}px`;
            overlay.style.bottom='auto';
        }
        handle.style.top=`${Math.max(12,parseFloat(overlay.style.top)-30)}px`;
        for (const [key,input] of controls) {
            if (input instanceof HTMLInputElement && input.type==='checkbox') input.checked=Boolean(current[key]); else input.value=String(current[key]);
            input.parentElement!.querySelector('output')!.textContent=ranges[key]?String(Math.round(Number(current[key])*100)/100):'';
        }
        apply.disabled=!saved || saving;
    };
    const home = () => {
        view.classList.remove('active'); panel.querySelector('#cueflora-view-home')!.classList.add('active');
        (panel.querySelector('#cueflora-nav-home') as HTMLElement).style.display='none';
        (panel.querySelector('#cueflora-nav-settings') as HTMLElement).style.display='inline';
    };
    const cancel = () => { editRevision++; draft=null; dragY=null; handle.hidden=true; update(); home(); nav.focus(); };
    nav.addEventListener('click',()=>{
        editRevision++;
        draft={...(saved||migrateAppearance(preferenceStorage,player.clientHeight||720))};
        (view.querySelector('#cueflora-appearance-preset') as HTMLSelectElement).value='Custom';
        panel.querySelectorAll('.cueflora-view').forEach(el=>el.classList.remove('active')); view.classList.add('active');
        (panel.querySelector('#cueflora-nav-home') as HTMLElement).style.display='inline';
        (panel.querySelector('#cueflora-nav-settings') as HTMLElement).style.display='none';
        handle.hidden=false; message.textContent=saved?'':'Waiting for player layout'; update();
        (view.querySelector('#cueflora-appearance-preset') as HTMLElement).focus();
    });
    view.querySelector('#cueflora-appearance-preset')!.addEventListener('change',e=>{ if(draft && (e.target as HTMLSelectElement).value!=='Custom') { editRevision++; draft=preset((e.target as HTMLSelectElement).value,draft); update(); } });
    view.querySelector('#cueflora-appearance-reset')!.addEventListener('click',()=>{ if(draft) { editRevision++; draft=preset('Classic',draft); (view.querySelector('#cueflora-appearance-preset') as HTMLSelectElement).value='Classic'; update(); } });
    view.querySelector('#cueflora-appearance-cancel')!.addEventListener('click',cancel);
    apply.addEventListener('click',async ()=>{
        if(!draft||!saved||saving) return;
        const revision = editRevision;
        const next = validateAppearance(draft);
        saving = true; apply.disabled = true; message.textContent = 'Saving appearance…';
        try {
            await savePreference(APPEARANCE_KEY,JSON.stringify(next));
            if(destroyed) return;
            saved=next;
            if (draft && revision === editRevision) { draft={...next}; message.textContent='Appearance saved'; }
            else if (draft) message.textContent='Previous changes saved. New preview changes are not yet applied.';
        }
        catch { if (!destroyed) message.textContent='Could not save appearance. Retry or Cancel.'; }
        finally { saving=false; if (!destroyed) update(); }
    });
    const onBack=()=>{ if(draft) cancel(); };
    panel.querySelector('#cueflora-nav-home')!.addEventListener('click',onBack);
    const onClose=()=>{ if(draft) cancel(); };
    panel.addEventListener('cueflora-panel-close',onClose);
    let dragY:number|null=null; let dragPosition=0;
    handle.addEventListener('pointerdown',e=>{ if(!draft) return; e.preventDefault(); e.stopPropagation(); dragY=e.clientY; dragPosition=draft.position; handle.setPointerCapture(e.pointerId); });
    handle.addEventListener('pointermove',e=>{ if(dragY===null||!draft) return; editRevision++; draft.position=Math.max(0,Math.min(100,dragPosition+(dragY-e.clientY)/(player.clientHeight-60)*100)); update(); });
    handle.addEventListener('pointerup',()=>{dragY=null;}); handle.addEventListener('pointercancel',()=>{dragY=null;});
    handle.addEventListener('click',e=>e.stopPropagation());
    const measure=async ()=>{
        frame=0; if(destroyed || migrating) return;
        const height=player.clientHeight,width=player.clientWidth;
        if(!saved && player.isConnected && height>60 && width>0 && player.getClientRects().length && getComputedStyle(player).visibility !== 'hidden') {
            if(height===lastHeight && width===lastWidth) {
                const migrated=migrateAppearance(preferenceStorage,height);
                migrating = true;
                try { await savePreference(APPEARANCE_KEY,JSON.stringify(migrated)); if(destroyed) return; saved=migrated; if(draft) draft.position=migrated.position; message.textContent=''; }
                catch { message.textContent='Could not save initial appearance settings.'; }
                finally { migrating = false; }
            } else { lastHeight=height; lastWidth=width; frame=requestAnimationFrame(measure); }
        }
        update();
    };
    const resize=typeof ResizeObserver==='undefined'?null:new ResizeObserver(()=>{if(!frame) frame=requestAnimationFrame(measure);});
    resize?.observe(player); resize?.observe(overlay);
    frame=requestAnimationFrame(measure); update();
    return ()=>{ destroyed=true; cancelAnimationFrame(frame); resize?.disconnect(); draft=null; setEffectiveAppearance(null); handle.remove(); view.remove(); nav.remove(); panel.querySelector('#cueflora-nav-home')?.removeEventListener('click',onBack); panel.removeEventListener('cueflora-panel-close',onClose); };
}
