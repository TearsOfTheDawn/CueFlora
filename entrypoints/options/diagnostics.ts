import {settingsRequest} from '../../utils/settingsRequest';
import {publicDebugReport} from '../../utils/failureDiagnostics';

/** Only user-triggered, metadata-only health/report requests. No inference or storage dump. */
export function createDiagnostics(section:HTMLElement) {
    section.id='diagnostics';
    const heading=document.createElement('h2');heading.textContent='Debugging & support';
    const help=document.createElement('p');help.textContent='After a failure, collect a report before reloading CueFlora. It includes versions, tool health and up to 20 recent failure codes—not keys, service addresses, models, videos or subtitle text. History survives background-worker sleep in browser-session memory, and clears on extension reload/update or browser restart.';
    const status=document.createElement('p');status.setAttribute('role','status');status.tabIndex=-1;
    const output=document.createElement('textarea');output.readOnly=true;output.hidden=true;output.rows=12;output.setAttribute('aria-label','Privacy-safe debug report');
    const collect=document.createElement('button');collect.type='button';collect.textContent='Collect debug report';
    const copy=document.createElement('button');copy.type='button';copy.textContent='Copy report';copy.disabled=true;
    collect.addEventListener('click',()=>void(async()=>{
        collect.disabled=true;copy.disabled=true;output.value='';output.hidden=true;status.textContent='Checking helper and collecting safe failure codes…';
        try{
            const result=publicDebugReport(await settingsRequest({type:'DIAGNOSTICS_GET'}));
            output.value=JSON.stringify(result,null,2);output.hidden=false;copy.disabled=false;status.textContent=(result.historyIncomplete?'Some failure history could not be retained. ':'')+'Report ready. Review it, then copy it to share with support. No AI request was made.';
        }catch{status.textContent='Could not collect the debug report. Check helper connection and retry.';status.focus();}
        finally{collect.disabled=false;}
    })());
    copy.addEventListener('click',()=>void(async()=>{
        try{await navigator.clipboard.writeText(output.value);status.textContent='Debug report copied.';}
        catch{output.focus();output.select();status.textContent='Automatic copy is unavailable. Copy the selected report manually.';}
    })());
    section.append(heading,help,collect,copy,status,output);
}
