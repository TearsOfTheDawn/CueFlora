import {beforeEach,describe,expect,it,vi} from 'vitest';
import {fakeBrowser} from 'wxt/testing/fake-browser';
import {createDiagnostics} from '../diagnostics';
import {createUpdates} from '../updates';

describe('support report and actionable update errors',()=>{
    beforeEach(()=>{fakeBrowser.reset();document.body.replaceChildren();vi.spyOn(fakeBrowser.runtime,'getManifest').mockReturnValue({manifest_version:3,name:'CueFlora',version:'0.2.1'} as any);});
    it('makes no automatic request, then displays only projected metadata and keyboard-copy fallback',async()=>{
        const send=vi.spyOn(fakeBrowser.runtime,'sendMessage').mockResolvedValue({schema:1,extensionVersion:'0.2.1',helperVersion:'0.2.1',tools:{ffmpeg:true},apiKey:'synthetic-secret',recentFailures:[{operation:'TRANSCRIBE_NATIVE',stage:'transcription',code:'provider-auth',httpStatus:401,at:123,raw:'synthetic-secret'}]} as any);
        const section=document.createElement('section');document.body.append(section);createDiagnostics(section);
        expect(send).not.toHaveBeenCalled();const buttons=section.querySelectorAll('button');buttons[0].click();
        await vi.waitFor(()=>expect(buttons[1].disabled).toBe(false));
        expect(send).toHaveBeenCalledWith({type:'DIAGNOSTICS_GET'});
        const output=section.querySelector('textarea')!;expect(output.readOnly).toBe(true);expect(output.value).toContain('401');expect(output.value).not.toContain('synthetic-secret');
        buttons[1].click();await vi.waitFor(()=>expect(section.textContent).toContain('Copy the selected report manually'));expect(document.activeElement).toBe(output);
    });
    it('retains safe update HTTP errors rather than replacing them with the generic task failure',async()=>{
        vi.spyOn(fakeBrowser.runtime,'sendMessage').mockImplementation(async(message:any)=>message.type==='UPDATES_CHECK'?{taskId:'task'}:{taskId:'task',status:'error',failure:{stage:'update-check',code:'provider-request',httpStatus:415,raw:'synthetic-secret'}});
        const section=document.createElement('section');document.body.append(section);createUpdates(section);section.querySelector('button')!.click();
        await vi.waitFor(()=>expect(section.textContent).toContain('HTTP 415'));expect(section.textContent).not.toContain('synthetic-secret');
        expect(section.querySelectorAll('button')[1].disabled).toBe(true);expect(document.activeElement).toBe(section.querySelector('[role=status]'));
    });
});
