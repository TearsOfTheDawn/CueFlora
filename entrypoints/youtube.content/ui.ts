import { preferences as preferenceStorage, initializePreferences, refreshPreferences } from '../../utils/preferenceClient';
import { getProviderSummary, refreshProviderSummary } from '../../utils/providerClient';
import { mountAppearanceEditor } from './appearanceEditor';
import type { CaptionTrack, Language, WorkflowStage } from '../../utils/types';
import { state } from '../../utils/state';
import { navigationGuard } from '../../utils/navigation';
import {
    STORAGE_PREFIX, LANGUAGES, DEFAULT_SUBTITLE_BG_OPACITY,
    langByBcp47, langByIso, resolveTranscriptionLang
} from '../../utils/constants';
import { isWorkflowBusy, resetWorkflow, WORKFLOW_CHANGED_EVENT } from '../../utils/workflow';
import { startRenderLoop, applyOverlaySettings, runSubtitleWorkflow } from './render';
import { trustedRun } from '../../utils/userRun';

const renderWorkflowProgress = (): void => {
    const container = document.getElementById('cueflora-workflow-progress');
    if (!container) return;

    const stages: WorkflowStage[] = ['transcription', 'translation'];
    const anyVisible = stages.some((stage) => state.workflow[stage].status !== 'idle');
    container.style.display = anyVisible ? 'block' : 'none';

    let firstError: string | null = null;
    let activeMessage: string | null = null;
    let allFinished = anyVisible;

    for (const stage of stages) {
        const s = state.workflow[stage];
        const labelEl = document.getElementById(`cueflora-progress-${stage}-message`);
        const percentEl = document.getElementById(`cueflora-progress-${stage}-percent`);
        const barEl = document.getElementById(`cueflora-progress-${stage}-bar`) as HTMLElement | null;
        const rowEl = document.getElementById(`cueflora-progress-${stage}-row`) as HTMLElement | null;

        const defaultMessage =
            s.status === 'waiting' ? 'waiting' :
            s.status === 'running' ? 'working…' :
            s.status === 'done' ? 'complete' :
            s.status === 'error' ? 'failed' :
            s.status === 'skipped' ? 'not requested' : '';

        if (labelEl) labelEl.innerText = s.message || defaultMessage;
        if (percentEl) {
            percentEl.innerText = s.percent != null
                ? `${s.percent}%`
                : (s.status === 'done' ? '100%' : '');
        }

        if (barEl) {
            const width =
                s.status === 'done' ? 100 :
                s.status === 'skipped' ? 100 :
                s.percent != null ? s.percent :
                s.status === 'running' ? 8 : 0;
            barEl.style.width = `${width}%`;
            barEl.style.opacity =
                s.status === 'waiting' || s.status === 'idle' ? '0.25' :
                s.status === 'skipped' ? '0.35' : '1';
        }

        if (rowEl) {
            rowEl.style.opacity = s.status === 'idle' ? '0.45' : '1';
        }

        if (s.status === 'error' && !firstError) {
            firstError = s.message || `${stage} failed`;
        }
        if (s.status === 'running' && !activeMessage) {
            activeMessage = `${stage}: ${s.message || 'working…'}`;
        }
        if (!['done', 'skipped', 'idle'].includes(s.status)) {
            allFinished = false;
        }
    }

    const statusEl = document.getElementById('cueflora-status');
    if (statusEl) {
        if (firstError) {
            statusEl.innerText = `Error: ${firstError}`;
            statusEl.style.whiteSpace = 'pre-wrap';
        } else if (activeMessage) {
            statusEl.innerText = activeMessage;
            statusEl.style.whiteSpace = 'normal';
        } else if (state.workflow.status === 'cancelled') {
            statusEl.innerText = 'Workflow cancelled.';
            statusEl.style.whiteSpace = 'normal';
        } else if (allFinished && state.workflow.status === 'complete') {
            statusEl.innerText = 'Workflow complete.';
            statusEl.style.whiteSpace = 'normal';
        }
    }

    const busy = isWorkflowBusy();
    const runButton = document.getElementById('cueflora-run-workflow') as HTMLButtonElement | null;
    const transcriptionSelect = document.getElementById('cueflora-transcription-lang') as HTMLSelectElement | null;
    const translationSelect = document.getElementById('cueflora-translation-lang') as HTMLSelectElement | null;
    if (runButton) {
        runButton.disabled = busy;
        runButton.innerText = busy ? 'running…' : 'run transcription + translation';
    }
    if (transcriptionSelect) transcriptionSelect.disabled = busy;
    if (translationSelect) translationSelect.disabled = busy;
};


