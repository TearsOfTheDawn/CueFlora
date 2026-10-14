import { beforeEach, expect, it, vi } from 'vitest';
beforeEach(()=>vi.resetModules());
const key='cueflora_translation_lang';
async function setup() {
    const send=vi.spyOn(browser.runtime,'sendMessage').mockImplementation(async()=>({[key]:'en'}));
    const client=await import('../preferenceClient'); await client.initializePreferences(); return {send,client};
}
it('refreshes only selected preference keys through the background',async()=>{
    const {send,client}=await setup(); send.mockImplementation(async()=>({[key]:'ja',cueflora_appearance_v1:'bad',private_key:'secret'}));
    expect(await client.refreshPreferences(()=>true,[key])).toEqual([key]);
    expect(client.preferences.getItem(key)).toBe('ja'); expect(client.preferences.getItem('private_key')).toBeNull();
});
it('rejects late responses after navigation/Run and newer refreshes',async()=>{
    const {send,client}=await setup(); const replies:Array<(value:unknown)=>void>=[];
    send.mockImplementation(()=>new Promise(resolve=>replies.push(resolve)));
    const old=client.refreshPreferences(), recent=client.refreshPreferences();
    replies[1]({[key]:'ja'}); await recent; replies[0]({[key]:'fr'}); await old;
    expect(client.preferences.getItem(key)).toBe('ja');
    const blocked=client.refreshPreferences(()=>false); replies[2]({[key]:'fr'}); expect(await blocked).toEqual([]);
    expect(client.preferences.getItem(key)).toBe('ja');
});
it('preserves local edits made during a refresh',async()=>{
    const {send,client}=await setup(); let reply!:(value:unknown)=>void;
    send.mockImplementationOnce(()=>new Promise(resolve=>{reply=resolve;})).mockImplementation(async()=>({value:'de'}));
    const refresh=client.refreshPreferences(); client.preferences.setItem(key,'de');
    reply({[key]:'fr'}); expect(await refresh).toEqual([]); expect(client.preferences.getItem(key)).toBe('de');
});
it('does not replace an edit whose write was already in flight when refresh began',async()=>{
    const {send,client}=await setup(); let written!:(value:unknown)=>void;
    send.mockImplementationOnce(()=>new Promise(resolve=>{written=resolve;})).mockImplementation(async()=>({[key]:'fr'}));
    client.preferences.setItem(key,'de'); expect(await client.refreshPreferences()).toEqual([]);
    expect(client.preferences.getItem(key)).toBe('de'); written({value:'de'}); await Promise.resolve();
});
