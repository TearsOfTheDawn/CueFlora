# Release and support templates

Publisher / contact / privacy URL / download URL / support URL / store-assigned Chrome ID: UNSET. No placeholder is an ownership claim.

Release notes template:

- Version and SHA-256: from the preparation artifact report.
- Supported scope: Windows x64 / Chrome only after external acceptance.
- Requirements: matching extension/helper; user-supplied compatible AI services for AI stages; native captions depend on the video.
- Changes, migration behavior, known limitations and licence/source download location: fill from the measured handoff and cleared ledger.
- Unsigned preview warning and explicit non-public approval status: retain until signing/release gates change.

Support request template:

- Extension/helper version, OS/Chrome version, workflow stage, failure reason, and whether the helper check reports all four tools.
- No plaintext/encrypted API key payloads, provider-vault/Run storage exports, endpoint credentials, signed URLs, full diagnostic dumps or private capture files. Review/redact any voluntarily shared subtitle/video information.
- Reproduce without changing active Run configuration; metadata success is not an inference test.
- If protected keys fail after helper rollback, upgrade the helper. A migration warning distinguishes failed protection from failed legacy cleanup; use the explicit retry, never send the key to support. Windows-account/device changes may require re-entering keys.

Publication checklist: release blockers resolved; licence/corresponding-source delivery ready; privacy/disclosures aligned; genuine screenshots collected; final identity bound; hashes/inventory checked; signed/clean-machine/browser-tested artifacts; explicit publisher authorization/account access. Preparation commands never submit automatically.
