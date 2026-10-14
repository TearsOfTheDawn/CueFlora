/** Headless execution of the production TS API and native handlers.
 * UI effects are stubbed; inference/prompt/batching/recovery/presentation are real.
 * Never describes this as a browser acceptance test. Output is opt-in local evidence.
 */
import { build } from 'esbuild';
import { JSDOM } from 'jsdom';
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
import path from 'node:path';
import vm from 'node:vm';
import { webcrypto } from 'node:crypto';
import { readFileSync } from 'node:fs';

const [videoId, title, description = ''] = process.argv.slice(2);
if (!/^[\w-]{11}$/.test(videoId || '') || !title || !process.env.CUEFLORA_EVIDENCE_DIR || !process.env.CUEFLORA_PROVIDER_CONFIG) {
    throw new Error('Usage: set CUEFLORA_EVIDENCE_DIR and CUEFLORA_PROVIDER_CONFIG to your private configuration file, then node scripts/quality-run.mjs VIDEO_ID TITLE [DESCRIPTION]. This explicitly runs inference.');
}
const python = process.env.CUEFLORA_PYTHON || path.resolve('.packaging-venv/Scripts/python.exe');
const configuration = JSON.parse(readFileSync(process.env.CUEFLORA_PROVIDER_CONFIG, 'utf8'));
const dom = new JSDOM('<html><head><meta name="description"></head><body></body></html>', {
    url: `https://www.youtube.com/watch?v=${videoId}`,
});
dom.window.document.title = `${title} - YouTube`;
dom.window.document.querySelector('meta').content = description;
const storage = dom.window.localStorage;
for (const [key, value] of Object.entries({
    transcription_max_parallel: '4', transcription_mb_per_req: '25', translation_batch_size: '30',
    transcription_lang: 'transcription:zh-CN', translation_lang: 'en',
})) storage.setItem(`cueflora_${key}`, value);

