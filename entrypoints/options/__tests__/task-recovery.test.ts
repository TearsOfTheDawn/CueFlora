import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest';
import {fakeBrowser} from 'wxt/testing/fake-browser';
import {createUpdates} from '../updates';
import {createChatGPTControls} from '../chatgpt';

const id='11111111-1111-4111-8111-111111111111';
const button=(root:HTMLElement,text:string)=>Array.from(root.querySelectorAll('button')).find(item=>item.textContent===text)!;
describe('settings task ownership after transient status failures',()=>{
    beforeEach(()=>{fakeBrowser.reset();document.body.replaceChildren();vi.useFakeTimers();
        vi.spyOn(fakeBrowser.runtime,'getManifest').mockReturnValue({manifest_version:3,name:'CueFlora',version:'0.2.2'} as any);});
    afterEach(()=>{vi.useRealTimers();vi.restoreAllMocks();});
    it('keeps an update task cancellable and prevents another start after polling fails',async()=>{
        let polls=0;
        const send=vi.spyOn(fakeBrowser.runtime,'sendMessage').mockImplementation(async(message:any)=>{
            if(message.type==='UPDATES_CHECK')return {taskId:id,status:'started'};
            if(message.type==='TASK_STATUS'){if(polls++)throw Error('synthetic private failure');return {taskId:id,status:'progress'};}
            if(message.type==='TASK_CANCEL')return {taskId:id,status:'error',reason:'cancelled'};
            throw Error('Unexpected request');
        });
        const root=document.createElement('section');document.body.append(root);createUpdates(root);
        button(root,'Check for updates').click();await vi.advanceTimersByTimeAsync(0);
        await vi.advanceTimersByTimeAsync(800);
        expect(button(root,'Check for updates').disabled).toBe(true);
        expect(button(root,'Cancel download/check').disabled).toBe(false);
        expect(root.textContent).toContain('may still be running');
        expect(root.textContent).not.toContain('synthetic private');
        button(root,'Cancel download/check').click();await vi.advanceTimersByTimeAsync(0);
        expect(send).toHaveBeenCalledWith({type:'TASK_CANCEL',taskId:id});
        expect(button(root,'Check for updates').disabled).toBe(false);
    });
    it('retains sign-in ownership after a failed status read, until explicit Cancel',async()=>{
        let polls=0;const activity=vi.fn();
        const send=vi.spyOn(fakeBrowser.runtime,'sendMessage').mockImplementation(async(message:any)=>{
            if(message.type==='CHATGPT_STATUS')return {accounts:[]};
            if(message.type==='CHATGPT_LOGIN')return {taskId:id,status:'started'};
            if(message.type==='TASK_STATUS'){if(polls++)throw Error('synthetic private failure');return {taskId:id,status:'progress'};}
            if(message.type==='TASK_CANCEL')return {taskId:id,status:'error',reason:'cancelled'};
            throw Error('Unexpected request');
        });
        const root=document.createElement('section');document.body.append(root);createChatGPTControls(root,vi.fn(),activity);
        button(root,'Continue with ChatGPT').click();await vi.advanceTimersByTimeAsync(0);
        await vi.advanceTimersByTimeAsync(800);
        expect(button(root,'Continue with ChatGPT').disabled).toBe(true);
        expect(button(root,'Cancel account task').disabled).toBe(false);
        expect(activity).toHaveBeenLastCalledWith(true);
        button(root,'Cancel account task').click();await vi.advanceTimersByTimeAsync(0);
        expect(send).toHaveBeenCalledWith({type:'TASK_CANCEL',taskId:id});
        expect(button(root,'Continue with ChatGPT').disabled).toBe(false);
        expect(activity).toHaveBeenLastCalledWith(false);
    });
    it('failed account metadata work cancels its native task before another task can start',async()=>{
        const send=vi.spyOn(fakeBrowser.runtime,'sendMessage').mockImplementation(async(message:any)=>{
            if(message.type==='CHATGPT_MODELS')return {taskId:id,status:'started'};
            if(message.type==='TASK_STATUS')throw Error('private status failure');
            if(message.type==='TASK_CANCEL')return {taskId:id,status:'error',reason:'cancelled'};
            throw Error('Unexpected request');
        });
        const root=document.createElement('section');document.body.append(root);const controls=createChatGPTControls(root,vi.fn());
        controls.display({backend:'chatgpt',accountRef:id,label:'saved',model:'fixture-model',baseUrl:'',apiKey:'',allowRemoteHttp:false});
        button(root,'Load eligible models').click();await vi.advanceTimersByTimeAsync(0);
        expect(send).toHaveBeenCalledWith({type:'TASK_CANCEL',taskId:id});
        expect(button(root,'Continue with ChatGPT').disabled).toBe(false);
    });
    it('releases settings after sign-in succeeds but refreshing account status fails',async()=>{
        let polls=0;const activity=vi.fn();
        vi.spyOn(fakeBrowser.runtime,'sendMessage').mockImplementation(async(message:any)=>{
            if(message.type==='CHATGPT_LOGIN')return {taskId:id,status:'started'};
            if(message.type==='TASK_STATUS')return polls++?{taskId:id,status:'complete',result:{accountRef:id}}:{taskId:id,status:'progress'};
            if(message.type==='CHATGPT_STATUS')throw Error('private status failure');
            throw Error('Unexpected request');
        });
        const root=document.createElement('section');document.body.append(root);createChatGPTControls(root,vi.fn(),activity);
        button(root,'Continue with ChatGPT').click();await vi.advanceTimersByTimeAsync(0);
        await vi.advanceTimersByTimeAsync(800);
        expect(root.textContent).toContain('Sign-in finished, but account status could not be loaded');
        expect(button(root,'Continue with ChatGPT').disabled).toBe(false);
        expect(activity).toHaveBeenLastCalledWith(false);
    });
});
