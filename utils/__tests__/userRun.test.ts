import { expect, it, vi } from 'vitest';
import { trustedRun } from '../userRun';

it('page-generated clicks and dispatches cannot invoke a Run handler',async()=>{
    const handler=vi.fn(),button=document.createElement('button');
    button.addEventListener('click',trustedRun(handler));
    button.click(); button.dispatchEvent(new MouseEvent('click'));
    await Promise.resolve(); expect(handler).not.toHaveBeenCalled();
});

it('the trusted-input branch executes exactly once without changing the workflow',async()=>{
    const handler=vi.fn(async()=>{});
    // Direct contract test, not a fabricated trusted browser event or live acceptance.
    await trustedRun(handler)({isTrusted:true});
    expect(handler).toHaveBeenCalledTimes(1);
});