const bridge = (msg) => new Promise((resolve, reject) => {
    console.log(`Native ${msg.type}${msg.cues ? ` (${msg.cues.length} cues)` : ''}`);
    const child = spawn(python, ['-B', '-m', 'cueflora_host.quality_cli', 'message'], {
        cwd: path.resolve('native'), env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
        windowsHide: true,
    });
    let output = ''; let error = '';
    child.stdout.setEncoding('utf8'); child.stderr.setEncoding('utf8');
    child.stdout.on('data', (chunk) => { output += chunk; });
    child.stderr.on('data', (chunk) => { error = (error + chunk).slice(-2000); });
    child.on('error', reject);
    child.on('close', (code) => {
        if (code) return reject(new Error(`Native CLI exit ${code}: ${error}`));
        try { resolve(JSON.parse(output)); } catch { reject(new Error(`Invalid native CLI result: ${error}`)); }
    });
    child.stdin.end(JSON.stringify(msg));
});
const bundled = await build({ stdin: { contents: `
    export { startTranscription, translateSubtitles } from './entrypoints/youtube.content/api';
    export { state } from './utils/state';
    export { beginWorkflow, transitionWorkflow, completeWorkflow } from './utils/workflow';
    export { refreshProviderSummary, bindRunProviders, releaseRunProviders } from './utils/providerClient';
    export { createCacheRepository } from './utils/cacheRepository';
    export { createPreferencesService } from './utils/preferences';
    export { initializePreferences } from './utils/preferenceClient';
    export { providerSummaryWithIdentity } from './utils/providers';
    export { validateProvider } from './utils/providers';
    export { assertControlledEvidence } from './utils/controlledEvidence';
`, resolveDir: process.cwd(), loader: 'ts' }, bundle: true, write: false,
    platform: 'node', format: 'cjs', plugins: [{ name: 'headless-ui', setup(b) {
        b.onResolve({ filter: /^\.\/(ui|render)$/ }, (args) => {
            if (args.importer.endsWith('api.ts')) return { path: args.path, namespace: 'headless-ui' };
        });
        b.onLoad({ filter: /.*/, namespace: 'headless-ui' }, () => ({
            contents: 'export const populateDropdowns = () => {}; export const startRenderLoop = () => {};',
        }));
    } }],
});
const mod = { exports: {} };
vm.runInNewContext(bundled.outputFiles[0].text, {
    module: mod, exports: mod.exports, require: createRequire(import.meta.url), console,
    window: dom.window, document: dom.window.document, location: dom.window.location,
    localStorage: storage, CustomEvent: dom.window.CustomEvent, Event: dom.window.Event, URL, URLSearchParams, Date, setTimeout, clearTimeout, crypto: webcrypto, TextEncoder,
    browser: { runtime: { sendMessage: (msg) => headlessRequest(msg), onMessage: { addListener() {}, removeListener() {} } },
        storage: { local: { get: async (key) => ({ [key]: 'local' }) } } },
});
const api = mod.exports;
// Explicit headless provider boundary, not browser registration/security acceptance.
const providers = Object.fromEntries(['transcription','translation'].map(stage => [stage, api.validateProvider(configuration[stage])]));
if (Object.values(providers).some(provider=>!provider.baseUrl || !provider.model)) throw Error('Both providers must be explicitly configured for this inference harness.');
const summary = await api.providerSummaryWithIdentity({ revision: 'headless-fixed', ...providers });
const cacheData = {};
const cache = api.createCacheRepository({ get: async () => structuredClone(cacheData), set: async values => Object.assign(cacheData, structuredClone(values)), remove: async keys => keys.forEach(key => delete cacheData[key]) });
const preferences = api.createPreferencesService({ get: async () => structuredClone(cacheData), set: async values => Object.assign(cacheData, structuredClone(values)) });
let boundJob;
async function headlessRequest(msg) {
    if (msg.type === 'PREFERENCES_INIT') return preferences.initialize(Object.fromEntries(Object.keys(storage).map(key=>[key,storage.getItem(key)])));
    if (msg.type === 'PREFERENCES_SAVE') return { value: await preferences.save(msg.key,msg.value) };
    if (msg.type === 'PROVIDERS_SUMMARY') return summary;
    if (msg.type === 'PROVIDERS_BIND') { if (msg.revision !== summary.revision) throw Error('Stale headless configuration'); boundJob = msg.jobId; return summary; }
    if (msg.type === 'PROVIDERS_RELEASE') { boundJob = undefined; return {}; }
    if (msg.type === 'CACHE_PUT') return cache.put(msg.key, msg.cues, msg.metadata);
    if (msg.type === 'CACHE_GET') return cache.get(msg.key);
    if (msg.type === 'CACHE_LIST') return cache.list();
    if (msg.type === 'CACHE_REMOVE') return cache.remove(msg.key);
    if (msg.jobId !== boundJob) throw Error('Unbound headless request');
    if (msg.type === 'TRANSCRIBE_NATIVE') msg = { ...msg, whisperConfig: { ...msg.whisperConfig, ...providers.transcription } };
    if (msg.type === 'TRANSLATE_NATIVE') msg = { ...msg, translateConfig: providers.translation };
    return bridge(msg);
}
await api.initializePreferences();
await api.refreshProviderSummary();
const jobId = api.beginWorkflow(videoId, true);
await api.bindRunProviders(jobId);
await api.startTranscription('zh-CN', jobId);
console.log('Baseline captured:', api.state.workflow.diagnostics.transcription.captureId);
api.transitionWorkflow(jobId, 'transcription_complete');
api.transitionWorkflow(jobId, 'translating');
await api.translateSubtitles('en', 'transcription:zh-CN', jobId);
api.assertControlledEvidence(api.state.workflow.diagnostics);
api.completeWorkflow(jobId);
await api.releaseRunProviders(jobId);
console.log('HEADLESS_PRODUCTION_PATH', JSON.stringify(api.state.workflow.diagnostics));
