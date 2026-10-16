import { beforeEach, expect, it, vi } from 'vitest';
import { fakeBrowser } from 'wxt/testing/fake-browser';
import background from '../background';
let installed:(details:any)=>void, clicked:()=>void;
beforeEach(()=>{
    fakeBrowser.reset();
    vi.spyOn(fakeBrowser.storage.local,'setAccessLevel').mockResolvedValue();
    vi.spyOn(fakeBrowser.runtime.onInstalled,'addListener').mockImplementation((fn:(details:any)=>void)=>{installed=fn;});
    vi.spyOn(fakeBrowser.action.onClicked,'addListener').mockImplementation((fn:(tab:any)=>void)=>{clicked=()=>fn({} as any);});
    background.main();
});
it('opens setup on first install and toolbar clicks, not updates',()=>{
    const open=vi.spyOn(fakeBrowser.runtime,'openOptionsPage').mockResolvedValue();
    installed({reason:'update'}); expect(open).not.toHaveBeenCalled();
    installed({reason:'install'}); expect(open).toHaveBeenCalledTimes(1);
    clicked(); expect(open).toHaveBeenCalledTimes(2);
});
