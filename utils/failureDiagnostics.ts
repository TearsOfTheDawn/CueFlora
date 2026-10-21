/** Versioned debug reports contain allowlisted metadata, never raw errors/configuration. */
export const failureStages = ['credentials','download','audio-preparation','upload','transcription','translation','update-check','update-download','native-connection','unknown'] as const;
export const failureCodes = ['credential-unavailable','transport-policy','download-failed','audio-preparation-failed','provider-auth','provider-permission','provider-payment','provider-rate-limit','provider-request','provider-unavailable','network','timeout','cancelled','invalid-response','verification-failed','helper-unavailable','unknown'] as const;
export interface SafeFailure {stage:typeof failureStages[number];code:typeof failureCodes[number];httpStatus?:number}
export function safeFailure(value:unknown):SafeFailure|undefined {
    if(!value||typeof value!=='object'||Array.isArray(value))return;
    const item=value as Record<string,unknown>;
    if(!failureStages.includes(item.stage as SafeFailure['stage'])||!failureCodes.includes(item.code as SafeFailure['code']))return;
    if(item.httpStatus!==undefined&&(!Number.isInteger(item.httpStatus)||Number(item.httpStatus)<400||Number(item.httpStatus)>599))return;
    return {stage:item.stage as SafeFailure['stage'],code:item.code as SafeFailure['code'],...(item.httpStatus===undefined?{}:{httpStatus:Number(item.httpStatus)})};
}
const advice:Record<SafeFailure['code'],string>={
    'credential-unavailable':'The saved key could not be opened. Replace it in AI settings or repair the helper.',
    'transport-policy':'Check the service API address. Remote services require HTTPS.',
    'download-failed':'Audio download failed. Retry explicitly; the AI service may not have been contacted.',
    'audio-preparation-failed':'Audio preparation failed. Check helper tools or repair CueFlora. No unprepared audio was substituted.',
    'provider-auth':'The service rejected authentication. Check the saved API key.',
    'provider-permission':'The service denied this request. Check account/model permissions.',
    'provider-payment':'The service requires payment or available credit. Check your provider account.',
    'provider-rate-limit':'The service rate limit was reached. Wait, then retry explicitly.',
    'provider-request':'The service rejected the request. Check model support, input limits and the service API settings.',
    'provider-unavailable':'The remote service is unavailable. Retry explicitly later.',
    network:'The network request failed. Check connectivity or proxy settings.',
    timeout:'The request timed out. Retry explicitly; no automatic new Run was started.',
    cancelled:'The operation was cancelled.',
    'invalid-response':'The service/helper returned an unsupported response. Copy the debug report.',
    'verification-failed':'Update verification failed. Nothing was installed. Download the matching package manually if needed.',
    'helper-unavailable':'The helper is unavailable or incompatible. Check its connection or Upgrade/Repair.',
    unknown:'The operation failed. Copy the debug report; the helper did not supply a more specific safe reason.',
};
export function failureMessage(value:SafeFailure):string {
    return advice[value.code]+(value.httpStatus?` HTTP ${value.httpStatus}.`:'')+` [${value.stage}/${value.code}]`;
}
const operations=['TRANSCRIBE_NATIVE','TRANSLATE_NATIVE','PROVIDERS_CHECK','CREDENTIAL_PROTECT','update-check','update-download','chatgpt-login','chatgpt-models','chatgpt-disconnect','native'] as const;
export function publicDebugReport(value:unknown) {
    if(!value||typeof value!=='object')throw Error('Debug report unavailable.');
    const raw=value as Record<string,unknown>;
    const version=(value:unknown)=>typeof value==='string'&&/^\d+\.\d+\.\d+$/.test(value)?value:'unavailable';
    if(raw.schema!==1||!Array.isArray(raw.recentFailures)||raw.recentFailures.length>20)throw Error('Debug report unavailable.');
    const tools=raw.tools as Record<string,unknown>|undefined;
    return {schema:1,extensionVersion:version(raw.extensionVersion),helperVersion:version(raw.helperVersion),
        tools:Object.fromEntries(['yt-dlp','ffmpeg','ffprobe','deno'].map(name=>[name,tools?.[name]===true])),
        recentFailures:raw.recentFailures.map(item=>{
            const failure=safeFailure(item);if(!failure||!Number.isSafeInteger(item.at)||item.at<0)throw Error('Debug report unavailable.');
            return {...failure,operation:operations.includes(item.operation)?item.operation:'native',at:item.at};
        }),retention:'Browser-session memory; cleared on extension reload/update or browser restart.',historyIncomplete:raw.historyIncomplete===true,
        excludes:['credentials','service addresses','models','video IDs','subtitle text','raw provider responses']};
}
export function createDiagnosticLog(now:()=>number=Date.now) {
    const failures:Array<SafeFailure&{operation:string;at:number}>=[];
    return {
        restore(value:unknown){
            const report=publicDebugReport({schema:1,recentFailures:value});
            failures.splice(0,failures.length,...report.recentFailures);
        },
        record(operation:unknown,value:unknown){
            const failure=safeFailure(value);if(!failure)return;
            failures.push({...failure,operation:operations.includes(operation as typeof operations[number])?String(operation):'native',at:now()});
            if(failures.length>20)failures.shift();
        },
        report(version:string,health:Record<string,unknown>={}){
            const validVersion=(v:unknown)=>typeof v==='string'&&/^\d+\.\d+\.\d+$/.test(v)?v:'unavailable';
            const tools=health.tools as Record<string,{available?:unknown}>|undefined;
            return {schema:1,extensionVersion:validVersion(version),helperVersion:validVersion(health.version),
                tools:Object.fromEntries(['yt-dlp','ffmpeg','ffprobe','deno'].map(name=>[name,tools?.[name]?.available===true])),
                recentFailures:failures.map(value=>({...value})),retention:'Memory only; cleared when the background worker restarts.',
                excludes:['credentials','service addresses','models','video IDs','subtitle text','raw provider responses']};
        },
    };
}

/** Serialize safe session metadata only; writes never control AI request/retry flow. */
export function createSessionDiagnosticLog(storage:{get:(key:string)=>Promise<Record<string,unknown>>;set:(values:Record<string,unknown>)=>Promise<void>},now:()=>number=Date.now) {
    const key='cueflora_debug_session_v1',log=createDiagnosticLog(now);
    let incomplete=false;
    let queue=storage.get(key).then(record=>{if(record[key]!==undefined)log.restore(record[key]);}).catch(()=>{incomplete=true;});
    return {
        record(operation:unknown,value:unknown){
            const failure=safeFailure(value);if(!failure)return;
            queue=queue.then(async()=>{
                log.record(operation,failure);
                try{await storage.set({[key]:log.report('unavailable').recentFailures});}
                catch{incomplete=true;}
            });
        },
        async report(version:string,health:Record<string,unknown>={}){
            await queue;
            return publicDebugReport({...log.report(version,health),historyIncomplete:incomplete});
        },
    };
}
