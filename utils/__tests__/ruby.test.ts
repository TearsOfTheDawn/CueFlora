vi.mock('../preferenceClient', () => ({
    preferences: { getItem: (key: string) => window.localStorage.getItem(key), setItem: (key: string, value: string) => window.localStorage.setItem(key,value) },
    initializePreferences: async () => {},
    savePreference: async (key: string, value: string) => window.localStorage.setItem(key,value),
}));
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { applyRuby, registerRubyProvider } from '../ruby';
import { STORAGE_PREFIX } from '../constants';

describe('applyRuby', () => {
    beforeEach(() => {
        localStorage.clear();
    });

    it('should return text unchanged when no provider is registered for the language', () => {
        expect(applyRuby('hello', 'xx')).toBe('hello');
    });

    it('should return text unchanged when text is null/empty', () => {
        expect(applyRuby(null as any, 'en')).toBeNull();
        expect(applyRuby('', 'en')).toBe('');
    });

    it('should return text unchanged when isoCode is null/undefined', () => {
        expect(applyRuby('hello', null)).toBe('hello');
        expect(applyRuby('hello', undefined as any)).toBe('hello');
    });

    it('should return text unchanged when localStorage toggle is not "1"', () => {
        // Chinese provider is registered by ruby.js import, but toggle is off
        expect(applyRuby('你好', 'zh')).toBe('你好');
    });

    it('should apply Chinese pinyin when toggle is enabled', () => {
        localStorage.setItem(`${STORAGE_PREFIX}ruby_zh`, '1');
        const result = applyRuby('你好', 'zh');
        // pinyin-pro wraps characters in span elements with ruby annotations
        expect(result).not.toBe('你好');
        expect(result).toContain('你');
        expect(result).toContain('好');
    });

    it('should use a custom registered provider', () => {
        const mockProvider = vi.fn((text: string): string => `<ruby>${text}</ruby>`);
        registerRubyProvider('test-lang', mockProvider);
        localStorage.setItem(`${STORAGE_PREFIX}ruby_test-lang`, '1');

        const result = applyRuby('hello', 'test-lang');
        expect(mockProvider).toHaveBeenCalledWith('hello');
        expect(result).toBe('<ruby>hello</ruby>');
    });
});

describe('registerRubyProvider', () => {
    it('should allow registering and overriding providers', () => {
        const provider1 = vi.fn((t: string): string => `v1:${t}`);
        const provider2 = vi.fn((t: string): string => `v2:${t}`);

        registerRubyProvider('custom', provider1);
        localStorage.setItem(`${STORAGE_PREFIX}ruby_custom`, '1');

        expect(applyRuby('test', 'custom')).toBe('v1:test');

        registerRubyProvider('custom', provider2);
        expect(applyRuby('test', 'custom')).toBe('v2:test');
    });
});
