/** Presentation only: never reads or changes subtitle cues or processing state. */
export const APPEARANCE_KEY = 'cueflora_appearance_v1';
export interface SubtitleAppearanceSettings {
    version: 1;
    sourceSize: number; translationSize: number;
    sourceFont: 'sans' | 'serif' | 'mono'; translationFont: 'sans' | 'serif' | 'mono';
    sourceBold: boolean; translationBold: boolean;
    sourceColor: string; translationColor: string;
    outlineColor: string; outline: number; shadow: 'off' | 'soft' | 'strong';
    background: string; opacity: number; paddingX: number; paddingY: number; radius: number;
    order: 'source' | 'translation'; align: 'center' | 'left'; width: number; lineHeight: number; gap: number;
    position: number; highlight: boolean; highlightColor: string; pinyin: boolean; pinyinSize: number;
}
export const defaults = (): SubtitleAppearanceSettings => ({
    version: 1, sourceSize: 22, translationSize: 18, sourceFont: 'sans', translationFont: 'sans',
    sourceBold: true, translationBold: false, sourceColor: '#ffffff', translationColor: '#dddddd',
    outlineColor: '#000000', outline: 0, shadow: 'soft', background: '#080808', opacity: 75,
    paddingX: 10, paddingY: 4, radius: 6, order: 'source', align: 'center', width: 80,
    lineHeight: 1.3, gap: 4, position: 0, highlight: true, highlightColor: '#ffd700', pinyin: false, pinyinSize: 50,
});
export const ranges: Partial<Record<keyof SubtitleAppearanceSettings, [number, number, number]>> = {
    sourceSize: [12,48,1], translationSize: [12,48,1], outline: [0,3,.5], opacity: [0,100,1],
    paddingX: [0,20,1], paddingY: [0,20,1], radius: [0,16,1], width: [40,95,1],
    lineHeight: [1.1,1.8,.1], gap: [0,20,1], position: [0,100,1], pinyinSize: [40,70,1],
};
const choices: Record<string, string[]> = { sourceFont: ['sans','serif','mono'], translationFont: ['sans','serif','mono'],
    shadow: ['off','soft','strong'], order: ['source','translation'], align: ['center','left'] };
export function validateAppearance(value: unknown): SubtitleAppearanceSettings {
    const result = defaults();
    if (!value || typeof value !== 'object') return result;
    const input = value as Record<string, unknown>;
    for (const key of Object.keys(result) as (keyof SubtitleAppearanceSettings)[]) {
        const v = input[key]; const fallback = result[key]; const range = ranges[key];
        if (range && typeof v === 'number' && Number.isFinite(v)) Object.assign(result, { [key]: Math.max(range[0], Math.min(range[1], v)) });
        else if (typeof fallback === 'boolean' && typeof v === 'boolean') Object.assign(result, { [key]: v });
        else if (typeof fallback === 'string' && typeof v === 'string' && (choices[key]?.includes(v) || (!choices[key] && /^#[\da-f]{6}$/i.test(v)))) Object.assign(result, { [key]: v });
    }
    return result;
}
export function preset(name: string, previous: SubtitleAppearanceSettings): SubtitleAppearanceSettings {
    const next = { ...defaults(), position: previous.position, highlight: previous.highlight, pinyin: previous.pinyin };
    if (name === 'Clean outline') Object.assign(next, { sourceSize:24, translationSize:20, translationColor:'#ffffff', opacity:0, outline:2, shadow:'off' });
    if (name === 'High contrast') Object.assign(next, { sourceSize:28, translationSize:24, translationColor:'#ffffff', background:'#000000', opacity:90, radius:4, shadow:'off' });
    if (name === 'Language learning') Object.assign(next, { sourceSize:28, translationSize:20, opacity:80, lineHeight:1.5, gap:8, highlight:true, pinyin:true });
    return next;
}
export function loadAppearance(storage: Pick<Storage, 'getItem'>): SubtitleAppearanceSettings | null {
    try { const value = JSON.parse(storage.getItem(APPEARANCE_KEY) || 'null'); return value?.version === 1 ? validateAppearance(value) : null; } catch { return null; }
}
export function migrateAppearance(storage: Pick<Storage, 'getItem'>, height: number): SubtitleAppearanceSettings {
    const next = defaults();
    const numeric = (key: string, fallback: number) => { const raw = storage.getItem('cueflora_'+key); const n = Number(raw); return raw !== null && Number.isFinite(n) ? n : fallback; };
    next.opacity = numeric('sub_bg_opacity',75);
    next.highlight = storage.getItem('cueflora_highlight_current_word') !== '0';
    next.pinyin = storage.getItem('cueflora_ruby_zh') === '1';
    // Legacy block bottom = H - offset - 10px overlay padding - 2px margin.
    next.position = (numeric('overlay_bottom',60) + 12 - 48) / (height - 60) * 100;
    return validateAppearance(next);
}
export const appearanceScale = (height: number): number => Math.max(.75, Math.min(2, height / 720));
export function appearanceTop(height: number, blockHeight: number, position: number): number {
    const bottom = height - 48;
    const anchor = bottom - position / 100 * (bottom - 12);
    return Math.max(12, Math.min(bottom - blockHeight, anchor - blockHeight));
}
const fonts: Record<string,string> = {
    sans: 'Arial, "Noto Sans CJK SC", "Microsoft YaHei", sans-serif',
    serif: 'Georgia, "Noto Serif CJK SC", SimSun, serif', mono: 'Consolas, "Noto Sans Mono CJK SC", monospace',
};
export function styleAppearance(element: HTMLElement, value: SubtitleAppearanceSettings, height: number): void {
    const s = appearanceScale(height); const px = (v:number) => `${v*s}px`;
    const vars: Record<string,string> = {
        'source-size':px(value.sourceSize), 'translation-size':px(value.translationSize),
        'source-font':fonts[value.sourceFont], 'translation-font':fonts[value.translationFont],
        'source-weight':value.sourceBold?'700':'400', 'translation-weight':value.translationBold?'700':'400',
        'source-color':value.sourceColor, 'translation-color':value.translationColor,
        outline:`${px(value.outline)} ${value.outlineColor}`, shadow:value.shadow === 'off'?'none':`0 0 ${px(value.shadow === 'strong'?8:4)} rgba(0,0,0,.9)`,
        background:`${value.background}${Math.round(value.opacity/100*255).toString(16).padStart(2,'0')}`,
        'padding-x':px(value.paddingX), 'padding-y':px(value.paddingY), radius:px(value.radius),
        width:`${value.width}%`, align:value.align, 'line-height':String(value.lineHeight), gap:px(value.gap),
        highlight:value.highlightColor, pinyin:`${value.pinyinSize/100}em`,
        'source-order':value.order==='source'?'0':'1', 'translation-order':value.order==='source'?'1':'0',
    };
    for (const [key,v] of Object.entries(vars)) element.style.setProperty('--cueflora-appearance-'+key,v);
}
let effective: SubtitleAppearanceSettings | null = null;
export const getEffectiveAppearance = (): SubtitleAppearanceSettings | null => effective;
export const setEffectiveAppearance = (value: SubtitleAppearanceSettings | null): void => { effective = value; };
