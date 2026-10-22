import {settingsRequest} from '../../utils/settingsRequest';
import {safeFailure,failureMessage} from '../../utils/failureDiagnostics';
class UpdateTaskFailure extends Error {}

/** No polling until a user starts a bounded update task. No automatic install. */
export function createUpdates(section:HTMLElement,canInstall:()=>boolean=()=>true) {
    const heading=document.createElement('h2');heading.textContent='Updates';
    const status=document.createElement('p');status.setAttribute('role','status');status.tabIndex=-1;
    const version=browser.runtime.getManifest()?.version || 'unavailable';
    const explanation=document.createElement('p');explanation.textContent='Extension '+version+'. Check published stable releases from TearsOfTheDawn/CueFlora. Downloads are verified; the installer is unsigned. Initial Chrome Load unpacked and the first 0.1.13 upgrade are manual. No update is installed silently.';
    let selected:{selectionRef:string;version:string;size:number}|null=null,taskId:string|null=null,ready=false,launched=false,busy=false,installed=false;
    let timer:ReturnType<typeof setTimeout>|undefined,sequence=0;
    const showError=(error:unknown)=>{busy=taskId!==null;status.textContent=taskId
        ? 'Update status unavailable. The task may still be running. Cancel the current task before trying again; nothing was installed automatically.'
        : error instanceof UpdateTaskFailure?error.message:'Update unavailable or verification failed. Retry explicitly, or download the matching Setup from GitHub. Older helpers need a manual Upgrade. Nothing was installed automatically.';status.focus();sync();};
    const make=(text:string,work:()=>Promise<void>)=>{const button=document.createElement('button');button.type='button';button.textContent=text;button.addEventListener('click',()=>void work().catch(showError));return button;};
    const sync=()=>{check.disabled=busy;download.disabled=busy||!selected||ready;install.disabled=busy||!ready;cancel.disabled=!taskId;recheck.disabled=busy;restart.disabled=busy||!installed;};
    async function poll(id:string,expected:number,operation:'check'|'download'){
        const result=await settingsRequest({type:'TASK_STATUS',taskId:id});if(sequence!==expected||taskId!==id)return;
        if(result.error||result.status==='error'){taskId=null;busy=false;sync();throw new UpdateTaskFailure(failureMessage(safeFailure(result.failure)||{stage:operation==='check'?'update-check':'update-download',code:'unknown'}));}
        if(result.status==='complete'){
            taskId=null;busy=false;
            if(operation==='check'){
                if(result.result.available){selected=result.result;status.textContent='CueFlora '+selected!.version+' is available ('+Math.ceil(selected!.size/1024/1024)+' MiB). Download it, then confirm installation.';}
                else status.textContent='No newer compatible stable release is available. Helper '+result.result.currentVersion+'; extension '+version+'.';
            }else{ready=true;status.textContent='Download verified. Click Install update to open Setup, then confirm Install / Upgrade there. Windows security warnings are not bypassed.';}
            sync();return;
        }
        status.textContent=operation==='download'?'Downloading update'+(typeof result.percent==='number'?' — '+result.percent+'%':'…'):'Checking published stable releases…';
        timer=setTimeout(()=>void poll(id,expected,operation).catch(error=>{
            if(sequence===expected&&taskId===id)showError(error);
        }),800);
    }
    async function start(operation:'check'|'download'){
        if(busy)return;busy=true;if(operation==='check'){selected=null;ready=false;installed=false;launched=false;}sync();
        const result=await settingsRequest(operation==='check'?{type:'UPDATES_CHECK'}:{type:'UPDATES_DOWNLOAD',selectionRef:selected!.selectionRef});
        if(result.error||!result.taskId)throw Error('Update startup failed');taskId=result.taskId;sync();await poll(taskId!,++sequence,operation);
    }
    const check=make('Check for updates',()=>start('check'));
    const download=make('Download update',()=>start('download'));
    const install=make('Install update',async()=>{
        if(!canInstall()){status.textContent='Save or Cancel your settings edits and finish account tasks before installing.';status.focus();return;}
        if(!ready||!selected||!window.confirm('Open the verified, unsigned CueFlora Setup for '+selected.version+'? Finish all Runs first. You must confirm Install / Upgrade in Setup.'))return;
        busy=true;sync();const result=await settingsRequest({type:'UPDATES_INSTALL',selectionRef:selected.selectionRef,confirmation:'install'});
        if(result.error||!result.launched)throw Error('Setup launch failed');busy=false;launched=true;status.textContent='Setup opened. Confirm Install / Upgrade. When it finishes, click Check installation below.';sync();
    });
    const cancel=make('Cancel download/check',async()=>{
        if(!taskId)return;const id=taskId;++sequence;if(timer)clearTimeout(timer);await settingsRequest({type:'TASK_CANCEL',taskId:id});taskId=null;busy=false;status.textContent='Update task cancelled. No installation occurred.';sync();
    });
    const recheck=make('Check helper / installation versions',async()=>{
        const result=await settingsRequest({type:'UPDATES_STATUS'});
        if(result.error)throw Error('Status unavailable');
        const matched=result.managed===true&&result.installedVersion===result.extensionVersion;
        installed=!!selected&&matched&&result.installedVersion===selected.version;
        status.textContent='Loaded extension '+version+'; installed helper '+(result.installedVersion||'unavailable')+'; managed extension '+(result.extensionVersion||'not managed')+'. '+
            (installed?'Matching update installed. Restart CueFlora, then reload open YouTube tabs.':matched&&result.installedVersion===version?'Versions match.':!result.managed?'A one-time manual Setup/folder adoption is required.':'Versions differ. Finish Setup and use Chrome Reload.');sync();
    });
    const restart=make('Restart CueFlora',async()=>{
        if(!canInstall()){status.textContent='Save or Cancel your settings edits before restarting CueFlora.';status.focus();return;}
        if(!installed||!selected||!window.confirm('Restart CueFlora now? Save/Cancel any appearance edits in other tabs first. Afterward, reload your open YouTube tabs.'))return;
        const result=await settingsRequest({type:'RESTART_CUEFLORA',version:selected.version,confirmation:'restart'});if(result?.error)throw Error('Restart refused');
    });
    const fallback=document.createElement('p');fallback.textContent='Manual fallback: open chrome://extensions, click CueFlora Reload, then reload YouTube. Keep the Setup-managed extension folder in place. If Windows blocks Setup, review the warning; never disable security software.';
    section.append(heading,explanation,check,download,install,cancel,recheck,restart,status,fallback);sync();
    window.addEventListener('pagehide',()=>{if(timer)clearTimeout(timer);if(taskId)void browser.runtime.sendMessage({type:'TASK_CANCEL',taskId});});
}
