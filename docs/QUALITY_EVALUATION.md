# CueFlora quality evidence and evaluation

## Scope and privacy

Capture is off unless the native process receives `CUEFLORA_EVIDENCE_DIR`. Use a local directory you control. Records include audio, Chinese and English; keep them private. Credential fields and signed URL query strings are excluded. Captures use exclusive UUID names and never overwrite older evidence. Ordinary workflow diagnostics contain counts, indexes, timings and reason codes, not subtitle text.

The implementation preserves explicit Run, structured IDs, TypeScript-only translation recovery, eight physical calls per original logical batch, and the existing English readability policy. It adds no phrase blacklist, semantic judge, automatic subtitle substitution or new model default.

## Capture a new production-path Run

From `C:\AI\CueFlora`, with your independently configured services available. This developer command explicitly performs inference and can incur charges; onboarding checks never invoke it:

```powershell
$env:CUEFLORA_EVIDENCE_DIR='C:\AI\cueflora\artifacts\quality'
$env:CUEFLORA_PROVIDER_CONFIG='C:\PRIVATE\providers.private.json'
node scripts/quality-run.mjs U_V6Jqg7PV4 '挖机勾水井斗齿都掉了' 'The excavator hooks the well and the bucket teeth have fallen off.'
```

The private JSON file must contain explicit `transcription` and `translation` provider objects with `label`, `baseUrl`, `apiKey` (empty when optional), `model` and `allowRemoteHttp`. No model or endpoint is supplied automatically. Keep this file outside public source. The harness uses jsdom/esbuild and real production API/prompt/batching/recovery/presentation code with stubbed UI and isolated preferences. Processing defaults remain batch 30, serial translation, ASR parallel 4 and 25 MiB uploads. It does not modify real browser settings. Set `CUEFLORA_PYTHON` if the developer Python executable differs. Supply exact title/description context; absent description is explicitly empty, not a reproduction of browser DOM.

For an actual browser Run, the browser-spawned native host must inherit the capture environment variable. Reload the rebuilt unpacked extension and start a new explicit Run. The headless harness does not establish this browser acceptance requirement.

## Exact upload and normalization replay

From `C:\AI\cueflora\native`:

```powershell
../.packaging-venv/Scripts/python.exe -B -m cueflora_host.quality_cli replay --capture CAPTURE_DIRECTORY --endpoint YOUR_ASR_BASE
../.packaging-venv/Scripts/python.exe -B -m cueflora_host.quality_cli normalize --capture CAPTURE_DIRECTORY
```

Replace `CAPTURE_DIRECTORY` with an absolute trusted saved Run directory. Replay verifies the upload hash and sends those exact bytes with saved parameters and filename; it does not rerun the encoder. Replay requires explicit `--endpoint`; `CUEFLORA_ASR_KEY` supplies optional authentication. No credentials are written into evidence.

Normalization replay executes the saved normalizer source snapshot: only use a trusted local capture, not an untrusted downloaded folder. It verifies its hash and compares identical raw responses through old/current paths, checking old cue reproduction, lexical sequence and the complete word text/timestamp multiset. Segment associations are explicitly temporal, not invented exact semantic matches.

## Controlled audio experiments

```powershell
$env:CUEFLORA_EVIDENCE_DIR='C:\AI\cueflora\artifacts\quality'
../.packaging-venv/Scripts/python.exe -B -m cueflora_host.quality_benchmark --capture BASELINE_DIRECTORY --high-format 234 --endpoint YOUR_ASR_BASE
../.packaging-venv/Scripts/python.exe -B -m cueflora_host.quality_benchmark --replay-prepared BENCHMARK_DIRECTORY --endpoint YOUR_ASR_BASE
../.packaging-venv/Scripts/python.exe -B -m cueflora_host.quality_summary BENCHMARK_DIRECTORY
```

Explicit format 234 is a candidate for these two videos, not a global recommendation. Metadata and alignment must establish the same content before causal conclusions. Five arms are A: low/48 kHz Opus 24 kbps; B: high/48 kHz Opus; C: low/48 kHz FLAC; D: high/48 kHz FLAC; D16: high/16 kHz FLAC (separate resampling arm). All use mono and identical requested clip boundaries. Inputs must fit the baseline upload limit without rechunking.

Sources are decoded fully to native-rate/channel float PCM WAV before clip seeking. This avoids bitrate-estimated seeking in raw AAC streams mislabeled `.mp4`. These controlled files are not byte-identical production uploads. Audio alignment measurements are only screens; listening is required. Different codec decodes are not expected to be sample-identical. Exclude uncertain track pairs.

`--prepare-only` prepares inputs without inference. `--replay-prepared` hashes and resends existing inputs, appending independent results for repeatability. `--only-starts 535,555` restricts predefined regions. Results are never promoted automatically. Empty output is not automatically missed speech, and nonempty output is not automatically invented speech.

Optional `--reference` reads a JSON object keyed by clip start seconds. Entries must have `text`, `audioReviewed: true`, and `uncertain: false` for CER calculation. Do not populate it from ASR output or burned-in captions and call it audio-reviewed. CER ignores punctuation/spacing; meaning errors, missed/invented speech and timing errors need separate audio-reviewed annotations. Uncertain dialectal speech must remain unscored.

## Translation evaluation independent of recognition

```powershell
../.packaging-venv/Scripts/python.exe -B -m cueflora_host.quality_translation --capture CAPTURE_DIRECTORY --request translation-request-UUID.json --endpoint YOUR_TRANSLATION_BASE
```

This sends three controls and three temperature-zero requests, interleaved, preserving the saved body except temperature. It is a developer-only experiment, not the production recovery engine or a change to its budget. `CUEFLORA_TRANSLATION_KEY` supplies optional authentication. The observed first-batch fabrication is retained in `native/cueflora_host/fixtures/translation_fabrication_case.json` and its regression test explicitly documents that valid IDs do not imply faithful translation.

Evaluate both actual ASR input and separately audio-reviewed Chinese when available. Review every assigned cue's meaning and alignment, not just the presence/absence of an outro phrase. Do not promote temperature, context, batch-size or architectural changes without broader faithful/unfaithful controls and latency/recovery measurements.

## Verification and remaining acceptance

Run `npm run typecheck`, `npm test`, both production browser builds, the native unittest modules listed in AGENTS.md, Python syntax compilation, native framed PING and `git diff --check`. Also reload the unpacked extension and inspect a real Run's timing, diagnostics and capture/cache behavior. Offline tests and headless inference are not browser acceptance or evidence of improved semantic accuracy.
