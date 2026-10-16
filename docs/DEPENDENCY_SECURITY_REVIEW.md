# Dependency security follow-up — 2026-10-16

Source 0.1.8 combines the downloader security patch and audited developer-tool migration. This is engineering evidence, not independent security certification, legal clearance or Store approval. No browser automation, live installation, media download or AI inference is used. Existing packages, including 0.1.7, remain immutable and predate these fixes. Only a complete fresh candidate's matching readiness, inventories and handoff establish its rebuilt results; changing source does not patch old installers.

## Confirmed shipped dependency update

The rebuilt downloader previously embedded urllib3 2.7.0. A fresh OSV query matched three upstream advisories (and three alias records, not six distinct defects). Primary upstream advisories identify 2.8.0 as patched:

- HTTPS proxy TLS configuration could be ignored or overwritten under the affected proxy configurations. [GHSA-8988-9cw3-xx77](https://github.com/urllib3/urllib3/security/advisories/GHSA-8988-9cw3-xx77).
- Streaming chunked Deflate with trailing bytes could loop without progressing. [GHSA-gh4c-6fx4-qh6g](https://github.com/urllib3/urllib3/security/advisories/GHSA-gh4c-6fx4-qh6g).
- Streaming chunk-size lines lacked a bounded buffer. Requests' streaming interface can use this affected path. [GHSA-vxq7-64xx-v4gw](https://github.com/urllib3/urllib3/security/advisories/GHSA-vxq7-64xx-v4gw).

These are confirmed affected-version matches in an actual bundled dependency, not proof that every exploit precondition occurs in a CueFlora Run. The requests downloader is retained, so upgrading this library is preferable to assuming only curl will be used or disabling a capability.

`downloader-inputs.lock.json` schema 2 explicitly selects urllib3 2.8.0, its original wheel/source hashes and a source-retained, exact original PyPI metadata response. It does not mislabel the patched wheel as part of yt-dlp's earlier upstream hash lock. `downloader_security.py` verifies the old baseline against the unchanged yt-dlp source, all unaffected upstream hashes, patch provenance and the actual rebuilt executable's observed library version. The immutable metadata snapshot avoids future changes to PyPI JSON breaking offline reproduction. Schema 1 original-pin records remain compatible.

The isolated new downloader uses the same yt-dlp 2026.08.19 source, Python 3.13.15 and all thirteen dependency capabilities. Its checks passed: 1752 extractors unchanged, exact local EJS bytes unchanged, 75 native-library origins hash-matched, urllib3 2.8.0 observed and `pip check` clean. A bounded loopback-only probe confirmed Deflate EOF/trailing-data termination and rejection of an oversized chunk-size line. The HTTPS proxy TLS regression was not independently exercised; no broader safety claim follows.

Source, package hashes and matching sources/notices are retained in build reports. Production audio selection, preparation, chunking, inference, credentials and explicit Run behavior are unchanged. Full fresh preparation must also verify the matching runtime/Setup/store/source packages; the isolated downloader alone is not a complete installer.

## npm developer-tool remediation

An isolated read-only npm audit of the entire lock reported 25 affected package entries (four critical, sixteen high, four moderate and one low). This includes meta-vulnerabilities inherited from dependencies; it is not 25 proven shipped extension flaws. Auditing only `--omit=dev` would be misleading because some WXT support packages marked development dependencies are actually emitted into the extension.

The corresponding 35-package OSV query covered observed emitted JavaScript, observed native host Python, downloader Python and explicitly labelled Python build inputs. Its only matched package was urllib3 2.7.0. This does not clear npm meta-vulnerabilities, unqueried native C/Rust components, unpublished defects or unknown vulnerabilities. [OSV API](https://google.github.io/osv.dev/api/), [npm audit behavior](https://docs.npmjs.com/cli/v11/commands/npm-audit/).

Most npm matches involved build/test/browser-launch tooling. A discarded non-forced proposal still left thirteen findings and changed emitted support-library versions; it was not adopted. After reviewing [WXT's migration requirements](https://wxt.dev/guide/resources/upgrading) and [exact release](https://github.com/wxt-dev/wxt/releases/tag/wxt-v0.21.4), source now selects WXT 0.21.4, explicit Vite 8.3.4 and patched Vitest 4.1.12. The unused web-ext/web-ext-run launcher tree is absent; both Chrome and Firefox production builds remain. Developer servers no longer open browsers automatically; unpacked development loading is manual. [Vitest advisory](https://github.com/vitest-dev/vitest/security/advisories/GHSA-82fw-gwwq-j7x9).

Explicit pins preserve the previous exact lock entries for @wxt-dev/browser 0.1.39, @wxt-dev/storage 1.2.8 and pinyin-pro 3.28.0, rather than silently upgrading emitted support packages to clear the scanner. jsdom's compatible undici dependency is locked to 7.30.1, beyond the upstream [7.29.1 fixes](https://github.com/nodejs/undici/security/advisories/GHSA-w293-vg96-wgc3). This is test tooling, not CueFlora's provider HTTP client. Existing Node typings are now explicit rather than accidentally supplied by removed launcher dependencies.

The selected full-lock candidate audit reported zero advisory matches, without forced repair, override rules or omitted development dependencies. Final applied source is audited separately. This is a dated database result, not proof of safety or coverage of native C/Rust components. CI checks the full dependency tree again; offline preparation does not silently query online advisory services.

Migration changes test imports/fixtures and compiler/build configuration, not production subtitle/provider/credential/Run/audio source. Typechecking explicitly covers owned source/tests/configuration and retains the previous strict contract; optional new WXT flags do not silently pull historical artifacts into compilation or redefine that contract. The upgraded fake-browser requires complete synthetic tabs, explicit callbacks and storage-access mocks. A new regression verifies the real background refuses requests when trusted storage restriction fails.

WXT's npm tarball omitted its MIT notice. The [original release-tag notice](https://raw.githubusercontent.com/wxt-dev/wxt/wxt-v0.21.4/LICENSE) is retained with SHA-256 `7b0b00fcdbc6a036078aad84d0bc0fae240ac67144b86c911149c2daa37c9f85`. `npm-notices.lock.json` binds it to version and npm integrity. Extension and Python ledger collectors verify the original bytes; missing/mismatched notices still fail. Tests cover missing identity, altered content and unsafe paths. This is not a substituted generic MIT text or legal clearance.

Root checks passed after migration: 293 TypeScript tests, 95 native/setup tests (two Windows symlink-privilege skips), 128 packaging tests and eight Node tests, plus typecheck, both browser builds, compilation and whitespace checks. Two further production-workspace tests bring packaging coverage to 130; full preparation reruns the complete current suite. Manifest comparison found only application version and an explicit `options_ui.open_in_tab: false`, equivalent to the earlier omitted default. Live browser behavior and semantic translation quality are not inferred from automated results.

## Remaining execution

1. Verify final applied dependency locks and retain the new exact offline cache; preserve architecture/layout/pipeline and earlier packages.
2. Full fresh preparation reruns root and actual clean-source suites/builds, rebuilding matching 0.1.8 runtime/Setup/store/source packages with notices and inventories.
3. Verify synthetic DPAPI, temporary-root simulated lifecycle, restricted-PATH/Unicode PING, archive hashes and original-project preservation. The complete candidate's measured reports supersede interim checks.
4. Continue the existing licensing, native-security/download-policy, public hosting, genuine Store assets, Google approval and final publication gates. No gate is cleared by this document or the isolated build.

The publisher's public-first route and deferred live testing remain unchanged. No routine manual test or intermediate Store upload is requested. The local advisory responses, exact proposed metadata and isolated-build evidence stay under ignored artifacts, not provider configuration or credential-bearing diagnostics.
