export function log(msg: string, data?: unknown): void {
    if (data) console.log('[cueflora] ' + msg, data);
    else console.log('[cueflora] ' + msg);
}

export function getVideoId(): string | null {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('v');
}
