declare const __CUEFLORA_PUBLIC_LINKS__: unknown;
export type PublicLinks = { downloadUrl: string; privacyUrl: string; supportUrl: string };

export const validatedLinks = (value: unknown): PublicLinks | null => {
    if (!value || typeof value !== 'object') return null;
    const fields = value as Record<string, unknown>;
    for (const name of ['downloadUrl','privacyUrl','supportUrl']) {
        if (typeof fields[name] !== 'string') return null;
        try {
            const url = new URL(fields[name]);
            const host = url.hostname.toLowerCase().replace(/\.$/, '');
            if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash
                || (url.port && url.port !== '443') || /\s|\\/.test(fields[name]) || host === 'localhost'
                || !host.includes('.') || /^[\d.]+$/.test(host) || host.startsWith('[')
                || /\.(invalid|test|local|localhost)$/.test(host)) return null;
        } catch { return null; }
    }
    return { downloadUrl: fields.downloadUrl as string, privacyUrl: fields.privacyUrl as string, supportUrl: fields.supportUrl as string };
};

export const renderReleaseGuidance = (document: Document, value: unknown = typeof __CUEFLORA_PUBLIC_LINKS__ !== 'undefined' ? __CUEFLORA_PUBLIC_LINKS__ : null): void => {
    const links = validatedLinks(value), guidance = document.getElementById('helper-install-guidance');
    if (!links || !guidance) return;
    guidance.replaceChildren(document.createTextNode('For AI features, download CueFlora Setup, run it, select Chrome, and choose Install. No Python or administrator access is needed. The installer is unsigned, so Windows may show a warning. '));
    for (const [label,address] of [['Download helper',links.downloadUrl],['Privacy',links.privacyUrl],['Support',links.supportUrl]]) {
        const link = document.createElement('a'); link.textContent = label; link.href = address;
        link.target = '_blank'; link.rel = 'noopener noreferrer'; guidance.append(link,document.createTextNode(' '));
    }
    const footer = document.getElementById('release-label');
    if (footer) footer.textContent = 'Based on Substrata by jmviz, under the MIT licence. Windows x64 / Chrome edition.';
};
