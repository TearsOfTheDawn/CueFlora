export function buildProfile(value?: string): 'preview' | 'store-candidate' | 'acceptance';
export function chromeIdentity(profile: string, preview: { publicKey?: string; chromeId?: string }, configuration?: {chromePublicKey?: string; extensionIds?: {chrome?: string}}): { key?: string };
export function bundledModulesPlugin(): import('vite').Plugin;
