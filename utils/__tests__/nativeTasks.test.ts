import {describe,expect,it,vi} from 'vitest';
import {createNativeTasks,publicTask} from '../nativeTasks';
import {validateRequest} from '../requestValidation';

const id='12345678-1234-1234-1234-123456789abc';
describe('settings-native task boundary',()=>{
    it('projects only safe account fields, never tokens',()=>{
        const result=publicTask({type:'task',taskId:id,status:'complete',result:{accountRef:id,label:'ChatGPT account 1',connected:true,planEnabled:true,access_token:'synthetic-secret',refresh_token:'synthetic-refresh'}},id);
        expect(JSON.stringify(result)).not.toContain('synthetic-secret');expect(JSON.stringify(result)).not.toContain('synthetic-refresh');
        expect(()=>publicTask({type:'task',taskId:'stale',status:'started'},id)).toThrow();
    });
    it('acknowledges login promptly, negotiates capabilities and cancels the same port',async()=>{
        let incoming:(value:any)=>void=()=>{},disconnected=()=>{};
        const post=vi.fn((message:any)=>queueMicrotask(()=>{
            if(message.type==='PING')incoming({status:'PONG',capabilities:{chatgpt:'chatgpt-translation-v1'}});
            else if(message.type==='TASK_START')incoming({type:'task',taskId:message.taskId,status:'started'});
        }));
        const disconnect=vi.fn(()=>disconnected());
        const hub=createNativeTasks(()=>({postMessage:post,disconnect,onMessage:{addListener:(listener:any)=>incoming=listener},onDisconnect:{addListener:(listener:any)=>disconnected=listener}} as any));
        const task=await hub.start('chatgpt-login');expect(task.status).toBe('started');
        expect(post.mock.calls[0][0]).toEqual({type:'PING'});expect(post.mock.calls[1][0]).toMatchObject({type:'TASK_START',operation:'chatgpt-login',taskId:task.taskId});
        hub.cancel(task.taskId);expect(hub.status(task.taskId).status).toBe('error');expect(disconnect).toHaveBeenCalled();
    });
    it('rejects arbitrary URLs, executable paths and token payloads before native dispatch',()=>{
        for(const request of [{type:'UPDATES_DOWNLOAD',selectionRef:id,url:'https://evil.invalid/file'},
            {type:'UPDATES_INSTALL',selectionRef:id,path:'foreign.exe',confirmation:'install'},
            {type:'CHATGPT_LOGIN',access_token:'synthetic-secret'}])expect(()=>validateRequest(request)).toThrow();
    });
});
