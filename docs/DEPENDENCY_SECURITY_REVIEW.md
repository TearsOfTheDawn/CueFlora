# Dependency security follow-up — 2026-10-16

This is an engineering review in progress, not independent security certification, legal clearance or Store approval. No browser automation, live installation, media download or AI inference is used. Source retains application version 0.1.7 until the combined security work is ready for a newly verified candidate; existing 0.1.7 artifacts are immutable and predate this fix.

## Confirmed shipped dependency update

The rebuilt downloader previously embedded urllib3 2.7.0. A fresh OSV query matched three upstream advisories (and three alias records, not six distinct defects). Primary upstream advisories identify 2.8.0 as patched:

- HTTPS proxy TLS configuration could be ignored or overwritten under the affected proxy configurations. [GHSA-8988-9cw3-xx77](https://github.com/urllib3/urllib3/security/advisories/GHSA-8988-9cw3-xx77).
- Streaming chunked Deflate with trailing bytes could loop without progressing. [GHSA-gh4c-6fx4-qh6g](https://github.com/urllib3/urllib3/security/advisories/GHSA-gh4c-6fx4-qh6g).
- Streaming chunk-size lines lacked a bounded buffer. Requests' streaming interface can use this affected path. [GHSA-vxq7-64xx-v4gw](https://github.com/urllib3/urllib3/security/advisories/GHSA-vxq7-64xx-v4gw).

These are confirmed affected-version matches in an actual bundled dependency, not proof that every exploit precondition occurs in a CueFlora Run. The requests downloader is retained, so upgrading this library is preferable to assuming only curl will be used or disabling a capability.

`downloader-inputs.lock.json` schema 2 explicitly selects urllib3 2.8.0, its original wheel/source hashes and a source-retained, exact original PyPI metadata response. It does not mislabel the patched wheel as part of yt-dlp's earlier upstream hash lock. `downloader_security.py` verifies the old baseline against the unchanged yt-dlp source, all unaffected upstream hashes, patch provenance and the actual rebuilt executable's observed library version. The immutable metadata snapshot avoids future changes to PyPI JSON breaking offline reproduction. Schema 1 original-pin records remain compatible.

The isolated new downloader uses the same yt-dlp 2026.08.19 source, Python 3.13.15 and all thirteen dependency capabilities. Its checks passed: 1752 extractors unchanged, exact local EJS bytes unchanged, 75 native-library origins hash-matched, urllib3 2.8.0 observed and `pip check` clean. A bounded loopback-only probe confirmed Deflate EOF/trailing-data termination and rejection of an oversized chunk-size line. The HTTPS proxy TLS regression was not independently exercised; no broader safety claim follows.

Source, package hashes and matching sources/notices are retained in the isolated build report. Production audio selection, preparation, chunking, inference, credentials and explicit Run behavior are unchanged. No full new installer has yet been declared verified; the old candidate does not acquire these protections by changing source.

## npm findings need separate triage/remediation

An isolated read-only npm audit of the entire lock reported 25 affected package entries (four critical, sixteen high, four moderate and one low). This includes meta-vulnerabilities inherited from dependencies; it is not 25 proven shipped extension flaws. Auditing only `--omit=dev` would be misleading because some WXT support packages marked development dependencies are actually emitted into the extension.

The corresponding 35-package OSV query covered observed emitted JavaScript, observed native host Python, downloader Python and explicitly labelled Python build inputs. Its only matched package was urllib3 2.7.0. This does not clear npm meta-vulnerabilities, unqueried native C/Rust components, unpublished defects or unknown vulnerabilities. [OSV API](https://google.github.io/osv.dev/api/), [npm audit behavior](https://docs.npmjs.com/cli/v11/commands/npm-audit/).

Most npm matches involve build/test/browser-launch tooling: Vitest/mocker, Vite, web-ext/web-ext-run and their transitive dependencies. Examples include pinned tmp 0.2.5 and fx-runner's pinned shell-quote 1.7.3. The audit suggests a WXT 0.21.4 framework upgrade for some paths, but that is not yet an approved remedy merely because npm suggests it. First assess compatible patched resolutions or narrowly scoped overrides and verify actual used paths. Do not run a forced broad update or silently remove Firefox build coverage. The current tests use jsdom, not Vitest's browser server; that narrows exposure without making the affected code vanish. [Vitest advisory](https://github.com/vitest-dev/vitest/security/advisories/GHSA-82fw-gwwq-j7x9).

## Remaining execution

1. Resolve npm tooling findings with measured dependency changes and preserve the existing extension architecture/layout/pipeline.
2. Run the full suites/builds and update exact input caches, notices and inventories. Assign a coherent higher application version only when the combined source is ready.
3. Build and independently verify fresh runtime/Setup/store/source artifacts; preserve every earlier package and record new artifact-bound decisions accurately.
4. Continue the existing licensing, native-security/download-policy, public hosting, genuine Store assets, Google approval and final publication gates. No gate is cleared by this document or the isolated build.

The publisher's public-first route and deferred live testing remain unchanged. No routine manual test or intermediate Store upload is requested. The local advisory responses, exact proposed metadata and isolated-build evidence stay under ignored artifacts, not provider configuration or credential-bearing diagnostics.
