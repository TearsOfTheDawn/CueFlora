import { buildProfile } from './build-profile.mjs';
export function validateReleaseConfig(env) {
  if (!env.CUEFLORA_RELEASE_OWNER?.trim()) throw Error('Release owner required');
  if (!/^[a-p]{32}$/.test(env.CHROME_EXTENSION_ID ?? '')) throw Error('Final Chrome identity required');
  for (const field of ['CUEFLORA_PRIVACY_URL', 'CUEFLORA_DOWNLOAD_URL', 'CUEFLORA_SUPPORT_URL']) {
    let url; try { url = new URL(env[field]); } catch { throw Error('Public HTTPS location required'); }
    if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash) throw Error('Invalid public location');
  }
  return { profile: buildProfile('store-candidate'), publicReleaseAuthorized: false, redistributionApproved: false };
}
export function refusePublication() { throw Error('Submission/signing is disabled. Preparation is not release clearance.'); }
