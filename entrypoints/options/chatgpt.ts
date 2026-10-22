import { accountRequest as settingsRequest } from '../../utils/settingsRequest';
import type { Provider } from '../../utils/providers';

export function createChatGPTControls(section:HTMLElement, changed:()=>void,activity:(busy:boolean)=>void=()=>{}) {
    const modeLabel=document.createElement('label');modeLabel.textContent='Translation connection';
    const mode=document.createElement('select');mode.name='translation.backend';
    for(const [value,text] of [['','Choose a connection (optional)'],['api','Your existing AI service'],['chatgpt','Use your ChatGPT plan']]){
        const option=document.createElement('option');option.value=value;option.textContent=text;mode.append(option);
    }
    modeLabel.append(mode);section.append(modeLabel);
    const panel=document.createElement('div');panel.hidden=true;panel.id='chatgpt-connection';
    const explanation=document.createElement('p');explanation.textContent='Optional translation only. Continue with ChatGPT to connect your own eligible plan. It cannot transcribe audio. CueFlora never switches to a paid API automatically.';
    const status=document.createElement('p');status.setAttribute('role','status');status.tabIndex=-1;
    const accounts=document.createElement('select');accounts.name='translation.accountRef';accounts.setAttribute('aria-label','ChatGPT account');
    const model=document.createElement('select');model.name='translation.chatgptModel';model.setAttribute('aria-label','ChatGPT model');
    const accountLabel=document.createElement('label');accountLabel.textContent='Connected ChatGPT account';accountLabel.append(accounts);
    const modelLabel=document.createElement('label');modelLabel.textContent='Eligible translation model — choose explicitly';modelLabel.append(model);
    const usage=document.createElement('a');usage.href='https://chatgpt.com/settings/usage';usage.textContent='Manage usage';usage.target='_blank';usage.rel='noopener noreferrer';
    let taskId:string|null=null, timer:ReturnType<typeof setTimeout>|undefined, sequence=0, disabled=false,working=false;
    const control=(text:string,work:()=>Promise<void>)=>{const button=document.createElement('button');button.type='button';button.textContent=text;
        button.addEventListener('click',()=>{if(button.disabled)return;working=true;activity(true);sync();
            void work().catch(()=>{status.textContent='ChatGPT connection failed. Upgrade/Repair the helper or reconnect. No paid API fallback was used.';status.focus();})
                .finally(()=>{working=false;activity(!!taskId);sync();});});return button;};
    const clearModels=()=>{model.replaceChildren();const blank=document.createElement('option');blank.value='';blank.textContent='Choose an eligible model';model.append(blank);};
    const sync=()=>{mode.disabled=disabled||working||!!taskId;accounts.disabled=disabled||working||!!taskId;model.disabled=disabled||working||!!taskId;
        for(const button of [login,reconnect,refresh,disconnect])button.disabled=disabled||working||!!taskId;cancel.disabled=!taskId;};
    async function refreshAccounts(selectRef?:string){
        const result=await settingsRequest({type:'CHATGPT_STATUS'});if(result.error)throw Error('Account status unavailable');
        const prior=selectRef||accounts.value;accounts.replaceChildren();
        const blank=document.createElement('option');blank.value='';blank.textContent='Choose an account';accounts.append(blank);
        for(const account of result.accounts||[]){const option=document.createElement('option');option.value=account.accountRef;
            option.textContent=account.label+(account.connected&&account.planEnabled?' — connected':' — reconnect required');accounts.append(option);}
        accounts.value=prior;sync();
    }
    async function poll(id:string,expected:number){
        const result=await settingsRequest({type:'TASK_STATUS',taskId:id});
        if(expected!==sequence||taskId!==id)return;
        if(result.error||result.status==='error'){
            taskId=null;activity(false);status.textContent=result.reason==='cancelled'?'ChatGPT sign-in cancelled.':'ChatGPT sign-in failed or expired. Check plan permission, Upgrade/Repair, then retry.';status.focus();sync();return;
        }
        if(result.status==='complete'){
            taskId=null;working=true;sync();
            try{
            await refreshAccounts(result.result?.accountRef);clearModels();changed();
            status.textContent='Connected. Choose an eligible model, then Save AI settings. Translation uses your ChatGPT plan; audio transcription still needs a separate service or YouTube captions.';
            if(result.result?.needsUsageNotice){
                const notice=document.createElement('dialog');const text=document.createElement('p');text.textContent='You’re using your ChatGPT plan. Eligible CueFlora translations use your plan or credits. Review limits in Manage usage. No request is sent until Run.';
                const gotIt=document.createElement('button');gotIt.textContent='Got it';
                gotIt.addEventListener('click',()=>{gotIt.disabled=true;
                    void settingsRequest({type:'CHATGPT_ACK_USAGE',accountRef:result.result.accountRef})
                        .then(reply=>{if(reply.error)throw Error();if(typeof notice.close==='function')notice.close();notice.remove();})
                        .catch(()=>{gotIt.disabled=false;text.textContent+=' Notice acknowledgement could not be saved; retry explicitly.';});
                });notice.append(text,gotIt);panel.append(notice);
                if(typeof notice.showModal==='function')notice.showModal();else notice.setAttribute('open','');
            }
            }catch{
                status.textContent='Sign-in finished, but account status could not be loaded. Reopen the ChatGPT connection to refresh accounts before saving.';status.focus();
            }finally{working=false;activity(!!taskId);sync();}
            return;
        }
        status.textContent=result.stage==='validating-account'?'Validating the ChatGPT account…':'Complete sign-in in your browser. You can Cancel; this window closes after ten minutes.';
        timer=setTimeout(()=>void poll(id,expected).catch(()=>{
            if(expected!==sequence||taskId!==id)return;
            activity(true);status.textContent='Account status unavailable. The task may still be running. Cancel it before trying again.';status.focus();sync();
        }),800);
    }
    async function start(ref?:string){
        if(disabled||taskId)return;const expected=++sequence;status.textContent='Starting secure ChatGPT sign-in…';
        const result=await settingsRequest({type:'CHATGPT_LOGIN',...(ref?{accountRef:ref}: {})});
        if(result.error||!result.taskId)throw Error('Sign-in startup failed');
        taskId=result.taskId;sync();await poll(taskId!,expected);
    }
    async function accountOperation(message:import('../../utils/types').AccountMessage){
        const started=await settingsRequest(message);if(started.error||!started.taskId)throw Error('Account task unavailable');
        taskId=started.taskId;sync();const id=taskId!,expected=sequence,deadline=Date.now()+120000;let completed=false;
        try{
            while(Date.now()<deadline){
                if(sequence!==expected||taskId!==id)throw Error('Account task changed');
                const result=await settingsRequest({type:'TASK_STATUS',taskId:id});
                if(sequence!==expected||taskId!==id||result.error||result.status==='error')throw Error('Account task changed or failed');
                if(result.status==='complete'){completed=true;return result.result;}
                await new Promise(resolve=>setTimeout(resolve,500));
            }
            throw Error('Account metadata task timed out');
        }finally{
            if(sequence===expected&&taskId===id){
                if(!completed){
                    try{const reply=await settingsRequest({type:'TASK_CANCEL',taskId:id});completed=!reply.error;}
                    catch{/* Keep the reference and Cancel available when termination is uncertain. */}
                }
                if(completed)taskId=null;
            }
            activity(!!taskId);sync();
        }
    }
    const login=control('Continue with ChatGPT',()=>start());
    const reconnect=control('Reconnect selected account',async()=>{if(!accounts.value)throw Error('Choose account');await start(accounts.value);});
    const refresh=control('Load eligible models',async()=>{
        if(!accounts.value){await refreshAccounts();status.textContent='Choose an account, then load its eligible models.';return;}
        const ref=accounts.value,expected=++sequence;status.textContent='Loading account-specific models (no generation)…';
        const result=await accountOperation({type:'CHATGPT_MODELS',accountRef:ref});if(expected!==sequence||ref!==accounts.value)return;
        if(result.error)throw Error('Models unavailable');clearModels();
        for(const item of result.models||[]){const option=document.createElement('option');option.value=item.id;option.textContent=item.label;model.append(option);}
        status.textContent='Using ChatGPT plan. Choose a model explicitly'+(result.partial?' (partial list)':'')+'. Generation compatibility has not been tested.';
    });
    const disconnect=control('Disconnect selected account',async()=>{
        const ref=accounts.value;if(!ref)throw Error('Choose account');
        const result=await accountOperation({type:'CHATGPT_DISCONNECT',accountRef:ref});if(result.error)throw Error('Disconnect failed');
        clearModels();await refreshAccounts(ref);changed();status.textContent=result.revocationConfirmed?'Disconnected. Choose another connection before the next AI translation.':'Disconnected locally. Remote revocation was not confirmed; disconnect CueFlora in ChatGPT settings too.';
    });
    const cancel=control('Cancel account task',async()=>{
        if(!taskId)return;const id=taskId;++sequence;if(timer)clearTimeout(timer);await settingsRequest({type:'TASK_CANCEL',taskId:id});taskId=null;status.textContent='ChatGPT sign-in cancelled.';sync();
    });
    panel.append(explanation,login,reconnect,cancel,accountLabel,refresh,modelLabel,usage,disconnect,status);section.append(panel);clearModels();sync();
    mode.addEventListener('change',()=>{panel.hidden=mode.value!=='chatgpt';changed();if(!panel.hidden)void refreshAccounts().catch(()=>{status.textContent='Run the latest CueFlora Setup and Upgrade/Repair to connect ChatGPT.';});});
    accounts.addEventListener('change',()=>{++sequence;clearModels();changed();});model.addEventListener('change',changed);
    window.addEventListener('pagehide',()=>{if(timer)clearTimeout(timer);if(taskId)void browser.runtime.sendMessage({type:'TASK_CANCEL',taskId});});
    return { mode, panel,
        display(provider:Provider){++sequence;mode.value=provider.backend==='chatgpt'?'chatgpt':provider.model?'api':'';panel.hidden=mode.value!=='chatgpt';
            accounts.replaceChildren();clearModels();
            if(provider.accountRef){const option=document.createElement('option');option.value=provider.accountRef;option.textContent='Saved ChatGPT account';accounts.append(option);}
            if(provider.backend==='chatgpt'&&provider.model){const option=document.createElement('option');option.value=provider.model;option.textContent=provider.model;model.append(option);model.value=provider.model;}},
        draft():Provider|null {return mode.value==='chatgpt'?{backend:'chatgpt',accountRef:accounts.value,label:'Using ChatGPT plan',model:model.value,baseUrl:'',apiKey:'',allowRemoteHttp:false}:null;},
        setBusy(value:boolean){disabled=value;sync();},
    };
}
