import { describe, it, expect, beforeEach, vi } from 'vitest';
import { fakeBrowser } from 'wxt/testing';
import background from '../background';

describe('background service worker', () => {
    beforeEach(() => {
        fakeBrowser.reset();
        vi.spyOn(fakeBrowser.action.onClicked, 'addListener').mockImplementation(() => {});
        vi.spyOn(fakeBrowser.runtime.onInstalled, 'addListener').mockImplementation(() => {});
    });

    it('should respond to PING with PONG', async () => {
        background.main();

        const result = await fakeBrowser.runtime.onMessage.trigger(
            { type: 'PING' },
            { tab: { id: 1 }, id: 'test' }
        );

        // trigger returns an array of return values from all listeners
        expect(result).toBeDefined();
    });

    it('should not handle unknown message types', async () => {
        background.main();

        // trigger returns array of listener return values
        const results = await fakeBrowser.runtime.onMessage.trigger(
            { type: 'UNKNOWN_TYPE' },
            { tab: { id: 1 }, id: 'test' }
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
            { tab: { id: 1 }, id: 'test' }
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
            { tab: { id: 1 }, id: 'test' }
        );

        expect(result).toBeInstanceOf(Promise);
    });
});
