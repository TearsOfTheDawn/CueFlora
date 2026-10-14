import type { Language } from './types';

export const STORAGE_PREFIX = 'cueflora_';

// Translation Defaults (Chat Completions)
export const DEFAULT_TRANSLATION_URL = '';
export const DEFAULT_TRANSLATION_MODEL = '';

// Contextual subtitle translation. The model only generates the central output
// window; nearby source/finalized translation lines are supplied as read-only
// context by api.ts. Keeping generation windows modest is especially important
// for local 7B-class models, while the context windows preserve continuity.
export const DEFAULT_TRANSLATION_BATCH_SIZE = 30;
export const DEFAULT_TRANSLATION_MAX_PARALLEL = 1;
export const TRANSLATION_PREVIOUS_CONTEXT_CUES = 8;
export const TRANSLATION_FORWARD_CONTEXT_CUES = 4;
export const TRANSLATION_MAX_BATCH_SOURCE_CHARS = 2400;
export const TRANSLATION_MAX_RECOVERY_SPLIT_DEPTH = 2;
export const TRANSLATION_MAX_CALLS_PER_BATCH = 8;
export const TRANSLATION_CACHE_SCHEMA_VERSION = 2;
export const TRANSLATION_PIPELINE_VERSION = 'contextual-v5-asr-normalization';
export const TRANSCRIPTION_NORMALIZATION_VERSION = 'asr-v2-punctuation-ownership';

// Subtitle display
export const DEFAULT_SUBTITLE_BG_OPACITY = 75;

// Transcription Defaults (Whisper)
export const DEFAULT_TRANSCRIPTION_URL = '';
export const DEFAULT_TRANSCRIPTION_MODEL = '';
export const DEFAULT_TRANSCRIPTION_MAX_PARALLEL = 4;
export const DEFAULT_TRANSCRIPTION_MB_PER_REQ = 25;

