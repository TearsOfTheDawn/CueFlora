/** Transient native connections owned by extension settings, never by page messages. */
import {safeFailure,type SafeFailure} from './failureDiagnostics';
type Port = ReturnType<typeof browser.runtime.connectNative>;
export interface TaskState { taskId:string; status:'starting'|'started'|'progress'|'complete'|'error'; stage?:string; reason?:string; result?:Record<string,unknown>;failure?:SafeFailure }
const uuid = (value:unknown):value is string => typeof value==='string' && /^[a-f0-9-]{36}$/.test(value);
export function publicTask(value:unknown, taskId:string, operation='chatgpt-login'):TaskState {
    if (!value || typeof value!=='object') throw Error('Invalid helper task response.');
    const incoming=value as Record<string,unknown>;
    if(incoming.taskId!==taskId || incoming.type!=='task' || !['started','progress','complete','error'].includes(String(incoming.status))) throw Error('Invalid helper task response.');
    const result:TaskState={taskId,status:incoming.status as TaskState['status']};
    if(incoming.failure!==undefined){const failure=safeFailure(incoming.failure);if(!failure)throw Error('Invalid helper failure metadata.');result.failure=failure;}
    if(['waiting-for-user','validating-account','downloading','verifying','ready-to-install'].includes(String(incoming.stage)))result.stage=String(incoming.stage);
    if(['cancelled','authentication-failed','download-failed','invalid-request'].includes(String(incoming.reason))) result.reason=String(incoming.reason);
    const raw=incoming.result as Record<string,unknown>|undefined;
    if(operation==='chatgpt-login' && raw && uuid(raw.accountRef) && typeof raw.label==='string' && raw.label.length<=200 && raw.connected===true && raw.planEnabled===true)
        result.result={accountRef:raw.accountRef,label:raw.label,connected:true,planEnabled:true,needsUsageNotice:raw.needsUsageNotice===true};
    if(operation==='update-check' && raw && typeof raw.available==='boolean') {
        if(raw.available===false && typeof raw.currentVersion==='string' && /^\d+\.\d+\.\d+$/.test(raw.currentVersion))result.result={available:false,currentVersion:raw.currentVersion};
        if(raw.available===true && uuid(raw.selectionRef) && typeof raw.version==='string' && /^\d+\.\d+\.\d+$/.test(raw.version) && typeof raw.size==='number' && Number.isSafeInteger(raw.size) && raw.size>0 && raw.size<=1024**3)
            result.result={available:true,selectionRef:raw.selectionRef,version:raw.version,size:raw.size,unsigned:true};
    }
    if(operation==='update-download' && raw && uuid(raw.selectionRef)&&raw.ready===true&&typeof raw.version==='string'&&/^\d+\.\d+\.\d+$/.test(raw.version))result.result={selectionRef:raw.selectionRef,version:raw.version,ready:true};
    if(operation==='chatgpt-models'&&raw&&Array.isArray(raw.models)&&raw.models.length<=500&&raw.models.every(item=>item&&typeof item.id==='string'&&/^[\w.:/\-]{1,200}$/.test(item.id)&&typeof item.label==='string'&&item.label.length<=200))result.result={models:raw.models.map(item=>({id:item.id,label:item.label})),partial:raw.partial===true};
    if(operation==='chatgpt-disconnect'&&raw&&raw.disconnected===true&&typeof raw.revocationConfirmed==='boolean')result.result={disconnected:true,revocationConfirmed:raw.revocationConfirmed};
    if(typeof incoming.percent==='number'&&Number.isFinite(incoming.percent)&&incoming.percent>=0&&incoming.percent<=100)(result as TaskState&{percent:number}).percent=incoming.percent;
    if(result.status==='complete'&&!result.result)throw Error('Invalid helper task result.');
    return result;
}
export function createNativeTasks(connect:()=>Port,onFailure:(operation:string,failure:SafeFailure)=>void=()=>{}) {
    const tasks=new Map<string,{state:TaskState;port:Port;cancel:()=>void;expires:number}>();
    return {
        async start(operation:'chatgpt-login'|'chatgpt-models'|'chatgpt-disconnect'|'update-check'|'update-download',accountRef?:string,selectionRef?:string):Promise<TaskState> {
            for(const [id,task] of tasks)if(task.expires<Date.now()){task.cancel();tasks.delete(id);}
            if([...tasks.values()].some(task=>!['complete','error'].includes(task.state.status)))throw Error('Finish or cancel the current CueFlora settings task first.');
            if(accountRef!==undefined&&!uuid(accountRef))throw Error('Invalid account reference.');
            if(selectionRef!==undefined&&!uuid(selectionRef))throw Error('Invalid update reference.');
            const taskId=crypto.randomUUID(), port=connect();
            return await new Promise((resolve,reject)=>{
                let acknowledged=false, preflight=true, ended=false;
                const task={state:{taskId,status:'starting'} as TaskState,port,cancel:()=>{},expires:Date.now()+(operation==='update-download'?62:12)*60*1000};
                if(tasks.size>=16)for(const [id,old]of tasks){if(['complete','error'].includes(old.state.status)){tasks.delete(id);if(tasks.size<16)break;}}
                const fail=(reason:string)=>{if(ended)return; ended=true;clearTimeout(ack);clearTimeout(limit);const failure:SafeFailure={stage:'native-connection',code:reason==='cancelled'?'cancelled':'helper-unavailable'};task.state={taskId,status:'error',reason,failure};onFailure(operation,failure);port.disconnect();if(!acknowledged)reject(Error('This operation requires the latest CueFlora helper. Upgrade/Repair and retry.'));};
                const ack=setTimeout(()=>fail('authentication-failed'),10000);
                const limit=setTimeout(()=>fail('cancelled'),operation==='update-download'?3610000:610000);
                task.cancel=()=>{if(ended)return;try{port.postMessage({type:'TASK_CANCEL',taskId});}finally{fail('cancelled');}};
                tasks.set(taskId,task);
                port.onDisconnect.addListener(()=>fail('authentication-failed'));
                port.onMessage.addListener((value:unknown)=>{
                    if(ended)return;
                    try{
                        if(preflight){
                            const health=value as {status?:string;capabilities?:{chatgpt?:string;updates?:string}};
                            if(health?.status!=='PONG'||(operation.startsWith('chatgpt-')?health.capabilities?.chatgpt!=='chatgpt-translation-v1':health.capabilities?.updates!=='paired-updates-v1'))throw Error('Upgrade required');
                            preflight=false;port.postMessage({type:'TASK_START',taskId,operation,...(accountRef?{accountRef}: {}),...(selectionRef?{selectionRef}: {})});return;
                        }
                        task.state=publicTask(value,taskId,operation);
                        if(task.state.status==='error')onFailure(operation,task.state.failure||{stage:'unknown',code:'unknown'});
                        if(!acknowledged){acknowledged=true;clearTimeout(ack);resolve({...task.state});}
                        if(['complete','error'].includes(task.state.status)){ended=true;clearTimeout(limit);port.disconnect();}
                    }catch{fail('authentication-failed');}
                });
                try{port.postMessage({type:'PING'});}catch{fail('authentication-failed');}
            });
        },
        status(taskId:unknown):TaskState {if(!uuid(taskId)||!tasks.has(taskId))throw Error('Task expired. Start again.');return {...tasks.get(taskId)!.state};},
        cancel(taskId:unknown):TaskState {if(!uuid(taskId)||!tasks.has(taskId))throw Error('Task expired.');tasks.get(taskId)!.cancel();return {...tasks.get(taskId)!.state};},
    };
}
