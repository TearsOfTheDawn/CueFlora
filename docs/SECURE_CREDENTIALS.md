# CueFlora 0.1.2 protected credentials

Remembered API keys use **user-scoped Windows DPAPI** in the on-demand helper. Protection is non-interactive (`CRYPTPROTECT_UI_FORBIDDEN`); machine-wide protection and plaintext fallback are not used. A successful protection operation includes a decrypt/compare check before returning the encrypted record. [Microsoft DPAPI documentation](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata)

This protects stored keys, not against malware executing as the same Windows user. Plaintext necessarily exists briefly in the settings input/helper/request memory. Buffer clearing is best-effort; no complete Python-memory erasure, browser-backup erasure or independent security-audit claim is made.

## Storage and requests

- `cueflora_private_providers_v2` stores one versioned provider/vault record. Each encrypted key is bound to product, stage and normalized service address using DPAPI entropy and an authenticated decrypted context check.
- Settings receive only empty key inputs and a saved-key indicator. Existing plaintext and encrypted blobs are never returned through provider settings, player summaries or Run records. Run snapshots contain opaque vault references, preserving their original configuration and key when another tab saves replacements.
- The background resolves a reference only for a native metadata/inference request. The helper decrypts immediately before using it. Before a keyed request, the background checks the exact protection capability on the **same native connection**. A missing/older helper stops the request with Upgrade/Repair guidance; preflight is not inference and does not consume a model attempt.
- Retired vault records remain only while an unexpired Run references them; subsequent saves/releases/tab removal prune them. Ciphertext/keys are excluded from diagnostics, captures and verification reports. Protected-request errors/progress are narrowed at the browser boundary, which cannot itself decrypt a key.
- New unsaved keys may be sent for an explicit metadata check without being persisted. Caption-only operation and services requiring no key remain available.

## Keep, Replace, Remove and migration

**Keep** retains the saved key without reading it into the UI. **Replace** protects a newly entered key. **Remove** drops the current provider reference; an already bound Run retains its original reference until released. An address change requires a replacement key or explicit confirmation to reuse/rebind the saved key inside the helper. Stage switching never reuses another stage's key.

When settings open, a validated legacy CueFlora v1 record is protected, persisted and reread for verification **before** plaintext removal. Protection/persistence failure retains the original record and reports incomplete migration. If protected persistence succeeds but legacy removal fails, the warning accurately distinguishes those outcomes. Use **Retry protected key migration** to retry deliberately. There is no import of Substrata settings.

An uncertain write timeout is reconciled using a read-only, background-queued **Reload saved state (keep edits)**. It never automatically repeats a write, migration or inference. Drafts survive failed saves; Cancel uses successfully reread/persisted values. Do not downgrade the extension after v2 migration: older extensions cannot read v2 records. Helper rollback remains supported, but a helper lacking protection capability cannot run keyed AI stages until upgraded again.

## Transport profiles

Store candidates require HTTPS for non-loopback services in both background and native request validation. HTTP exceptions are exactly `localhost`, `127.0.0.1` and `::1`; deceptive aliases are not accepted as loopback exceptions. Provider redirects are not followed. Preview builds retain explicit remote-HTTP acknowledgement for compatibility; it is **not** secure transport, and may expose keys/audio/text to network observers. Neither encryption at rest nor acknowledgement makes that preview behavior store-compliant.

All endpoint/model defaults remain blank. Protection/health/model checks are bounded metadata operations; subtitle generation still requires explicit Run, with unchanged pipeline and request ceiling. Store compliance and independent review remain separate gates.
