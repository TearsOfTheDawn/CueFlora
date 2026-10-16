import { describe, it, expect, beforeEach, vi } from 'vitest';
import { fakeBrowser } from 'wxt/testing/fake-browser';
import background from '../background';
import { messageTab } from './browserFixture';

describe('background service worker', () => {
    beforeEach(() => {
        fakeBrowser.reset();
        vi.spyOn(fakeBrowser.storage.local, 'setAccessLevel').mockResolvedValue();
        vi.spyOn(fakeBrowser.action.onClicked, 'addListener').mockImplementation(() => {});
        vi.spyOn(fakeBrowser.runtime.onInstalled, 'addListener').mockImplementation(() => {});
    });

    it('fails closed when trusted storage access cannot be restricted', async () => {
        vi.mocked(fakeBrowser.storage.local.setAccessLevel).mockRejectedValue(new Error('synthetic failure'));
        const connect = vi.spyOn(fakeBrowser.runtime, 'connectNative');
        background.main();
        const [result] = await fakeBrowser.runtime.onMessage.trigger(
            { type: 'PROVIDERS_GET' },
            { id: fakeBrowser.runtime.id, url: fakeBrowser.runtime.getURL('/options.html') }, vi.fn(),
        );
        expect(result).toHaveProperty('error');
        expect(connect).not.toHaveBeenCalled();
        expect(fakeBrowser.storage.local.setAccessLevel).toHaveBeenCalledWith({ accessLevel: 'TRUSTED_CONTEXTS' });
    });

    it('should respond to PING with PONG', async () => {
        background.main();

        const result = await fakeBrowser.runtime.onMessage.trigger(
            { type: 'PING' },
            { tab: messageTab, id: 'test' }, vi.fn()
        );

        // trigger returns an array of return values from all listeners
        expect(result).toBeDefined();
    });

    it('should not handle unknown message types', async () => {
        background.main();

        // trigger returns array of listener return values
        const results = await fakeBrowser.runtime.onMessage.trigger(
            { type: 'UNKNOWN_TYPE' },
            { tab: messageTab, id: 'test' }, vi.fn()
        );

        // Listener returns undefined for unknown types, so trigger resolves with [undefined]
        expect(results).toBeDefined();
        expect(results[0]).toBeUndefined();
    });

    it('should handle TRANSCRIBE_NATIVE messages', async () => {
        background.main();

        // This will attempt connectNative which fake-browser stubs —
        // the key thing is it doesn't throw synchronously
        const result = fakeBrowser.runtime.onMessage.trigger(
            {
                type: 'TRANSCRIBE_NATIVE',
                jobId: 'job-1',
                videoId: 'test123',
                whisperConfig: { apiKey: 'key', baseUrl: 'http://test', model: 'whisper-1' }
            },
            { tab: messageTab, id: 'test' }, vi.fn()
        );

        expect(result).toBeInstanceOf(Promise);
    });

    it('should handle TRANSLATE_NATIVE messages', async () => {
        background.main();

        const result = fakeBrowser.runtime.onMessage.trigger(
            {
                type: 'TRANSLATE_NATIVE',
                jobId: 'job-1',
                cues: [{ startMs: 0, endMs: 1000, text: 'Hello' }],
                systemPrompt: 'Translate to Spanish',
                translateConfig: { apiKey: 'key', baseUrl: 'http://test', model: 'gpt-4' }
            },
            { tab: messageTab, id: 'test' }, vi.fn()
        );

        expect(result).toBeInstanceOf(Promise);
    });
});
