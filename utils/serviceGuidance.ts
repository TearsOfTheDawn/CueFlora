/** Guidance only: never populate a connection, key or model for the user. */
export function serviceGuidance(address: string): { text: string; url?: string } {
    let host = '';
    try { host = new URL(address).hostname; } catch { /* A draft can be incomplete. */ }
    if (host === 'openrouter.ai') return {text:'OpenRouter: copy the API base address from its API documentation, create an API key in Keys, and copy a transcription or text model ID. OpenRouter billing is separate from ChatGPT.',url:'https://openrouter.ai/docs/quickstart'};
    if (host === 'api.openai.com') return {text:'OpenAI API: get an API key from the API dashboard and the API base address/model ID from the documentation. API billing is separate from a ChatGPT subscription.',url:'https://platform.openai.com/docs/quickstart'};
    if (['localhost','127.0.0.1','[::1]'].includes(host)) return {text:'Local service: copy the OpenAI-compatible API address and exact loaded model ID from your running service. CueFlora does not start it or download models.'};
    return {text:'Your service must provide an OpenAI-compatible API: /audio/transcriptions for audio or /chat/completions with structured JSON for translation. Copy its API base address, optional API key and exact model ID from its dashboard or documentation. Caption-only use needs none of these.'};
}