// Unified language list with bidirectional ISO 639-1 ↔ IETF BCP 47 mapping.
// - iso: { code, whisper } — ISO 639-1 code (null if none) + whether Whisper supports it
// - bcp47: IETF BCP 47 language tag (ISO 639-1 with optional region/script subtags, e.g. zh-HK, fr-CA)
//          Used by YouTube and Google APIs. null = transcription-only (no YouTube track).
// - iso_default: true if this is the default BCP 47 variant for a shared ISO code
// - whisper_variant_prompt: prompt to nudge Whisper toward the correct variant
//
// Sources:
//   Audio (Whisper): https://developers.openai.com/api/docs/guides/speech-to-text#supported-languages
//   Text (BCP 47):   https://developers.google.com/workspace/admin/directory/v1/languages
//
// Mapping notes:
//   he (ISO) ↔ iw (BCP 47): ISO revised Hebrew code; Google still uses legacy 'iw'
//   tl (ISO) ↔ fil (BCP 47): Tagalog is the basis of Filipino
//   zh (ISO) → zh-CN/zh-TW/zh-HK: single ISO code, BCP 47 subtags distinguish region/script
//   pt (ISO) → pt-BR/pt-PT: single ISO code, default is Brazilian (more speakers)
//
// For the approach of using different prompts to get different language
// variants from Whisper, see https://github.com/openai/whisper/discussions/277.
export const LANGUAGES: Language[] = [
    { name: 'Afrikaans', iso: { code: 'af', whisper: true }, bcp47: 'af' },
    { name: 'Albanian', iso: { code: 'sq', whisper: false }, bcp47: 'sq' },
    { name: 'Amharic', iso: { code: 'am', whisper: false }, bcp47: 'am' },
    { name: 'Arabic', iso: { code: 'ar', whisper: true }, bcp47: 'ar' },
    { name: 'Armenian', iso: { code: 'hy', whisper: true }, bcp47: 'hy' },
    { name: 'Assamese', iso: { code: 'as', whisper: false }, bcp47: 'as' },
    { name: 'Azerbaijani', iso: { code: 'az', whisper: true }, bcp47: 'az' },
    { name: 'Basque', iso: { code: 'eu', whisper: false }, bcp47: 'eu' },
    { name: 'Belarusian', iso: { code: 'be', whisper: true }, bcp47: null },
    { name: 'Bengali', iso: { code: 'bn', whisper: false }, bcp47: 'bn' },
    { name: 'Bosnian', iso: { code: 'bs', whisper: true }, bcp47: null },
    { name: 'Bulgarian', iso: { code: 'bg', whisper: true }, bcp47: 'bg' },
    { name: 'Burmese', iso: { code: 'my', whisper: false }, bcp47: 'my' },
    { name: 'Catalan', iso: { code: 'ca', whisper: true }, bcp47: 'ca' },
    { name: 'Cherokee', iso: { code: null, whisper: false }, bcp47: 'chr' },
    { name: 'Chinese (Hong Kong)', iso: { code: 'zh', whisper: true }, bcp47: 'zh-HK',
      whisper_variant_prompt: '以下內容為廣東話，請使用繁體字轉錄。' },
    { name: 'Chinese (Simplified)', iso: { code: 'zh', whisper: true }, bcp47: 'zh-CN', iso_default: true,
      whisper_variant_prompt: '以下内容为普通话，请使用简体字转录。' },
    { name: 'Chinese (Traditional)', iso: { code: 'zh', whisper: true }, bcp47: 'zh-TW',
      whisper_variant_prompt: '以下內容為國語，請使用繁體字轉錄。' },
    { name: 'Croatian', iso: { code: 'hr', whisper: true }, bcp47: 'hr' },
    { name: 'Czech', iso: { code: 'cs', whisper: true }, bcp47: 'cs' },
    { name: 'Danish', iso: { code: 'da', whisper: true }, bcp47: 'da' },
    { name: 'Dutch', iso: { code: 'nl', whisper: true }, bcp47: 'nl' },
    { name: 'English (UK)', iso: { code: 'en', whisper: true }, bcp47: 'en-GB',
      whisper_variant_prompt: 'This audio is in British English. Please transcribe using British English spelling.' },
    { name: 'English (US)', iso: { code: 'en', whisper: true }, bcp47: 'en', iso_default: true },
    { name: 'Estonian', iso: { code: 'et', whisper: true }, bcp47: 'et' },
    { name: 'Filipino', iso: { code: 'tl', whisper: true }, bcp47: 'fil' },
    { name: 'Finnish', iso: { code: 'fi', whisper: true }, bcp47: 'fi' },
    { name: 'French', iso: { code: 'fr', whisper: true }, bcp47: 'fr', iso_default: true },
    { name: 'French (Canada)', iso: { code: 'fr', whisper: true }, bcp47: 'fr-CA',
      whisper_variant_prompt: 'Ce contenu est en français canadien. Veuillez transcrire en utilisant les conventions du français québécois.' },
    { name: 'Galician', iso: { code: 'gl', whisper: true }, bcp47: 'gl' },
    { name: 'Georgian', iso: { code: 'ka', whisper: false }, bcp47: 'ka' },
    { name: 'German', iso: { code: 'de', whisper: true }, bcp47: 'de' },
    { name: 'Greek', iso: { code: 'el', whisper: true }, bcp47: 'el' },
    { name: 'Gujarati', iso: { code: 'gu', whisper: false }, bcp47: 'gu' },
    { name: 'Hebrew', iso: { code: 'he', whisper: true }, bcp47: 'iw' },
    { name: 'Hindi', iso: { code: 'hi', whisper: true }, bcp47: 'hi' },
    { name: 'Hungarian', iso: { code: 'hu', whisper: true }, bcp47: 'hu' },
    { name: 'Icelandic', iso: { code: 'is', whisper: true }, bcp47: 'is' },
    { name: 'Indonesian', iso: { code: 'id', whisper: true }, bcp47: 'id' },
    { name: 'Irish', iso: { code: 'ga', whisper: false }, bcp47: 'ga' },
    { name: 'Italian', iso: { code: 'it', whisper: true }, bcp47: 'it' },
    { name: 'Japanese', iso: { code: 'ja', whisper: true }, bcp47: 'ja' },
    { name: 'Kannada', iso: { code: 'kn', whisper: true }, bcp47: 'kn' },
    { name: 'Kazakh', iso: { code: 'kk', whisper: true }, bcp47: 'kk' },
    { name: 'Khmer', iso: { code: 'km', whisper: false }, bcp47: 'km' },
    { name: 'Korean', iso: { code: 'ko', whisper: true }, bcp47: 'ko' },
    { name: 'Lao', iso: { code: 'lo', whisper: false }, bcp47: 'lo' },
    { name: 'Latvian', iso: { code: 'lv', whisper: true }, bcp47: 'lv' },
    { name: 'Lithuanian', iso: { code: 'lt', whisper: true }, bcp47: 'lt' },
    { name: 'Macedonian', iso: { code: 'mk', whisper: true }, bcp47: 'mk' },
    { name: 'Malay', iso: { code: 'ms', whisper: true }, bcp47: 'ms' },
    { name: 'Malayalam', iso: { code: 'ml', whisper: false }, bcp47: 'ml' },
    { name: 'Maori', iso: { code: 'mi', whisper: true }, bcp47: null },
    { name: 'Marathi', iso: { code: 'mr', whisper: true }, bcp47: 'mr' },
    { name: 'Mongolian', iso: { code: 'mn', whisper: false }, bcp47: 'mn' },
    { name: 'Nepali', iso: { code: 'ne', whisper: true }, bcp47: 'ne' },
    { name: 'Norwegian', iso: { code: 'no', whisper: true }, bcp47: 'no' },
    { name: 'Oriya', iso: { code: 'or', whisper: false }, bcp47: 'or' },
    { name: 'Persian', iso: { code: 'fa', whisper: true }, bcp47: 'fa' },
    { name: 'Polish', iso: { code: 'pl', whisper: true }, bcp47: 'pl' },
    { name: 'Portuguese (Brazil)', iso: { code: 'pt', whisper: true }, bcp47: 'pt-BR', iso_default: true,
      whisper_variant_prompt: 'Este conteúdo está em português brasileiro. Transcreva usando o português do Brasil.' },
    { name: 'Portuguese (Portugal)', iso: { code: 'pt', whisper: true }, bcp47: 'pt-PT',
      whisper_variant_prompt: 'Este conteúdo está em português europeu. Transcreva utilizando as convenções do português de Portugal.' },
    { name: 'Punjabi', iso: { code: 'pa', whisper: false }, bcp47: 'pa' },
    { name: 'Romanian', iso: { code: 'ro', whisper: true }, bcp47: 'ro' },
    { name: 'Russian', iso: { code: 'ru', whisper: true }, bcp47: 'ru' },
    { name: 'Serbian', iso: { code: 'sr', whisper: true }, bcp47: 'sr' },
    { name: 'Sinhala', iso: { code: 'si', whisper: false }, bcp47: 'si' },
    { name: 'Slovak', iso: { code: 'sk', whisper: true }, bcp47: 'sk' },
    { name: 'Slovenian', iso: { code: 'sl', whisper: true }, bcp47: 'sl' },
    { name: 'Spanish', iso: { code: 'es', whisper: true }, bcp47: 'es', iso_default: true },
    { name: 'Spanish (Latin America)', iso: { code: 'es', whisper: true }, bcp47: 'es-419',
      whisper_variant_prompt: 'Este contenido está en español latinoamericano. Transcribe usando convenciones del español de América Latina.' },
    { name: 'Swahili', iso: { code: 'sw', whisper: true }, bcp47: 'sw' },
    { name: 'Swedish', iso: { code: 'sv', whisper: true }, bcp47: 'sv' },
    { name: 'Tamil', iso: { code: 'ta', whisper: true }, bcp47: 'ta' },
    { name: 'Telugu', iso: { code: 'te', whisper: false }, bcp47: 'te' },
    { name: 'Thai', iso: { code: 'th', whisper: true }, bcp47: 'th' },
    { name: 'Turkish', iso: { code: 'tr', whisper: true }, bcp47: 'tr' },
    { name: 'Ukrainian', iso: { code: 'uk', whisper: true }, bcp47: 'uk' },
    { name: 'Urdu', iso: { code: 'ur', whisper: true }, bcp47: 'ur' },
    { name: 'Uzbek', iso: { code: 'uz', whisper: false }, bcp47: 'uz' },
    { name: 'Vietnamese', iso: { code: 'vi', whisper: true }, bcp47: 'vi' },
    { name: 'Welsh', iso: { code: 'cy', whisper: true }, bcp47: 'cy' },
    { name: 'Zulu', iso: { code: 'zu', whisper: false }, bcp47: 'zu' }
];

export function langByBcp47(codeBcp47: string | null): Language | null {
    if (!codeBcp47) return null;
    return LANGUAGES.find((l) => l.bcp47 === codeBcp47) || null;
}

export function langByIso(codeIso: string | null): Language | null {
    if (!codeIso) return null;
    return LANGUAGES.find((l) => l.iso.code === codeIso && l.iso_default) ||
           LANGUAGES.find((l) => l.iso.code === codeIso) || null;
}

export function resolveTranscriptionLang(value: string | null): Language | null {
    if (!value) return null;
    if (value.startsWith('transcription:')) {
        const code = value.split(':')[1];
        return langByBcp47(code) || langByIso(code);
    }
    return langByBcp47(value) || langByIso(value);
}
