# Deno source-notice evidence — 2026-10-15

This is evidence collection, not a licence approval or proof every package is shipped in Windows Deno.

## Exact inputs and offline replay

The official Deno 2.9.7 source archive is hash-locked. `deno-cargo-policy.json` separately locks its Cargo.lock bytes and the canonical 1046-package registry pin inventory. Each source archive must match its Cargo checksum; no latest-version or moving-git fallback is permitted. Rust source/build code is never executed by the notice collectors.

`cargo_notice_evidence.py` extracts 1672 original notice files from these exact archives. It separates package-root/explicit `license-file` notices from nested source/test notices. There are 122 packages without a root/declared notice; merely finding an unrelated nested licence does not resolve them. This Cargo list includes optional, test, build-only and non-Windows dependencies; it is deliberately labelled a conservative source superset, not a shipment inventory.

Version 0.1.7 fixes filename discovery globally: LICENSE and British LICENCE spellings, plus UNLICENSE, are retained without package-specific substitutions. Replaying the identical hash-verified archives recovers 13 original files and all previous notice evidence remains. Package-root notices for plist 1.9.0, smartstring 1.0.1 and win_uds 0.2.2 reduce the earlier missing-root count from 125 to 122. smartstring's original MPL terms are evidence of an obligation to assess, not proof of corresponding-source compliance or actual Windows inclusion. The separate repository catalog below is historical and unchanged; its 52 unresolved lookup rows are not the combined count after source-archive recovery.

The initial 120 entirely notice-free archive cases were investigated through recorded VCS commits. `repository-notice-inputs.lock.json` freezes the results and exact source archive/notice hashes. `repository_notice_evidence.py` independently replays them against exact Cargo archives and VCS records. Source 0.1.10 adds three verified monorepo origins, bringing the catalogue to 123 selected packages and recovered notices for 71 packages (81 distinct files), with 52 unresolved lookup rows. Preserved earlier packages retain their original reports; they are not silently modified or declared newly cleared.

The follow-up adds original notices for cranelift-isle, five OpenTelemetry crates, five wasm-tools crates, zune-jpeg and win_uds. Some repository metadata included a monorepo `/tree/...` URL; the fixed crate commit, not that moving branch, selects the source. The original `UNLICENSE` is retained as such, without inventing another grant. These 13 source rows use small notice-only assets instead of complete repository ZIPs. Each asset is bound to the exact repository/commit/path, SHA-256, Git blob SHA-1 and byte count; online reads are bounded to at most 1 MiB plus one detection byte and 30 seconds, redirects are rejected, existing inputs are never replaced, and offline replay refuses missing/changed files. Newer licences are not substituted for missing historical notices.

The 28 SWC rows still have unavailable exact upstream commits across 13 pinned IDs. Public SWC metadata and its current licence were accessible during the control check, but the current licence is not proof of a missing historical commit's contents. The remaining cases still need actual source/applicability review; notice recovery alone does not establish Windows binary shipment.

Repository inference is recorded when another exact same-commit crate identifies the repository. Ancestor notices remain original evidence with applicability unproven; a monorepo root licence is not automatically assigned to every crate.

## Integration in 0.1.10

The already recovered original monorepo notices for libffi-sys 4.1.0, objc2-foundation 0.3.2 and opentelemetry-proto 0.32.0 now participate in normal offline preparation/bootstrap instead of existing only in a private investigation. Their exact crate hashes and `.cargo_vcs_info.json` are checked against the original repository/commit/path, SHA-256, Git blob hash and size. The policy binds the updated inventory hash; regression coverage checks the actual production lock. The old installers/archives are never patched in place.

This adds four original notice files to the build catalogue, not three newly proven Windows binary dependencies. The OpenTelemetry Apache text already appeared as nested notice bytes; the new record improves original provenance rather than inventing missing copyright text. objc2-foundation is Apple-oriented source and is not declared shipped by Windows merely because its notice is collected. Little CMS's original vendor notice was already retained from the crate; its root symlink is not copied as though the link text were a licence. Neither these input additions nor a successful rebuild clears the remaining dependency review.

## What ships and what remains

Preparation includes the original notice bytes, hashes and source provenance in runtime/Setup and the separate source evidence bundle. These are static notices, not executable downloaded components. The frozen downloader still disables remote component downloads/plugins and selects bundled Deno explicitly.

V8/binding core notices are separately restored from fixed upstream archives because the source crate omits `LICENSE*`. Dirty VCS metadata, Rust/V8 transitive/submodule coverage, Windows-relevant build flags and any unproven actual binary dependencies remain explicit. Missing source evidence remains a release blocker; source/notice inventory coverage does not itself grant redistribution permission.

Before publication, review the generated candidate's exact dependency ledger and unresolved evidence against actual shipped bytes. Do not infer GPL inclusion from unused test/Linux source notices, and do not infer absence of obligations merely because the application is MIT-licensed. Public promotion remains blocked until the required exact-bound release decisions are supplied.
