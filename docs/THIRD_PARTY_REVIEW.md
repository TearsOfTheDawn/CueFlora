# Third-party licence and security review: 0.1.12

Updated 2026-10-17. Scope: the existing Windows x64 / Chrome product and its pinned dependencies. No public upload, live installation, browser automation, video download or inference is part of this review. Exact candidate inventories and the later hash-bound review record are authoritative; source documentation alone is not an approval sidecar.

## Material corrections

- Normal packaging now requires thirteen original notices from ten exact V8 dependency commits. Provenance includes the original Gitiles trees, SHA-256, Git blob identities, sizes and V8 DEPS binding. These cover dragonbox, fast_float, simdutf, Abseil, zlib, Perfetto, protobuf and the selected LLVM runtime libraries. The former filename match for `copying-phase.cc/.h` is excluded because those are source code, not licence documents. Core V8 and original ICU terms remain retained.
- The source bundle now includes all 1,046 exact Cargo registry archives, not just a cached copy or a list of download URLs. This also supplies the unchanged MPL-covered sources. No registry package is claimed to be shipped merely because it occurs in that source superset.
- The 122 packages without a root/declared licence filename receive separately labelled generated attribution records. Each retains the original Cargo manifest, archive checksum, author metadata and supplied source copyright statements. No holder or year is invented. Original standalone/nested/repository notices are kept separately. Hash-pinned SPDX reference texts are explicitly standard templates, not fabricated original notices.
- Setup exposes third-party terms before its existing confirmation. Install/repair acknowledgement preserves the upstream Windows-Python/Microsoft conditions without asserting ownership of third-party software or restricting LGPL reverse-engineering/replacement rights. CLI mutations require `--accept-third-party-terms`; removal remains ungated.
- Frozen solver subprocesses discard unrelated Deno runtime/authentication/trace configuration, OTEL exporter configuration, Node options and TLS-key logging. Explicit tool-path overrides and proxy/certificate configuration remain supported. Prompting and updater checks are explicitly disabled. Developer/unfrozen behaviour is unchanged. This is configuration isolation, not an OS sandbox or a claim that a suspected updater request had been reproduced.

## Licence judgments and their limits

Published Cargo manifests declare the licences under which packages are released. [Cargo documents standard SPDX declarations and the separate nonstandard `license-file` mechanism](https://doc.rust-lang.org/cargo/reference/manifest.html#the-license-and-license-file-fields). A missing root filename or unavailable historical GitHub commit is therefore not, by itself, proof of no licence grant. Authors metadata is not automatically a copyright notice. This corrects the earlier overly broad missing-file blocker; it does not replace a known applicable original notice with a template.

For the actual declared MIT/Apache/CC0 packages, retain the distributed declaration, all supplied original attribution, full standard terms and unchanged source archives. Original repository notices already recovered remain supplied. Apache's [redistribution conditions](https://www.apache.org/licenses/LICENSE-2.0) concern the licence copy, retained notices, marked changes and applicable NOTICE files; they do not require an invented unique copyright notice or a bit-identical rebuild for every crate. A missing historical repository lookup is not silently converted into an invented NOTICE. No new upstream source modification is made by this packaging correction.

FFmpeg/Opus retain their exact verified shared-source build, sources, recipes and notices, with no GPL/nonfree build additions. The [FFmpeg guidance](https://ffmpeg.org/legal.html) applies to their LGPL distribution; required sources must actually accompany binary hosting. The downloader remains rebuilt from its pinned source with all thirteen dependency wheel/source pairs, original notices and byte-matched curl/native recipe evidence. The source bundle and notices must be distributed with the binary; a planned download URL is not source delivery.

Windows interpreter/DLL provenance is traced to the pinned upstream interpreter, and the eleven component families retain their original terms. The original Windows Python additional conditions remain authoritative. Their downstream distribution conditions are acknowledged rather than claiming a mandatory new paid Visual Studio purchase. This is a review of the supplied upstream distribution route, not independent verification of every upstream author's legal title or a legal opinion.

The file-by-file ledger still produces review-required findings rather than granting itself approval. A later recorded assessment must bind to the exact ledger, runtime, Setup, extension and real evidence-file hashes. Missing mandatory sources, changed notices, unknown owners or corrupted inputs cannot be waived by that review. Source-lock/binary-closure uncertainty and the absence of mathematical proof of safety are not automatically newly invented release requirements.

## Known security finding dispositions

The preserved primary Rust advisory snapshot concerns 21 package/version rows and 30 alias groups, not 21 working CueFlora exploits. Five rows are maintenance warnings. Exact source/caller evidence and the same Deno executable hash allow the known findings to be reviewed without blindly updating the subtitle stack:

- `unicycle` and the `scc` consumer chain are test/benchmark-only in the inspected source graph.
- The actual `anyhow::Error::downcast_mut` consumers trace to the wasm32/WASI binding chain, not the Windows target. Deno's apparent direct match uses the unrelated standard-library `Any` API.
- The documented faster-hex, memmap2, xxhash-rust and quick-xml preconditions are absent at the inspected direct callers. Crossbeam's affected Atomic/Shared pointer formatting is not used by the inspected consumers; moka's MiniArc formats its own raw pointer.
- The documented rand reentrant `ThreadRng` precondition is not found in the inspected normal CLI/SDK log paths. Ambient logging/telemetry configuration is additionally excluded from frozen subprocesses. This is not a patched rand library or proof concerning arbitrary native plugins/configuration.
- Network-related h2/hickory/quinn/rustls findings retain their affected library versions. The solver has no permission-granting flags and no prompts, remote/npm module loading is disabled, and synthetic tests exercise denied network APIs. Frozen environment policy prevents ambient telemetry/updater configuration from silently expanding this contract. Those are bounded exposure controls, not an OS sandbox or universal native exploit resistance.
- The RSA timing record does not show provider-key disclosure: provider secrets are not supplied to the solver as RSA private keys or a decryption service. Arbitrary scripts performing their own crypto do not acquire a persistent CueFlora private key.

These are explicit, scoped review judgments, not a zero-vulnerability certificate. Future advisories, native/V8 defects outside this known set, same-user malware and provider output errors remain ordinary residual risks. A confirmed newly reachable issue requires remediation; successful unit tests or the word “stable” are not a substitute. Audio preparation and inference settings are unchanged.

## Separate publication boundary

Completing this dependency work does not upload the installer, grant Google approval, establish authorisation to download every video, or certify Chrome's treatment of native challenge execution. [Store policies](https://developer.chrome.com/docs/webstore/program-policies/policies) and [MV3 requirements](https://developer.chrome.com/docs/webstore/program-policies/mv3-requirements) remain separate review/submission constraints. No disclaimer is presented as an architectural remedy. Paid signing, an independent auditor's signature and routine prelaunch user testing are not newly imposed requirements.

Only the fresh candidate's completed verification and candidate-bound assessment can close this engineering work. Earlier packages and their pending assessments remain immutable historical evidence.
