import { describe, it, expect } from 'vitest';
import { publicNativeResponse } from '../nativeResponse';
describe('Deno health capability', () => {
  it('marks older helpers for upgrade without forwarding paths', () => {
    const response = publicNativeResponse({ status:'PONG',version:'0.1.0',tools:{ ffmpeg:{available:true,path:'secret'} } },{type:'PING'});
    expect(response.helperUpgradeRequired).toBe(true);
    expect(response.tools).toMatchObject({deno:{available:false},ffmpeg:{available:true}});
    expect(JSON.stringify(response)).not.toContain('secret');
  });
  it('supports new helpers and rejects malformed availability', () => {
    const response = publicNativeResponse({status:'PONG',version:'0.1.0',tools:{deno:{available:true,error:'secret'}}},{type:'PING'});
    expect(response.helperUpgradeRequired).toBe(false);
    expect(response.tools).toMatchObject({deno:{available:true}});
    const invalid = publicNativeResponse({status:'PONG',tools:{deno:{available:'yes'}}},{type:'PING'});
    expect(invalid.tools).toMatchObject({deno:{available:false}});
  });
});
