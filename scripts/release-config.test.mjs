import test from 'node:test';
import assert from 'node:assert/strict';
import { validateReleaseConfig, refusePublication } from './release-config.mjs';
import { buildProfile, chromeIdentity, bundledModulesPlugin } from './build-profile.mjs';
import { supplementalNotices } from './npm-notices.mjs';
import { createHash, generateKeyPairSync } from 'node:crypto';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
const valid = { CUEFLORA_RELEASE_OWNER: 'Fixture only', CHROME_EXTENSION_ID: 'a'.repeat(32),
  CUEFLORA_PRIVACY_URL: 'https://example.invalid/privacy', CUEFLORA_DOWNLOAD_URL: 'https://example.invalid/download', CUEFLORA_SUPPORT_URL: 'https://example.invalid/support' };
test('final binding needs owner, Chrome and public URLs, not Firefox or GitHub', () => {
  assert.equal(validateReleaseConfig(valid).publicReleaseAuthorized, false);
  for (const key of Object.keys(valid)) assert.throws(()=>validateReleaseConfig({...valid,[key]:''}));
  for (const url of ['http://example.invalid', 'https://secret@example.invalid', 'https://example.invalid/?secret=x']) assert.throws(()=>validateReleaseConfig({...valid,CUEFLORA_PRIVACY_URL:url}));
});

test('omitted WXT notice uses the exact original source release and npm identity', () => {
  const [notice] = supplementalNotices('wxt','0.21.4');
  assert.equal(notice.sha256,'7b0b00fcdbc6a036078aad84d0bc0fae240ac67144b86c911149c2daa37c9f85');
  assert.ok(notice.content.includes('Copyright (c) 2023 Aaron'));
  assert.throws(()=>supplementalNotices('wxt','0.20.20'));
  assert.throws(()=>supplementalNotices('wxt','0.21.4',{lock:{packages:{}}}));
  assert.throws(()=>supplementalNotices('wxt','0.21.4',{read:()=>Buffer.from('changed')}));
  assert.deepEqual(supplementalNotices('unlisted-package','1.0.0'),[]);
});

test('supplemental notice locks reject duplicate and unsafe bindings', () => {
  const item={name:'fixture',version:'1.0.0',integrity:'sha512-AAAA',file:'LICENSE',entry:'LICENSE',sha256:'a'.repeat(64),origin:'https://raw.githubusercontent.com/example/repo/tag/LICENSE'};
  const lock={packages:{'node_modules/fixture':{version:item.version,integrity:item.integrity}}};
  for (const policy of [{schema:2,packages:[item]},{schema:1,packages:[item,item]},
    ...['../LICENSE','.','..'].map(file=>({schema:1,packages:[{...item,file}]}))])
    assert.throws(()=>supplementalNotices('fixture','1.0.0',{lock,policy,read:()=>Buffer.from('fixture')}));
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

test('real bundle collector retains LICENCE and UNLICENSE original terms, not README text', () => {
  const temporary=mkdtempSync(join(tmpdir(),'cueflora-notice-test-'));
  try {
    const root=join(temporary,'node_modules','synthetic-notice-fixture');
    mkdirSync(root,{recursive:true});
    writeFileSync(join(root,'package.json'),JSON.stringify({name:'synthetic-notice-fixture',version:'1.0.0',license:'MIT'}));
    writeFileSync(join(root,'LICENCE.md'),'Original synthetic British terms\r\n');
    writeFileSync(join(root,'UNLICENSE'),'Original synthetic dedication\n');
    writeFileSync(join(root,'README.md'),'This is not licence text');
    const module=root.replaceAll('\\','/')+'/index.js';
    const assets=[];
    bundledModulesPlugin().generateBundle.call({emitFile(asset){assets.push(asset);}}, {},
      {'fixture.js':{type:'chunk',modules:{[module]:{}}}});
    const record=JSON.parse(assets.find(asset=>asset.fileName.startsWith('cueflora-bundled-dependencies')).source);
    assert.deepEqual(record.packages[0].notices.map(item=>item.entry).sort(),['LICENCE.md','UNLICENSE']);
    assert.equal(record.packages[0].notices.find(item=>item.entry==='LICENCE.md').sha256,
      createHash('sha256').update('Original synthetic British terms\r\n').digest('hex'));
    const terms=assets.find(asset=>asset.fileName.startsWith('cueflora-third-party-notices')).source;
    assert.ok(terms.includes('Original synthetic British terms\r\n'));
    assert.ok(terms.includes('Original synthetic dedication\n'));
    assert.ok(!terms.includes('This is not licence text'));
  } finally { rmSync(temporary,{recursive:true,force:true}); }
});
