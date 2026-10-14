import { describe, expect, it } from 'vitest';
import { validatedLinks, renderReleaseGuidance } from '../publicLinks';

const links = {downloadUrl:'https://fixture.example.com/download',privacyUrl:'https://fixture.example.com/privacy',supportUrl:'https://fixture.example.com/support'};
describe('public installation guidance',()=>{
    it('leaves preview guidance unchanged without real configured links',()=>{
        document.body.innerHTML='<p id="helper-install-guidance">Private preview</p>';
        renderReleaseGuidance(document,null);
        expect(document.body.textContent).toBe('Private preview');
        for (const url of ['http://example.com','https://secret@example.com','https://example.com/?key=secret','https://localhost',
            'https://localhost.','https://127.0.0.2','https://10.0.0.1','https://[::1]','https://example.com:444','https://example.test','https://example.com/ path'])
            expect(validatedLinks({...links,downloadUrl:url})).toBeNull();
    });
    it('creates user-triggered links as safe DOM nodes without requests or credentials',()=>{
        document.body.innerHTML='<p id="helper-install-guidance"></p><footer id="release-label"></footer>';
        renderReleaseGuidance(document,{...links,apiKey:'not forwarded'});
        expect(document.querySelectorAll('a')).toHaveLength(3);
        expect(document.body.textContent).toContain('unsigned');
        expect(document.body.textContent).not.toContain('not forwarded');
        expect(document.querySelector('a')?.rel).toBe('noopener noreferrer');
    });
});
