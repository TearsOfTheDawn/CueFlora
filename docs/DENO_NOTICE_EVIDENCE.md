# Deno source-notice evidence — 2026-10-15

This is evidence collection, not a licence approval or proof every package is shipped in Windows Deno.

## Exact inputs and offline replay

The official Deno 2.9.7 source archive is hash-locked. `deno-cargo-policy.json` separately locks its Cargo.lock bytes and the canonical 1046-package registry pin inventory. Each source archive must match its Cargo checksum; no latest-version or moving-git fallback is permitted. Rust source/build code is never executed by the notice collectors.

`cargo_notice_evidence.py` extracts 1659 original notice files from these exact archives. It separates package-root/explicit `license-file` notices from nested source/test notices. There are 125 packages without a root/declared notice; merely finding an unrelated nested licence does not resolve them. This Cargo list includes optional, test, build-only and non-Windows dependencies; it is deliberately labelled a conservative source superset, not a shipment inventory.

The initial 120 entirely notice-free archive cases were investigated through recorded VCS commits. `repository-notice-inputs.lock.json` freezes the results and exact source archive/notice hashes. `repository_notice_evidence.py` independently replays them against exact Cargo archives and VCS records. Current source recovers notices for 68 packages (77 distinct files), leaving 52 unresolved lookup rows. The preserved 0.1.5 package predates this follow-up and retains its original 55/65 report; it is not silently modified or declared newly cleared.

The follow-up adds original notices for cranelift-isle, five OpenTelemetry crates, five wasm-tools crates, zune-jpeg and win_uds. Some repository metadata included a monorepo `/tree/...` URL; the fixed crate commit, not that moving branch, selects the source. The original `UNLICENSE` is retained as such, without inventing another grant. These 13 source rows use small notice-only assets instead of complete repository ZIPs. Each asset is bound to the exact repository/commit/path, SHA-256, Git blob SHA-1 and byte count; online reads are bounded to at most 1 MiB plus one detection byte and 30 seconds, redirects are rejected, existing inputs are never replaced, and offline replay refuses missing/changed files. Newer licences are not substituted for missing historical notices.

The 28 SWC rows still have unavailable exact upstream commits across 13 pinned IDs. Public SWC metadata and its current licence were accessible during the control check, but the current licence is not proof of a missing historical commit's contents. The remaining cases still need actual source/applicability review; notice recovery alone does not establish Windows binary shipment.

Repository inference is recorded when another exact same-commit crate identifies the repository. Ancestor notices remain original evidence with applicability unproven; a monorepo root licence is not automatically assigned to every crate.

## What ships and what remains

Preparation includes the original notice bytes, hashes and source provenance in runtime/Setup and the separate source evidence bundle. These are static notices, not executable downloaded components. The frozen downloader still disables remote component downloads/plugins and selects bundled Deno explicitly.

V8/binding core notices are separately restored from fixed upstream archives because the source crate omits `LICENSE*`. Dirty VCS metadata, Rust/V8 transitive/submodule coverage, Windows-relevant build flags and any unproven actual binary dependencies remain explicit. Missing source evidence remains a release blocker; source/notice inventory coverage does not itself grant redistribution permission.

Before publication, review the generated candidate's exact dependency ledger and unresolved evidence against actual shipped bytes. Do not infer GPL inclusion from unused test/Linux source notices, and do not infer absence of obligations merely because the application is MIT-licensed. Public promotion remains blocked until the required exact-bound release decisions are supplied.
