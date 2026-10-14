/** Local visual QA harness: real UI and renderer, no native/model requests. */
import { createUI, togglePanel } from '../entrypoints/youtube.content/ui';
import { renderOverlay } from '../entrypoints/youtube.content/render';
import '../entrypoints/youtube.content/style.css';
import { createPreferencesService } from '../utils/preferences';
const previewData: Record<string,unknown> = {};
const previewPreferences = createPreferencesService({ get: async () => previewData, set: async items => { Object.assign(previewData,items); } });
Object.assign(globalThis,{browser:{storage:{local:{get:async()=>({}),set:async()=>{}}},runtime:{sendMessage:async(message: {type:string;legacy:Record<string,unknown>;key:string;value:string})=>{
    if(message.type==='PREFERENCES_INIT') return previewPreferences.initialize(message.legacy);
    if(message.type==='PREFERENCES_SAVE') return {value:await previewPreferences.save(message.key,message.value)};
    throw Error('Inference disabled in UI preview');
}}}});
await createUI(); togglePanel();
const cue={startMs:0,endMs:100000,text:'看得更清楚，学得更轻松。'};
setInterval(()=>renderOverlay(cue,{...cue,text:'A clearer view, in both languages.'},0),100);
document.querySelectorAll<HTMLButtonElement>('[data-size]').forEach(button=>button.onclick=()=>{
    const player=document.getElementById('movie_player')!; const [width,height]=button.dataset.size!.split('x'); player.style.width=width+'px';player.style.height=height+'px';
});
