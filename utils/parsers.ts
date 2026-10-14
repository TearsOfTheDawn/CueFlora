import type { Cue, Word, Json3Data } from './types';

export function parseJson3(json3Data: Json3Data | null): Cue[] {
    if (!json3Data || !json3Data.events) return [];
    const cues: Cue[] = [];
    for (let i = 0; i < json3Data.events.length; i++) {
        const event = json3Data.events[i];
        if (event.tStartMs === undefined || !event.segs) continue;

        // Skip pure newline / append-only events (line separators)
        if (event.aAppend === 1) continue;

        const words: Word[] = [];
        const textParts: string[] = [];
        for (let j = 0; j < event.segs.length; j++) {
            const seg = event.segs[j];
            const raw = (seg.utf8 || '').replace(/<[^>]+>/g, '');
            if (raw === '\n' || !raw.trim()) continue;
            const clean = raw.replace(/&#39;/g, "'").replace(/&quot;/g, '"').trim();
            if (!clean) continue;
            textParts.push(clean);
            words.push({
                text: clean,
                startMs: event.tStartMs! + (seg.tOffsetMs || 0),
                endMs: 0, // computed below
            });
        }

        const text = textParts.join(' ').trim();
        if (!text) continue;

        let endMs: number;
        if (words.length > 1) {
            // Derive end from word timing, not dDurationMs (which is display
            // duration and overlaps with subsequent events).
            const lastWord = words[words.length - 1];
            const avgGap = (lastWord.startMs - words[0].startMs) / (words.length - 1);
            endMs = lastWord.startMs + Math.min(Math.max(avgGap, 200), 500);
        } else {
            endMs = event.tStartMs! + (event.dDurationMs || 3000);
        }

        // Compute per-word endMs from next word's start; last word ends at cue end
        for (let k = 0; k < words.length; k++) {
            words[k].endMs = (k < words.length - 1) ? words[k + 1].startMs : endMs;
        }

        cues.push({ startMs: event.tStartMs!, endMs, text, words });
    }

    // Clamp each cue's end and last word endMs against the next cue's first word
    for (let n = 0; n < cues.length - 1; n++) {
        const cur = cues[n];
        const nxt = cues[n + 1];
        const nxtStart = (nxt.words && nxt.words.length > 0) ? nxt.words[0].startMs : nxt.startMs;
        if (cur.endMs > nxtStart) cur.endMs = nxtStart;
        if (cur.words && cur.words.length > 0) {
            const last = cur.words[cur.words.length - 1];
            if (last.endMs > nxtStart) last.endMs = nxtStart;
        }
    }

    return cues;
}

export function parseVttTime(timeStr: string): number {
    const parts = timeStr.split(':');
    let seconds = 0;
    if (parts.length === 3) seconds = parseInt(parts[0]) * 3600 + parseInt(parts[1]) * 60 + parseFloat(parts[2]);
    else if (parts.length === 2) seconds = parseInt(parts[0]) * 60 + parseFloat(parts[1]);
    return seconds * 1000;
}

export function parseVtt(text: string): Cue[] {
    const cues: Cue[] = [];
    const lines = text.split('\n').filter((line) =>
        line.includes('-->') || (line.trim().length > 0 && !/^\d+$/.test(line.trim()))
    );
    let currentCue: Cue | null = null;
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (line.includes('-->')) {
            const parts = line.split('-->');
            if (parts.length === 2) {
                currentCue = {
                    startMs: parseVttTime(parts[0].trim()),
                    endMs: parseVttTime(parts[1].trim()),
                    text: ''
                };
            }
        } else if (currentCue) {
            const cleanedLine = line.replace(/<[^>]+>/g, '').trim();
            if (cleanedLine) currentCue.text = currentCue.text ? currentCue.text + ' ' + cleanedLine : cleanedLine;
            const nextLine = lines[i + 1] ? lines[i + 1].trim() : '';
            if (currentCue.text && (!nextLine || nextLine.includes('-->'))) {
                cues.push(currentCue);
                currentCue = null;
            }
        }
    }
    return cues;
}
