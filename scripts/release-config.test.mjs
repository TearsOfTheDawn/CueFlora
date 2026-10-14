import test from 'node:test';
import assert from 'node:assert/strict';
import { validateReleaseConfig, refusePublication } from './release-config.mjs';
import { buildProfile, chromeIdentity, bundledModulesPlugin } from './build-profile.mjs';
import { createHash, generateKeyPairSync } from 'node:crypto';
const valid = { CUEFLORA_RELEASE_OWNER: 'Fixture only', CHROME_EXTENSION_ID: 'a'.repeat(32),
  CUEFLORA_PRIVACY_URL: 'https://example.invalid/privacy', CUEFLORA_DOWNLOAD_URL: 'https://example.invalid/download', CUEFLORA_SUPPORT_URL: 'https://example.invalid/support' };
test('final binding needs owner, Chrome and public URLs, not Firefox or GitHub', () => {
  assert.equal(validateReleaseConfig(valid).publicReleaseAuthorized, false);
  for (const key of Object.keys(valid)) assert.throws(()=>validateReleaseConfig({...valid,[key]:''}));
  for (const url of ['http://example.invalid', 'https://secret@example.invalid', 'https://example.invalid/?secret=x']) assert.throws(()=>validateReleaseConfig({...valid,CUEFLORA_PRIVACY_URL:url}));
});
test('preview has stable key, candidates have none and unknown profiles fail', () => {
  assert.equal(buildProfile(), 'preview');
  assert.deepEqual(chromeIdentity('preview',{publicKey:'fixture'}),{key:'fixture'});
  assert.deepEqual(chromeIdentity('store-candidate',{publicKey:'fixture'}),{});
  assert.throws(()=>buildProfile('public'));
});
test('publication cannot be enabled using identities or authorization flags', () => assert.throws(()=>refusePublication(valid)));
test('acceptance uses the assigned Store key, rejects mismatches and remains distinct from a keyless upload',()=>{
  const bytes=generateKeyPairSync('rsa',{modulusLength:1024}).publicKey.export({type:'spki',format:'der'});
  const key=bytes.toString('base64');
  const id=[...createHash('sha256').update(bytes).digest('hex').slice(0,32)].map(c=>String.fromCharCode(97+parseInt(c,16))).join('');
  const configuration={chromePublicKey:key,extensionIds:{chrome:id}};
  assert.deepEqual(chromeIdentity('acceptance',{chromeId:'a'.repeat(32)},configuration),{key});
  assert.deepEqual(chromeIdentity('store-candidate',{},configuration),{});
  assert.throws(()=>chromeIdentity('acceptance',{},{}));
  assert.throws(()=>chromeIdentity('acceptance',{chromeId:id},configuration));
  assert.throws(()=>chromeIdentity('acceptance',{}, {...configuration,extensionIds:{chrome:'b'.repeat(32)}}));
  assert.throws(()=>chromeIdentity('acceptance',{}, {...configuration,chromePublicKey:Buffer.alloc(140,1).toString('base64')}));
});
test('per-entrypoint inventories do not overwrite each other or expose absolute paths', () => {
  const assets = [];
  const plugin = bundledModulesPlugin();
  const context = {emitFile(asset){assets.push(asset);}};
  plugin.generateBundle.call(context,{}, {'background.js':{type:'chunk',modules:{}}});
  plugin.generateBundle.call(context,{}, {'youtube.js':{type:'chunk',modules:{}}});
  const inventories=assets.filter(asset=>asset.fileName.startsWith('cueflora-bundled-dependencies'));
  assert.notEqual(inventories[0].fileName,inventories[1].fileName);
  assert.deepEqual(JSON.parse(inventories[0].source).chunks,['background.js']);
  assert.ok(!inventories[0].source.includes('C:/'));
  const notices=assets.filter(asset=>asset.fileName.startsWith('cueflora-third-party-notices'));
  assert.equal(notices.length,2); assert.ok(notices[0].source.includes('MIT'));
});
