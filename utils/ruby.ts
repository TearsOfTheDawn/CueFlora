import { preferences as preferenceStorage } from './preferenceClient';
import { pinyin } from 'pinyin-pro';
import { STORAGE_PREFIX } from './constants';
import { getEffectiveAppearance } from './appearance';

type RubyProvider = (text: string) => string;

const RUBY_PROVIDERS: Record<string, RubyProvider> = {};

/** Display path: subtitle content is always text, never interpreted as markup. */
export function createRubyNodes(text: string, isoCode: string | null): DocumentFragment {
    const fragment = document.createDocumentFragment();
    const enabled = getEffectiveAppearance()?.pinyin ?? (preferenceStorage.getItem(STORAGE_PREFIX + 'ruby_zh') === '1');
    if (isoCode !== 'zh' || !enabled) {
        fragment.append(document.createTextNode(text));
        return fragment;
    }
    for (const token of pinyin(text, { type: 'all', toneType: 'symbol' })) {
        if (!token.isZh) {
            fragment.append(document.createTextNode(token.origin));
            continue;
        }
        const ruby = document.createElement('ruby');
        ruby.className = 'cueflora-ruby-item';
        const base = document.createElement('span');
        base.className = 'cueflora-ruby-zh';
        base.textContent = token.origin;
        const annotation = document.createElement('rt');
        annotation.className = 'cueflora-ruby-py';
        annotation.textContent = token.pinyin;
        const open = document.createElement('rp');
        open.textContent = '(';
        const close = document.createElement('rp');
        close.textContent = ')';
        ruby.append(base, open, annotation, close);
        fragment.append(ruby);
    }
    return fragment;
}

export function registerRubyProvider(isoCode: string, provider: RubyProvider): void {
    RUBY_PROVIDERS[isoCode] = provider;
}

/** Legacy string API; production display callers must use createRubyNodes. */
export function applyRuby(text: string, isoCode: string | null): string {
    if (!text || !isoCode) return text;
    const provider = RUBY_PROVIDERS[isoCode];
    if (!provider) return text;
    const key = STORAGE_PREFIX + 'ruby_' + isoCode;
    const appearance = getEffectiveAppearance();
    if (!(isoCode === 'zh' && appearance ? appearance.pinyin : preferenceStorage.getItem(key) === '1')) return text;
    return provider(text);
}

// Chinese Pinyin provider
registerRubyProvider('zh', (text: string) => {
    const container = document.createElement('span');
    container.append(createRubyNodes(text, 'zh'));
    return container.innerHTML;
});
