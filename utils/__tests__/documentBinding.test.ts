import {beforeEach,describe,expect,it,vi} from 'vitest';
import {verifyRunDocument} from '../documentBinding';
import {documentCheck,runContext} from '../runIdentity';
import {invalidateNavigation} from '../navigation';
import {beginWorkflow} from '../workflow';

const context={videoId:'U_V6Jqg7PV4',generation:2,documentToken:'12345678-1234-1234-1234-123456789abc'};
describe('fresh document Run binding',()=>{
    const tabs={get:vi.fn(),sendMessage:vi.fn()};
    beforeEach(()=>{tabs.get.mockResolvedValue({url:'https://www.youtube.com/watch?v='+context.videoId});tabs.sendMessage.mockImplementation(async(_tab,message)=>({requestId:message.requestId,context:message.context,current:true}));});
    it('uses the current URL and a document-targeted correlated reply',async()=>{
        await verifyRunDocument(4,'document-id','job',context,tabs as any);
        expect(tabs.sendMessage).toHaveBeenCalledWith(4,expect.objectContaining({context}),{documentId:'document-id'});
    });
    it.each(['wrong URL','stale request','new generation','wrong instance','inactive job'])('rejects %s',async failure=>{
        if(failure==='wrong URL')tabs.get.mockResolvedValue({url:'https://www.youtube.com/watch?v=zEpLJgf_4u0'});
        else tabs.sendMessage.mockImplementation(async(_tab,message)=>({requestId:failure==='stale request'?'old':message.requestId,
            context:{...context,...(failure==='new generation'?{generation:3}:failure==='wrong instance'?{documentToken:'aaaaaaaa-1234-1234-1234-123456789abc'}:{})},current:failure!=='inactive job'}));
        await expect(verifyRunDocument(4,'document-id','job',context,tabs as any)).rejects.toThrow();
    });
    it('rejects missing replies within a bounded deadline',async()=>{
        vi.useFakeTimers();tabs.sendMessage.mockImplementation(()=>new Promise(()=>{}));
        const result=expect(verifyRunDocument(4,'document-id','job',context,tabs as any)).rejects.toThrow('did not confirm');
        await vi.advanceTimersByTimeAsync(2500);await result;vi.useRealTimers();
    });
    it('production content rejects same-video returns and noncurrent jobs',()=>{
        window.history.replaceState({},'','/watch?v=U_V6Jqg7PV4');const job=beginWorkflow('U_V6Jqg7PV4',false);const captured=runContext();
        expect(documentCheck({type:'RUN_DOCUMENT_CHECK',requestId:'one',jobId:job,context:captured})?.current).toBe(true);
        invalidateNavigation();expect(documentCheck({type:'RUN_DOCUMENT_CHECK',requestId:'two',jobId:job,context:captured})?.current).toBe(false);
    });
});
