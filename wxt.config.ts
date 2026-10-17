import { defineConfig } from 'wxt';
import { readFileSync } from 'node:fs';
import { buildProfile, chromeIdentity, bundledModulesPlugin } from './scripts/build-profile.mjs';
import { validatedLinks } from './utils/publicLinks';
const preview = JSON.parse(readFileSync(new URL('./preview-identity.json', import.meta.url), 'utf8'));
const profile = buildProfile(process.env.CUEFLORA_BUILD_PROFILE);
let publicLinks = null;
let configuration = null;
if (process.env.CUEFLORA_PUBLIC_CONFIG) {
  if (profile === 'preview') throw Error('Preview must not link to a public-identity helper');
  configuration = JSON.parse(readFileSync(process.env.CUEFLORA_PUBLIC_CONFIG, 'utf8'));
  if (!configuration.owner?.trim() || !/^[a-p]{32}$/.test(configuration.extensionIds?.chrome ?? '') || configuration.extensionIds.chrome === preview.chromeId)
    throw Error('Real publisher and assigned Chrome identity required for public links');
  publicLinks = validatedLinks(configuration);
  if (!publicLinks) throw Error('Real public HTTPS domain locations required');
}
if (['acceptance', 'github'].includes(profile) && !configuration) throw Error('Keyed build requires the release Chrome identity');

export default defineConfig({
  vite: () => ({ plugins: [bundledModulesPlugin()], define: { __CUEFLORA_STORE_CANDIDATE__: JSON.stringify(profile !== 'preview'), __CUEFLORA_PUBLIC_LINKS__:JSON.stringify(publicLinks) } }),
  manifest: ({ browser }) => ({
    name: 'CueFlora — AI Subtitles & Translation for YouTube',
    description: 'AI subtitles and translation for YouTube using your chosen services. Requires the CueFlora helper for AI generation.',
    ...(browser === 'chrome' ? chromeIdentity(profile, preview, configuration) : {}),
    icons: { 16: '/icon/16.png', 32: '/icon/32.png', 48: '/icon/48.png', 128: '/icon/128.png' },
    action: { default_title: 'CueFlora setup' },
    host_permissions: ['https://*.youtube.com/*'],
    permissions: ['nativeMessaging', 'storage'],
    ...(browser === 'firefox' ? { browser_specific_settings: {
      gecko: {
        ...(process.env.FIREFOX_EXTENSION_ID ? { id: process.env.FIREFOX_EXTENSION_ID } : {}),
        strict_min_version: '128.0',
        // Local builds must never inherit an upstream update feed.
      },
    } } : {}),
  }),
});