const getTrackDisplayName = (t: CaptionTrack): string => {
    const entry = langByBcp47(t.languageCode) || langByIso(t.languageCode);
    if (entry) return entry.name;
    if (t.name && t.name.simpleText) return t.name.simpleText;
    if (t.languageName && t.languageName.simpleText) return t.languageName.simpleText;
    return t.languageCode;
};

export const populateDropdowns = (): void => {
    const transcriptionLangSelect = document.getElementById('cueflora-transcription-lang') as HTMLSelectElement | null;
    const translationLangSelect = document.getElementById('cueflora-translation-lang') as HTMLSelectElement | null;
    const savedTranscriptionLang = preferenceStorage.getItem(`${STORAGE_PREFIX}transcription_lang`);
    const savedTranslationLang = preferenceStorage.getItem(`${STORAGE_PREFIX}translation_lang`);

    if (!transcriptionLangSelect || !translationLangSelect) return;

    // Deduplicate tracks: prefer non-ASR over ASR for same language/display name
    const dedupTracks: CaptionTrack[] = [];
    const seenCodes: Record<string, boolean> = {};
    const seenNames: Record<string, boolean> = {};
    const sorted = state.availableTracks.slice().sort((a: CaptionTrack, b: CaptionTrack): number => {
        if (a.kind === 'asr' && b.kind !== 'asr') return 1;
        if (a.kind !== 'asr' && b.kind === 'asr') return -1;
        return 0;
    });
    sorted.forEach((t: CaptionTrack) => {
        const code = t.languageCode;
        const name = getTrackDisplayName(t);
        if (!seenCodes[code] && !seenNames[name]) {
            dedupTracks.push(t);
            seenCodes[code] = true;
            seenNames[name] = true;
        }
    });

    transcriptionLangSelect.innerHTML = '';
    if (dedupTracks.length > 0) {
        const grpYT = document.createElement('optgroup');
        grpYT.label = 'YouTube Subtitles';
        dedupTracks.forEach((t: CaptionTrack) => {
            const opt = document.createElement('option');
            opt.value = t.languageCode;
            let text = getTrackDisplayName(t);
            if (t.isDefault) text += ' (Default)';
            if (t.kind === 'asr') text += ' (Auto)';
            opt.text = text;
            grpYT.appendChild(opt);
        });
        transcriptionLangSelect.appendChild(grpYT);
    }

    const grpTranscribe = document.createElement('optgroup');
    grpTranscribe.label = 'AI Transcription';
    LANGUAGES.filter((l: Language) => l.iso.whisper).forEach((lang: Language) => {
        const key = lang.bcp47 || lang.iso.code;
        const opt = document.createElement('option');
        opt.value = `transcription:${key}`;
        if (state.generatedTracks[`transcription:${key}`]) {
            opt.text = `[✓] ${lang.name}`;
        } else if (
            state.workflow.status === 'transcribing' &&
            savedTranscriptionLang === `transcription:${key}`
        ) {
            opt.text = `[Transcribing...] ${lang.name}`;
            opt.disabled = true;
        } else {
            opt.text = lang.name;
        }
        grpTranscribe.appendChild(opt);
    });
    transcriptionLangSelect.appendChild(grpTranscribe);

    if (savedTranscriptionLang) transcriptionLangSelect.value = savedTranscriptionLang;

    const actualTranscriptionLang = transcriptionLangSelect.value;
    const transcriptionLangEntry = resolveTranscriptionLang(actualTranscriptionLang || null);
    const transcriptionLangBcp47 = transcriptionLangEntry ? transcriptionLangEntry.bcp47 : null;

    translationLangSelect.innerHTML = '';
    const optNone = document.createElement('option');
    optNone.value = 'none';
    optNone.text = 'None (Disable)';
    translationLangSelect.appendChild(optNone);

    if (dedupTracks.length > 0) {
        const grpAvail = document.createElement('optgroup');
        grpAvail.label = 'YouTube Subtitles';
        dedupTracks.forEach((t: CaptionTrack) => {
            const opt = document.createElement('option');
            opt.value = t.languageCode;
            opt.text = getTrackDisplayName(t);
            grpAvail.appendChild(opt);
        });
        translationLangSelect.appendChild(grpAvail);
    }

    const isTranscriptionSource = actualTranscriptionLang && actualTranscriptionLang.startsWith('transcription:');
    const grpGen = document.createElement('optgroup');
    grpGen.label = isTranscriptionSource ? 'AI Translation (transcription required)' : 'AI Translation';
    LANGUAGES.filter((l: Language) => l.bcp47).forEach((lang: Language) => {
        const opt = document.createElement('option');
        opt.value = `translation:${lang.bcp47}`;
        if (state.generatedTracks[lang.bcp47!]) {
            opt.text = `[✓] ${lang.name}`;
        } else if (
            state.workflow.status === 'translating' &&
            savedTranslationLang === `translation:${lang.bcp47}`
        ) {
            opt.text = `[Translating...] ${lang.name}`;
            opt.disabled = true;
        } else {
            opt.text = lang.name;
        }
        if (transcriptionLangBcp47 && lang.bcp47 === transcriptionLangBcp47) {
            opt.disabled = true;
            opt.style.color = '#666';
        }
        grpGen.appendChild(opt);
    });
    translationLangSelect.appendChild(grpGen);

    if (savedTranslationLang) translationLangSelect.value = savedTranslationLang;


};

