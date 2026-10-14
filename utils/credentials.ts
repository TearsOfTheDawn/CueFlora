export interface ProtectedCredential { schema: 1; method: 'windows-dpapi-v1'; blob: string }
export type CredentialStage = 'transcription' | 'translation';
export type KeyAction = 'keep' | 'replace' | 'remove';
export interface MigrateCredentialsMessage { type: 'PROVIDERS_MIGRATE' }
export interface ProtectCredentialMessage {
    type: 'CREDENTIAL_PROTECT'; requestId: string; stage: CredentialStage; baseUrl: string;
    apiKey?: string; credential?: ProtectedCredential; previousBaseUrl?: string;
}
export function validCredential(value: unknown): value is ProtectedCredential {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
    const item = value as Record<string, unknown>;
    return Object.keys(item).sort().join(',') === 'blob,method,schema' && item.schema === 1 && item.method === 'windows-dpapi-v1' &&
        typeof item.blob === 'string' && item.blob.length > 0 && item.blob.length <= 100000 && /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(item.blob);
}
