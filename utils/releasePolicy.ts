declare const __CUEFLORA_STORE_CANDIDATE__: boolean;
export type TransportPolicy = 'preview' | 'https-remote';
export const transportPolicy: TransportPolicy = typeof __CUEFLORA_STORE_CANDIDATE__ !== 'undefined' && __CUEFLORA_STORE_CANDIDATE__ ? 'https-remote' : 'preview';
