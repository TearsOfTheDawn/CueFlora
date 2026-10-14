import { describe, it, expect } from 'vitest';
import { LANGUAGES, langByBcp47, langByIso, resolveTranscriptionLang, STORAGE_PREFIX } from '../constants';
import type { Language } from '../types';

describe('LANGUAGES array integrity', () => {
    it('should have a non-empty array of languages', () => {
        expect(LANGUAGES.length).toBeGreaterThan(50);
    });

    it('should have unique BCP 47 codes (no duplicates among non-null)', () => {
        const bcp47Codes = LANGUAGES.filter((l: Language) => l.bcp47).map((l: Language) => l.bcp47);
        const unique = new Set(bcp47Codes);
        expect(unique.size).toBe(bcp47Codes.length);
    });

    it('should have a name for every language entry', () => {
        LANGUAGES.forEach((l: Language) => {
            expect(l.name).toBeTruthy();
        });
    });

    it('should have iso.whisper boolean for every entry', () => {
        LANGUAGES.forEach((l: Language) => {
            expect(typeof l.iso.whisper).toBe('boolean');
        });
    });

    it('should have exactly one iso_default per shared ISO code', () => {
        const isoGroups: Record<string, Language[]> = {};
        LANGUAGES.forEach((l: Language) => {
            if (!l.iso.code) return;
            if (!isoGroups[l.iso.code]) isoGroups[l.iso.code] = [];
            isoGroups[l.iso.code].push(l);
        });
        Object.keys(isoGroups).forEach((code: string) => {
            const group = isoGroups[code];
            if (group.length > 1) {
                const defaults = group.filter((l: Language) => l.iso_default);
                expect(defaults.length).toBe(1);
            }
        });
    });

    it('should include well-known languages', () => {
        expect(langByBcp47('en')).toBeTruthy();
        expect(langByBcp47('es')).toBeTruthy();
        expect(langByBcp47('ja')).toBeTruthy();
        expect(langByBcp47('zh-CN')).toBeTruthy();
    });
});

describe('langByBcp47', () => {
    it('should find English (US) by bcp47', () => {
        const result = langByBcp47('en');
        expect(result).toBeTruthy();
        expect(result!.name).toBe('English (US)');
    });

    it('should find Chinese (Simplified) by zh-CN', () => {
        const result = langByBcp47('zh-CN');
        expect(result).toBeTruthy();
        expect(result!.name).toBe('Chinese (Simplified)');
    });

    it('should return null for unknown code', () => {
        expect(langByBcp47('xx-YY')).toBeNull();
    });

    it('should return null for null/undefined input', () => {
        expect(langByBcp47(null)).toBeNull();
        expect(langByBcp47(undefined as any)).toBeNull();
    });

    it('should find Hebrew via legacy bcp47 code "iw"', () => {
        const result = langByBcp47('iw');
        expect(result).toBeTruthy();
        expect(result!.name).toBe('Hebrew');
        expect(result!.iso.code).toBe('he');
    });

    it('should find Filipino via "fil"', () => {
        const result = langByBcp47('fil');
        expect(result).toBeTruthy();
        expect(result!.name).toBe('Filipino');
        expect(result!.iso.code).toBe('tl');
    });
});

describe('langByIso', () => {
    it('should find English by ISO code "en"', () => {
        const result = langByIso('en');
        expect(result).toBeTruthy();
        expect(result!.name).toBe('English (US)');
        expect(result!.iso_default).toBe(true);
    });

    it('should prefer iso_default variant for shared codes', () => {
        const zh = langByIso('zh');
        expect(zh).toBeTruthy();
        expect(zh!.name).toBe('Chinese (Simplified)');
        expect(zh!.iso_default).toBe(true);

        const pt = langByIso('pt');
        expect(pt).toBeTruthy();
        expect(pt!.name).toBe('Portuguese (Brazil)');
        expect(pt!.iso_default).toBe(true);

        const es = langByIso('es');
        expect(es).toBeTruthy();
        expect(es!.name).toBe('Spanish');
        expect(es!.iso_default).toBe(true);
    });

    it('should return null for unknown code', () => {
        expect(langByIso('xx')).toBeNull();
    });

    it('should return null for null/undefined', () => {
        expect(langByIso(null)).toBeNull();
        expect(langByIso(undefined as any)).toBeNull();
    });

    it('should find a language even without iso_default if only one variant', () => {
        const ja = langByIso('ja');
        expect(ja).toBeTruthy();
        expect(ja!.name).toBe('Japanese');
    });
});

describe('resolveTranscriptionLang', () => {
    it('should return null for null/undefined/empty', () => {
        expect(resolveTranscriptionLang(null)).toBeNull();
        expect(resolveTranscriptionLang(undefined as any)).toBeNull();
        expect(resolveTranscriptionLang('')).toBeNull();
    });

    it('should resolve a plain bcp47 code', () => {
        const result = resolveTranscriptionLang('en');
        expect(result).toBeTruthy();
        expect(result!.name).toBe('English (US)');
    });

    it('should resolve a plain ISO code', () => {
        const result = resolveTranscriptionLang('ja');
        expect(result).toBeTruthy();
        expect(result!.name).toBe('Japanese');
    });

    it('should resolve a "transcription:" prefixed bcp47 code', () => {
        const result = resolveTranscriptionLang('transcription:zh-CN');
        expect(result).toBeTruthy();
        expect(result!.name).toBe('Chinese (Simplified)');
    });

    it('should resolve a "transcription:" prefixed ISO code', () => {
        const result = resolveTranscriptionLang('transcription:fr');
        expect(result).toBeTruthy();
        expect(result!.name).toBe('French');
    });

    it('should return null for unknown transcription code', () => {
        expect(resolveTranscriptionLang('transcription:zzzz')).toBeNull();
    });

    it('should prefer bcp47 match over ISO match', () => {
        // 'fil' is bcp47 for Filipino (iso code 'tl')
        const result = resolveTranscriptionLang('fil');
        expect(result).toBeTruthy();
        expect(result!.name).toBe('Filipino');
    });
});

describe('STORAGE_PREFIX', () => {
    it('should be a non-empty string', () => {
        expect(typeof STORAGE_PREFIX).toBe('string');
        expect(STORAGE_PREFIX.length).toBeGreaterThan(0);
    });
});
