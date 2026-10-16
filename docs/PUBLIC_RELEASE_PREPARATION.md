# Repeating Windows/Chrome preparation

For current preparation, follow [DISTRIBUTION.md](DISTRIBUTION.md) and [RELEASE_COMPLETION.md](RELEASE_COMPLETION.md). The exact npm lock uses WXT 0.21.4/Vite 8.3.4/Vitest 4.1.12; populate a fresh npm cache for that lock rather than reusing an old cache inventory. Downloader schema 2 requires the exact urllib3 2.8.0 inputs. Official Node/npm and Python are restored from pinned public archives. Audio can be built with `--audio-cache` or copied/reverified with `--audio-build <verified-9.0.2-build>`. `--public-config` binds a real Store identity without granting release approval. Since 0.1.9 full preparation requires independently consistent runtime-file attribution before assembly; source/notice completeness and external approval remain separate. The older commands, unresolved-FFmpeg-origin discussion and identity statements below document the historical 0.1.2 baseline, not current adoption instructions.

Run from `C:\AI\CueFlora` with the exact cached inputs and the pinned Python environment:

```powershell
npm run release:prepare -- --output artifacts/distribution/public-preparation-001 --cache artifacts/input-cache-v1
```

Choose a **fresh** output directory each time. Default is offline and rejects missing, corrupt or substituted files. `--online` fetches only missing URL-bound files from the reviewed input lock; it never chooses latest or repairs a mismatched cache automatically. The current FFmpeg/ffprobe origin is unresolved, so their exact preserved bytes must be supplied in the cache, not downloaded speculatively.

For 0.1.2, also supply `--evidence-cache artifacts/redistribution-evidence-v2` (the default), containing the six exact supplemental inputs in `packaging/evidence-windows.lock.json`. Preparation verifies it offline; it never downloads or substitutes these inputs, including in `--online` mode. `fetch_redistribution_evidence.py` is a separate explicit maintainer collection command, not a runtime updater. Use a copied fresh main cache if retaining earlier cache manifests byte-for-byte. Source evidence remains independent of the audio binaries actually shipped.

The command verifies all inputs and EJS; records source hashes without requiring commits/remotes; restores a disposable offline Python environment; runs all engineering gates; restores npm dependencies offline in a separate workspace; builds Chrome preview and keyless store-candidate profiles; builds two fresh runtime/Setup pairs in the same restored environment; compares outputs; collects licence/source evidence; exercises headless Setup and simulated lifecycle; verifies Substrata preservation; assembles a private preview and independently verifies its ZIP. It never installs into the live user environment, launches a browser or performs inference.

The 0.1.2 pipeline additionally checks actual frozen-host Windows protection using synthetic keys, generates consolidated notices and a runtime/Setup/dependency/source ledger, and checks newly added source whitespace without staging. All previously measured preview ZIPs/Setup files are hash-checked before and after preparation.

PyInstaller DLL discovery uses only the pinned interpreter and Windows system directory. Every collected and shipped native DLL/pyd must match the locked interpreter bytes; unrelated PATH dependencies fail, rather than quietly entering a portable package. A final audit found this contamination in `security-hardening-001`, which is preserved/superseded; use the corrected fresh delivery. System DLLs resolved by the installed OS are not a claim of bundled redistribution or clean-machine certification.

`readiness.json`, command logs, `source-files.json`, `build-comparison.json`, licence evidence and artifact checksums provide the ledger. A failure leaves `engineeringPassed: false` with its stage; a passing run still has `publicReleaseReady: false` and enumerated blockers. Source changes during the run are rejected. The development Chrome identity remains `klnnagigpdlgchlablabnafceoldfalm` (see `preview-identity.json`; do not regenerate it).

## Locked inputs and offline use

`packaging/inputs-windows.lock.json` records exact tool/source/notice/wheel digests and interpreter-file hashes. `requirements-windows-hashed.lock` enforces pip hashes. The private cache also contains a complete local interpreter snapshot and exact npm tarballs validated against `package-lock.json` integrity fields. All 2256 upstream interpreter payload files match the hash-verified official stripped archive; two uv-added metadata files are separately locked. This establishes payload matching, not complete native-library licence clearance. Node/npm must be available; their effective versions and Node executable hash are recorded, not silently downloaded. No unlocked global npm/Python packages are installed.

For an independent offline environment:

```powershell
.packaging-venv/Scripts/python.exe packaging/bootstrap_offline.py --cache artifacts/input-cache-v1 --output artifacts/another-offline-env
node scripts/cache-npm.mjs artifacts/input-cache-v1/npm --offline
```

The one-time maintainer `pin_inputs.py` is not called by preparation. It refuses to overwrite a reviewed lock and uses explicit versions, never latest. A cache refresh or tool replacement is a separately reviewed operation.

Preparation uses generated credential-free npm configuration, disables update notifications/audit/funding probes and populates npm's actual `_cacache` store. The initial preflight caught a wrong cache namespace before shipping; only exact integrity-checked tarballs may migrate from it, with no offline network fallback.

`.gitattributes` preserves upstream notice bytes; only the imported yt-dlp aggregate notice is exempt from whitespace lint because its original trailing spaces are part of the pinned upstream file. Application/source whitespace checks remain enabled.

## Profiles and identity gates

`CUEFLORA_BUILD_PROFILE=preview` is the default and preserves the public development key. `store-candidate` omits that key in the build itself; unknown profiles fail. Candidates do not contain a public/native-host binding and cannot use the preview helper merely by uploading them. `public-release.template.json` leaves publisher, assigned Chrome ID and public locations unset. No public installer is manufactured; private packages remain SHA-bound to their own runtime/preview identity.

`release.yml` now builds candidates only, with read-only repository permission and no store credentials, signing, tags or publication. The old submit/sign aliases refuse non-dry operations and never load `.env.submit`. CI definitions are prepared but have not been run remotely. Windows packaging CI needs the exact reviewed offline cache; external runner tools are not accepted as substitutes.

## Reproducibility and limitations

Matching source/input hashes are not a promise of byte-identical PE executables. The report compares complete runtime file hashes and Setup hashes from two new builds. PE timestamps, frozen bytecode/paths, generated inventories and archive metadata can differ. Differences must be explained from the observed report, not dismissed as harmless without inspection. Signing/authenticity, live browser registration, clean-machine operation, screenshots, public-policy/licence clearance and cross-platform certification remain separate gates.

The comparison additionally reads PE timestamps/checksums and frozen archive entries and compares every standard-library ZIP entry's contents/order. It distinguishes header-only EXE changes from payload changes and ZIP ordering; it does not promise reproducibility. Simulated uninstall/recovery retains a bounded owned-directory rename retry for observed transient Windows locks; permanent access errors still recover and fail visibly.

PE debug-directory timestamps are now included with their measured offsets, not merely the main PE timestamp/checksum. Only those explicit fields are normalized; unexplained code/payload differences are not classified as harmless. Setup changes must be traced to actual embedded runtime/header/library/inventory/binding entries.
