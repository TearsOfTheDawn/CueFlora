import { describe, it, expect, beforeEach } from 'vitest';
import { defaults, preset, validateAppearance, appearanceTop, appearanceScale, migrateAppearance, loadAppearance, APPEARANCE_KEY, styleAppearance } from '../appearance';
describe('appearance model',()=>{
    beforeEach(()=>localStorage.clear());
    it('clamps invalid values and rejects arbitrary CSS',()=>{
        const v=validateAppearance({sourceSize:999,position:-10,background:'url(bad)',sourceFont:'evil',highlight:'yes'});
        expect(v.sourceSize).toBe(48); expect(v.position).toBe(0); expect(v.background).toBe('#080808'); expect(v.sourceFont).toBe('sans'); expect(v.highlight).toBe(true);
    });
    it('preserves aids and position except intentional learning overrides',()=>{
        const old={...defaults(),position:42,highlight:false,pinyin:false};
        expect(preset('Classic',old)).toMatchObject({position:42,highlight:false,pinyin:false});
        expect(preset('Language learning',old)).toMatchObject({position:42,highlight:true,pinyin:true});
    });
    it('preserves a stable bottom anchor with changing cue heights',()=>{
        expect(appearanceTop(720,40,50)+40).toBe(appearanceTop(720,120,50)+120);
        expect(appearanceTop(720,1000,50)).toBe(12);
        expect(appearanceTop(720,100,100)).toBe(12);
    });
    it('bounds responsive scale',()=>{expect(appearanceScale(100)).toBe(.75);expect(appearanceScale(720)).toBe(1);expect(appearanceScale(3000)).toBe(2);});
    it('migrates legacy zeros without fallback or deleting keys',()=>{
        localStorage.setItem('cueflora_overlay_bottom','0');localStorage.setItem('cueflora_sub_bg_opacity','0');
        expect(migrateAppearance(localStorage,720)).toMatchObject({position:0,opacity:0});
        expect(localStorage.getItem('cueflora_overlay_bottom')).toBe('0');
    });
    it('rejects malformed or unknown-version storage',()=>{
        localStorage.setItem(APPEARANCE_KEY,'bad');expect(loadAppearance(localStorage)).toBeNull();
        localStorage.setItem(APPEARANCE_KEY,'{"version":2}');expect(loadAppearance(localStorage)).toBeNull();
    });
    it('maps styles independently without touching content',()=>{
        const element=document.createElement('div');element.textContent='unchanged';
        styleAppearance(element,{...defaults(),sourceSize:30,translationSize:14},720);
        expect(element.style.getPropertyValue('--cueflora-appearance-source-size')).toBe('30px');expect(element.style.getPropertyValue('--cueflora-appearance-translation-size')).toBe('14px');expect(element.textContent).toBe('unchanged');
    });
});