export const togglePanel = (): void => {
    const panel = document.getElementById('cueflora-panel');
    if (!panel) return;
    state.isPanelOpen = !state.isPanelOpen;
    if (!state.isPanelOpen) panel.dispatchEvent(new Event('cueflora-panel-close'));
    if (state.isPanelOpen) {
        panel.classList.add('visible');
        populateDropdowns();
        // Keep progress/errors visible when the panel is closed and reopened.
        renderWorkflowProgress();
        panel.dispatchEvent(new Event('cueflora-panel-open'));
    } else {
        panel.classList.remove('visible');
    }
};

export const createUI = async (): Promise<void> => {
    const current = navigationGuard();
    await initializePreferences();
    if (!current()) return;
    await refreshProviderSummary().catch(() => {});
    if (!current()) return;
    const controls = document.querySelector('.ytp-right-controls');
    if (!controls) return;

    // Treat the button + panel as one atomic UI.  Previously the player button was
    // inserted before #movie_player was checked.  On YouTube's SPA navigation
    // there is a short race where the controls exist but the player does not;
    // that left behind an orphan flower button with no click listener or panel.
    // Future createUI() calls then saw the existing button and returned early,
    // making the visible flower button permanently inert for that page.
    const existingBtn = document.getElementById('cueflora-btn');
    const existingPanel = document.getElementById('cueflora-panel');
    if (existingBtn && existingPanel) return;

    if (existingBtn || existingPanel) {
        if (state._cleanupUI) state._cleanupUI();
        existingBtn?.remove();
        existingPanel?.remove();
        state.isPanelOpen = false;
    }

    // Do not create any visible UI until both required YouTube anchors exist.
    // index.ts will retry createUI() while either is still being mounted.
    const player = document.querySelector('#movie_player');
    if (!player) return;

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.setAttribute('aria-label', 'CueFlora subtitles');
    btn.setAttribute('aria-controls', 'cueflora-panel');
    btn.id = 'cueflora-btn';
    btn.className = 'cueflora-btn';
    const flower = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    flower.setAttribute('viewBox', '0 0 128 128'); flower.setAttribute('aria-hidden', 'true');
    flower.setAttribute('width', '22'); flower.setAttribute('height', '22');
    for (const [cx, cy, r] of [[64,32,23],[94,54,23],[83,90,23],[45,90,23],[34,54,23],[64,64,16]]) {
        const circle = document.createElementNS(flower.namespaceURI, 'circle');
        circle.setAttribute('cx', String(cx)); circle.setAttribute('cy', String(cy)); circle.setAttribute('r', String(r));
        circle.setAttribute('fill', 'currentColor'); flower.append(circle);
    }
    btn.append(flower);
    btn.title = 'CueFlora — AI Subtitles & Translation';

    const panel = document.createElement('div');
    panel.id = 'cueflora-panel';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'CueFlora subtitle settings');

    const savedShowTranscription = preferenceStorage.getItem(`${STORAGE_PREFIX}show_transcription`);
    if (savedShowTranscription !== null) state.showTranscription = savedShowTranscription !== '0';
    const savedShowTranslation = preferenceStorage.getItem(`${STORAGE_PREFIX}show_translation`);
    if (savedShowTranslation !== null) state.showTranslation = savedShowTranslation !== '0';
    const savedHighlightCurrentWord = preferenceStorage.getItem(`${STORAGE_PREFIX}highlight_current_word`);
    if (savedHighlightCurrentWord !== null) state.highlightCurrentWord = savedHighlightCurrentWord !== '0';


    const savedOpacity = preferenceStorage.getItem(`${STORAGE_PREFIX}sub_bg_opacity`);
    if (savedOpacity !== null) state.subtitleBgOpacity = parseInt(savedOpacity) || DEFAULT_SUBTITLE_BG_OPACITY;

    const savedOverlayBottom = preferenceStorage.getItem(`${STORAGE_PREFIX}overlay_bottom`);
    if (savedOverlayBottom !== null) state.overlayOffsetBottom = parseInt(savedOverlayBottom) || 60;

    panel.innerHTML =
        '<div class="cueflora-header">' +
            '<span class="cueflora-title">CueFlora</span>' +
            '<div class="cueflora-icons">' +
                '<button type="button" id="cueflora-nav-settings" title="AI settings">AI settings ›</button>' +
                '<button type="button" id="cueflora-nav-home" title="Back" style="display:none">‹ Back</button>' +
                '<button type="button" id="cueflora-close" aria-label="Close">\u00d7</button>' +
            '</div>' +
        '</div>' +
        '<div id="cueflora-view-home" class="cueflora-view active"><h2>Subtitles</h2>' +
            '<div class="cueflora-row">' +
                '<div class="cueflora-row-header">' +
                    '<label class="cueflora-check"><input type="checkbox" id="cueflora-show-transcription"' + (state.showTranscription ? ' checked' : '') + '><span class="cueflora-check-box"></span><span class="cueflora-check-text">transcription language</span></label>' +
                '</div>' +
                '<select id="cueflora-transcription-lang" class="cueflora-select"></select>' +
            '</div>' +
            '<div class="cueflora-row">' +
                '<div class="cueflora-row-header">' +
                    '<label class="cueflora-check"><input type="checkbox" id="cueflora-show-translation"' + (state.showTranslation ? ' checked' : '') + '><span class="cueflora-check-box"></span><span class="cueflora-check-text">translation language</span></label>' +
                '</div>' +
                '<select id="cueflora-translation-lang" class="cueflora-select"></select>' +
            '</div>' +
            '<div class="cueflora-row">' +
                '<button id="cueflora-run-workflow" class="cueflora-select" type="button" ' +
                    'style="cursor:pointer;text-align:center;font-weight:600;">run transcription + translation</button>' +
            '</div>' +
            '<div id="cueflora-workflow-progress" style="display:none;margin:4px 0 6px 0;">' +
                '<div id="cueflora-progress-transcription-row" style="margin-bottom:5px;">' +
                    '<div style="display:grid;grid-template-columns:78px 1fr 38px;gap:6px;align-items:center;font-size:11px;line-height:14px;">' +
                        '<span style="opacity:.8;">transcription</span>' +
                        '<span id="cueflora-progress-transcription-message" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"></span>' +
                        '<span id="cueflora-progress-transcription-percent" style="text-align:right;opacity:.75;"></span>' +
                    '</div>' +
                    '<div style="height:3px;margin-top:2px;background:rgba(255,255,255,.15);border-radius:2px;overflow:hidden;">' +
                        '<div id="cueflora-progress-transcription-bar" style="height:100%;width:0;background:currentColor;transition:width .18s ease;"></div>' +
                    '</div>' +
                '</div>' +
                '<div id="cueflora-progress-translation-row">' +
                    '<div style="display:grid;grid-template-columns:78px 1fr 38px;gap:6px;align-items:center;font-size:11px;line-height:14px;">' +
                        '<span style="opacity:.8;">translation</span>' +
                        '<span id="cueflora-progress-translation-message" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"></span>' +
                        '<span id="cueflora-progress-translation-percent" style="text-align:right;opacity:.75;"></span>' +
                    '</div>' +
                    '<div style="height:3px;margin-top:2px;background:rgba(255,255,255,.15);border-radius:2px;overflow:hidden;">' +
                        '<div id="cueflora-progress-translation-bar" style="height:100%;width:0;background:currentColor;transition:width .18s ease;"></div>' +
                    '</div>' +
                '</div>' +
            '</div>' +
            '<div id="cueflora-status" class="cueflora-status" style="white-space:pre-wrap;"></div>' +
        '</div>' +
        '<div id="cueflora-view-settings" class="cueflora-view"><h2>Provider settings</h2><p>Provider configuration is managed privately in extension settings.</p><button id="cueflora-open-options" type="button">Open extension settings</button></div>';

    // Nothing is inserted before the only asynchronous setup step above. If
    // YouTube replaced either anchor while secure settings were loading, leave
    // no partial UI and let index.ts retry on its next initialization tick.
    if (!controls.isConnected || !player.isConnected) return;
    player.appendChild(panel);
    const settingsBtn = controls.querySelector('.ytp-settings-button');
    if (settingsBtn?.parentNode) settingsBtn.parentNode.insertBefore(btn, settingsBtn);
    else controls.appendChild(btn);

    const onWorkflowProgress = (): void => renderWorkflowProgress();
    document.addEventListener(WORKFLOW_CHANGED_EVENT, onWorkflowProgress);
    renderWorkflowProgress();

    // Stop YouTube keyboard shortcuts from firing when interacting with the panel
    (['keydown', 'keyup', 'keypress'] as const).forEach((evt) => {
        panel.addEventListener(evt, (e: Event) => { e.stopPropagation(); });
    });

    let overlay = document.getElementById('cueflora-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'cueflora-overlay';
        overlay.style.bottom = `${state.overlayOffsetBottom}px`;
        overlay.style.setProperty('--cueflora-bg-opacity', String(state.subtitleBgOpacity / 100));
        overlay.addEventListener('click', (e: Event) => { e.stopPropagation(); });
        overlay.addEventListener('contextmenu', (e: Event) => { e.stopPropagation(); });

        player.appendChild(overlay);
    } else {
        overlay.style.bottom = `${state.overlayOffsetBottom}px`;
        overlay.style.setProperty('--cueflora-bg-opacity', String(state.subtitleBgOpacity / 100));
    }

    const navHome = document.getElementById('cueflora-nav-home')!;
    const navSettings = document.getElementById('cueflora-nav-settings')!;
    const viewHome = document.getElementById('cueflora-view-home')!;
    const viewSettings = document.getElementById('cueflora-view-settings')!;

    const switchView = (view: string): void => {
        if (view === 'settings') {
            viewHome.classList.remove('active');
            viewSettings.classList.add('active');
            navSettings.style.display = 'none';
            navHome.style.display = 'inline';
        } else {
            viewSettings.classList.remove('active');
            viewHome.classList.add('active');
            navHome.style.display = 'none';
            navSettings.style.display = 'inline';
            populateDropdowns();
        }
    };

    btn.addEventListener('click', togglePanel);
    document.getElementById('cueflora-close')!.addEventListener('click', togglePanel);
    navSettings.addEventListener('click', () => { switchView('settings'); });
    navHome.addEventListener('click', () => { switchView('home'); });

    document.getElementById('cueflora-open-options')!.addEventListener('click', () => {
        browser.runtime.sendMessage({ type: 'OPEN_OPTIONS' }).catch(() => {});
    });
    const providerStatus = document.createElement('div');
    providerStatus.className = 'cueflora-status';
    providerStatus.id = 'cueflora-provider-summary';
    viewHome.append(providerStatus);
    const updateProviderSummary = () => {
        const summaries = getProviderSummary();
        const describe = (summary: typeof summaries.next) => {
            const sourceSelect = document.getElementById('cueflora-transcription-lang') as HTMLSelectElement;
            const targetSelect = document.getElementById('cueflora-translation-lang') as HTMLSelectElement;
            const source = sourceSelect.value;
            const target = targetSelect.value;
            const nativeLabel = (select: HTMLSelectElement) => !select.value || select.value === 'none'
                ? 'Off' : 'YouTube captions / ' + (select.selectedOptions[0]?.textContent || select.value);
            const describeAI = (provider: typeof summary.transcription) => provider.model ? provider.label + ' / ' + provider.model : 'Not configured';
            return 'Transcription: ' + (source.startsWith('transcription:') ? describeAI(summary.transcription) : nativeLabel(sourceSelect)) +
                '\nTranslation: ' + (target.startsWith('translation:') ? describeAI(summary.translation) : nativeLabel(targetSelect));
        };
        providerStatus.textContent = 'Next Run\n' + describe(summaries.next) +
            (summaries.current ? '\nCurrent Run\n' + describe(summaries.current) : '');
    };
    const refreshSummary = async () => {
        const sameNavigation = navigationGuard();
        const canApply = () => sameNavigation() && panel.isConnected && !isWorkflowBusy() &&
            !document.getElementById('cueflora-view-appearance')?.classList.contains('active');
        if (!canApply()) return;
        try {
            await refreshProviderSummary(canApply);
            if (!canApply()) return;
            const changed = await refreshPreferences(canApply,[`${STORAGE_PREFIX}transcription_lang`,`${STORAGE_PREFIX}translation_lang`]);
            if (!canApply()) return;
            if (changed.includes(`${STORAGE_PREFIX}transcription_lang`)) { state.transcriptionCues=[]; state.translationCues=[]; }
            else if (changed.includes(`${STORAGE_PREFIX}translation_lang`)) state.translationCues=[];
            if (changed.length) { resetWorkflow(); populateDropdowns(); renderWorkflowProgress(); startRenderLoop(); }
            updateProviderSummary();
        } catch { if (canApply()) providerStatus.textContent = 'Saved settings could not be refreshed. Reopen the panel to retry; no processing was started.'; }
    };
    document.addEventListener('cueflora-providers-changed', updateProviderSummary);
    window.addEventListener('focus', refreshSummary);
    panel.addEventListener('cueflora-panel-open', refreshSummary);
    panel.addEventListener('change', updateProviderSummary);
    updateProviderSummary();
    const warnings = document.createElement('div');
    warnings.id = 'cueflora-persistence-warnings';
    warnings.setAttribute('role', 'status');
    const warningMessages = new Map<string, string>();
    const showWarning = (kind: string, message: string) => {
        warningMessages.set(kind, message);
        warnings.textContent = [...warningMessages.values()].join(' ');
    };
    providerStatus.after(warnings);
    const showCacheWarning = () => {
        showWarning('cache', 'Subtitle cache could not be saved. Regeneration may be needed after reloading.');
    };
    document.addEventListener('cueflora-cache-warning', showCacheWarning);
    const showEvidenceWarning = () => {
        showWarning('evidence', 'Diagnostic evidence is incomplete. Subtitle processing continues.');
    };
    document.addEventListener('cueflora-evidence-warning', showEvidenceWarning);
    const showPreferenceWarning = () => {
        showWarning('preferences', 'Could not save preferences. Changes may be lost after reloading.');
    };
    document.addEventListener('cueflora-preference-warning', showPreferenceWarning);

    // Click outside panel to close
    const onDocumentClick = (e: MouseEvent): void => {
        if (!state.isPanelOpen) return;
        if (panel.contains(e.target as Node) || btn.contains(e.target as Node)) return;
        togglePanel();
    };
    document.addEventListener('click', onDocumentClick);

    const cleanupAppearance = mountAppearanceEditor(panel, player as HTMLElement, overlay);
    panel.querySelectorAll('.cueflora-input, .cueflora-select').forEach((input) => {
        const label = input.closest('.cueflora-row')?.querySelector('.cueflora-label, .cueflora-check-text');
        if (label) input.setAttribute('aria-label', label.textContent || 'Setting');
    });
    panel.addEventListener('keydown', (event) => { if (event.key === 'Escape') { event.preventDefault(); togglePanel(); btn.focus(); } });

    // Store cleanup function to remove document-level listeners on navigation
    state._cleanupUI = (): void => {
        cleanupAppearance();
        document.removeEventListener('click', onDocumentClick);
        document.removeEventListener(WORKFLOW_CHANGED_EVENT, onWorkflowProgress);
        document.removeEventListener('cueflora-providers-changed', updateProviderSummary);
        document.removeEventListener('cueflora-cache-warning', showCacheWarning);
        document.removeEventListener('cueflora-evidence-warning', showEvidenceWarning);
        document.removeEventListener('cueflora-preference-warning', showPreferenceWarning);
        window.removeEventListener('focus', refreshSummary);
        panel.removeEventListener('cueflora-panel-open', refreshSummary);
        state._cleanupUI = null;
    };

    // Show toggles on home view — immediate
    document.getElementById('cueflora-show-transcription')!.addEventListener('change', function (this: HTMLInputElement) {
        state.showTranscription = this.checked;
        preferenceStorage.setItem(`${STORAGE_PREFIX}show_transcription`, this.checked ? '1' : '0');
        startRenderLoop();
    });
    document.getElementById('cueflora-show-translation')!.addEventListener('change', function (this: HTMLInputElement) {
        state.showTranslation = this.checked;
        preferenceStorage.setItem(`${STORAGE_PREFIX}show_translation`, this.checked ? '1' : '0');
        startRenderLoop();
    });
    (document.getElementById('cueflora-transcription-lang') as HTMLSelectElement).addEventListener('change', function (this: HTMLSelectElement) {
        const value = this.value;
        preferenceStorage.setItem(`${STORAGE_PREFIX}transcription_lang`, value);

        // Selection is declarative only. Do not fetch, transcribe, or translate
        // until the user explicitly presses the unified Run button.
        state.transcriptionCues = [];
        state.translationCues = [];

        resetWorkflow();
        const statusEl = document.getElementById('cueflora-status');
        if (statusEl) statusEl.innerText = 'Selection updated — click Run to process subtitles.';

        populateDropdowns();
        startRenderLoop();
    });

    (document.getElementById('cueflora-translation-lang') as HTMLSelectElement).addEventListener('change', function (this: HTMLSelectElement) {
        const value = this.value;
        preferenceStorage.setItem(`${STORAGE_PREFIX}translation_lang`, value);

        // As with transcription, changing the target language only changes the
        // pending selection. Existing translation display is cleared so the UI
        // never labels an old track as the newly selected language.
        state.translationCues = [];

        resetWorkflow();
        const statusEl = document.getElementById('cueflora-status');
        if (statusEl) statusEl.innerText = 'Selection updated — click Run to process subtitles.';

        populateDropdowns();
        startRenderLoop();
    });

    document.getElementById('cueflora-run-workflow')!.addEventListener('click', trustedRun(async () => {
        const transcriptionSelect = document.getElementById('cueflora-transcription-lang') as HTMLSelectElement;
        const translationSelect = document.getElementById('cueflora-translation-lang') as HTMLSelectElement;
        const statusEl = document.getElementById('cueflora-status');

        const transcriptionCode = transcriptionSelect.value || null;
        const rawTranslationCode = translationSelect.value || 'none';
        const translationCode = rawTranslationCode === 'none' ? null : rawTranslationCode;

        if (!transcriptionCode) {
            if (statusEl) statusEl.innerText = 'Select a transcription language first.';
            return;
        }

        // Save both choices together immediately before executing the workflow.
        preferenceStorage.setItem(`${STORAGE_PREFIX}transcription_lang`, transcriptionCode);
        preferenceStorage.setItem(`${STORAGE_PREFIX}translation_lang`, rawTranslationCode);

        try {
            await runSubtitleWorkflow(transcriptionCode, translationCode);
        } catch (error) {
            if (statusEl) {
                statusEl.innerText = error instanceof Error ? error.message : String(error);
            }
        } finally {
            populateDropdowns();
            renderWorkflowProgress();
            startRenderLoop();
        }
    }));
};
