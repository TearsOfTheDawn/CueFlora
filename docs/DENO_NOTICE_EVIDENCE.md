# Deno source-notice evidence — 2026-10-14

This is evidence collection, not a licence approval or proof every package is shipped in Windows Deno.

## Exact inputs and offline replay

The official Deno 2.9.7 source archive is hash-locked. `deno-cargo-policy.json` separately locks its Cargo.lock bytes and the canonical 1046-package registry pin inventory. Each source archive must match its Cargo checksum; no latest-version or moving-git fallback is permitted. Rust source/build code is never executed by the notice collectors.

`cargo_notice_evidence.py` extracts 1659 original notice files from these exact archives. It separates package-root/explicit `license-file` notices from nested source/test notices. There are 125 packages without a root/declared notice; merely finding an unrelated nested licence does not resolve them. This Cargo list includes optional, test, build-only and non-Windows dependencies; it is deliberately labelled a conservative source superset, not a shipment inventory.

The initial 120 entirely notice-free archive cases were investigated through recorded VCS commits. `repository-notice-inputs.lock.json` freezes the results and exact source archive/notice hashes. `repository_notice_evidence.py` independently replays them against exact Cargo archives and VCS records. Notices were recovered for 55 packages (67 distinct shared files). There are still 65 unresolved lookup rows: unavailable fixed commits, missing repository/commit metadata, or absent notices at the recorded package/ancestor locations. No newer branch or generic invented copyright text is substituted.

Repository inference is recorded when another exact same-commit crate identifies the repository. Ancestor notices remain original evidence with applicability unproven; a monorepo root licence is not automatically assigned to every crate.

## What ships and what remains

Preparation includes the original notice bytes, hashes and source provenance in runtime/Setup and the separate source evidence bundle. These are static notices, not executable downloaded components. The frozen downloader still disables remote component downloads/plugins and selects bundled Deno explicitly.

V8/binding core notices are separately restored from fixed upstream archives because the source crate omits `LICENSE*`. Dirty VCS metadata, Rust/V8 transitive/submodule coverage, Windows-relevant build flags and any unproven actual binary dependencies remain explicit. Missing source evidence remains a release blocker; source/notice inventory coverage does not itself grant redistribution permission.

Before publication, review the generated candidate's exact dependency ledger and unresolved evidence against actual shipped bytes. Do not infer GPL inclusion from unused test/Linux source notices, and do not infer absence of obligations merely because the application is MIT-licensed. Public promotion remains blocked until the required exact-bound release decisions are supplied.
