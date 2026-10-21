import {describe,expect,it} from 'vitest';
import {createDiagnosticLog,createSessionDiagnosticLog,publicDebugReport,safeFailure,failureMessage} from '../failureDiagnostics';
import {publicNativeResponse,validNativeResponse} from '../nativeResponse';
import {publicTask} from '../nativeTasks';
import {validateRequest} from '../requestValidation';

describe('privacy-safe failure diagnostics',()=>{
    it('serializes session writes and restores history after a worker restart without secrets',async()=>{
        const records:Record<string,unknown>={};const storage={get:async()=>structuredClone(records),set:async(values:Record<string,unknown>)=>{Object.assign(records,structuredClone(values));}};
        const first=createSessionDiagnosticLog(storage,()=>123);
        first.record('TRANSCRIBE_NATIVE',{stage:'upload',code:'network',raw:'synthetic-secret'});
        first.record('update-check',{stage:'update-check',code:'provider-request',httpStatus:415});
        expect((await first.report('0.2.1')).recentFailures).toHaveLength(2);
        const restarted=createSessionDiagnosticLog(storage,()=>456);
        expect((await restarted.report('0.2.1')).recentFailures.map(item=>item.at)).toEqual([123,123]);
        expect(JSON.stringify(records)).not.toContain('synthetic-secret');
    });
    it('retains in-memory failures and reports incomplete history when session persistence fails',async()=>{
        const log=createSessionDiagnosticLog({get:async()=>{throw Error('synthetic-secret');},set:async()=>{throw Error('synthetic-secret');}},()=>123);
        log.record('TRANSCRIBE_NATIVE',{stage:'transcription',code:'provider-auth',httpStatus:401});
        const result=await log.report('0.2.1');expect(result.historyIncomplete).toBe(true);expect(result.recentFailures).toHaveLength(1);
        expect(JSON.stringify(result)).not.toContain('synthetic-secret');
    });
    it('preserves HTTP status and stage, never provider bodies or credential payloads',()=>{
        const request={type:'TRANSCRIBE_NATIVE',jobId:'run',whisperConfig:{credential:{blob:'synthetic-ciphertext'}}};
        const incoming={jobId:'run',error:'synthetic-secret https://private.invalid',failure:{stage:'transcription',code:'provider-request',httpStatus:400,body:'synthetic-secret'}};
        expect(validNativeResponse(incoming,request)).toBe(true);
        const response=publicNativeResponse(incoming,request);
        expect(response.error).toContain('HTTP 400');expect(response.error).toContain('transcription/provider-request');
        expect(JSON.stringify(response)).not.toMatch(/synthetic-secret|private.invalid|ciphertext/);
        expect(safeFailure({stage:'credentials',code:'credential-unavailable'})).toBeDefined();
        for(const value of [{stage:'private-url',code:'unknown'},{stage:'upload',code:'arbitrary-secret'},{stage:'upload',code:'network',httpStatus:NaN},{stage:'upload',code:'network',httpStatus:true}])expect(safeFailure(value)).toBeUndefined();
    });
    it('bounds memory history and strips arbitrary operation/health/report fields',()=>{
        const log=createDiagnosticLog(()=>123);
        for(let i=0;i<25;i++)log.record('TRANSCRIBE_NATIVE',{stage:'upload',code:'network',raw:'synthetic-secret'});
        log.record('https://private.invalid',{stage:'download',code:'download-failed'});
        const result=log.report('0.2.1',{version:'0.2.1',apiKey:'synthetic-secret',tools:{ffmpeg:{available:true,key:'synthetic-secret'}}});
        expect(result.recentFailures).toHaveLength(20);expect(result.recentFailures.at(-1)?.operation).toBe('native');
        const report=publicDebugReport({...result,apiKey:'synthetic-secret',recentFailures:result.recentFailures.map(value=>({...value,credential:'synthetic-secret'}))});
        expect(JSON.stringify(report)).not.toMatch(/synthetic-secret|private.invalid/);expect(report.tools.ffmpeg).toBe(true);
    });
    it('projects update task failure reasons and rejects injected diagnostics messages',()=>{
        const id='12345678-1234-1234-1234-123456789abc';
        const task=publicTask({type:'task',taskId:id,status:'error',failure:{stage:'update-check',code:'provider-request',httpStatus:415,raw:'synthetic-secret'}},id,'update-check');
        expect(failureMessage(task.failure!)).toContain('HTTP 415');expect(JSON.stringify(task)).not.toContain('synthetic-secret');
        expect(()=>validateRequest({type:'DIAGNOSTICS_GET',includeKeys:true})).toThrow();
    });
});
