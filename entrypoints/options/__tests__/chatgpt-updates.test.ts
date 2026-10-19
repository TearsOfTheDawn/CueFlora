import {beforeEach,describe,expect,it,vi} from 'vitest';
import {fakeBrowser} from 'wxt/testing/fake-browser';
import {createChatGPTControls} from '../chatgpt';
import {createUpdates} from '../updates';
import {providerDefaults} from '../../../utils/providers';

describe('optional accounts and user-triggered updates',()=>{
    beforeEach(()=>{fakeBrowser.reset();document.body.replaceChildren();vi.spyOn(fakeBrowser.runtime,'getManifest').mockReturnValue({manifest_version:3,name:'CueFlora',version:'0.2.0'} as any);});
    it('starts with no account selection and makes no metadata or inference request automatically',()=>{
        const send=vi.spyOn(fakeBrowser.runtime,'sendMessage');const section=document.createElement('section');document.body.append(section);
        const controls=createChatGPTControls(section,vi.fn());controls.display(providerDefaults().translation);
        expect(controls.mode.value).toBe('');expect(controls.draft()).toBeNull();expect(send).not.toHaveBeenCalled();
        expect(section.textContent).toContain('cannot transcribe audio');
    });
    it('does not check, download, install or reload until the user explicitly acts',()=>{
        const send=vi.spyOn(fakeBrowser.runtime,'sendMessage');const section=document.createElement('section');document.body.append(section);createUpdates(section);
        const buttons=Array.from(section.querySelectorAll('button'));expect(buttons[0].disabled).toBe(false);
        expect(buttons.filter(button=>!button.disabled).map(button=>button.textContent)).toEqual(['Check for updates','Check helper / installation versions']);expect(send).not.toHaveBeenCalled();
        expect(section.textContent).toContain('0.2.0');
    });
});
