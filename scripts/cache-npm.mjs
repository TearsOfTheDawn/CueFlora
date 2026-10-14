// Seed/verify only exact package-lock tarballs; never resolve latest versions.
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { createHash } from 'node:crypto';
const cache = resolve(process.argv[2] || 'artifacts/input-cache-v1/npm');
const offline = process.argv.includes('--offline');
const require = createRequire(join(process.env.CUEFLORA_NPM_MODULES || join(dirname(process.execPath), 'node_modules/npm'), 'package.json'));
const pacote = require('pacote');
const cacache = require('cacache');
const lock = JSON.parse(readFileSync('package-lock.json','utf8'));
const entries = [...new Map(Object.values(lock.packages).filter(item=>item.resolved).map(item=>[item.resolved,item])).values()];
for (const item of entries) {
  const url = new URL(item.resolved);
  if (url.protocol !== 'https:' || url.hostname !== 'registry.npmjs.org' || url.username || url.password || !/^sha512-[A-Za-z0-9+/]+=*$/.test(item.integrity || '')) throw Error('Unpinned or unapproved npm input');
}
mkdirSync(cache,{recursive:true});
const records = [];
let next = 0;
await Promise.all(Array.from({length:8},async()=>{
  while (next < entries.length) {
    const item = entries[next++];
    let body;
    try { body = await pacote.tarball(item.resolved,{integrity:item.integrity,cache:join(cache,'_cacache'),offline,ignoreScripts:true}); }
    catch (error) {
      if (!offline || !['ENOENT','ENOTCACHED'].includes(error.code)) throw error;
      // Migrate exact hash-checked tarballs from the initial cache namespace.
      // No network or alternate version is permitted during this migration.
      body = await cacache.get.byDigest(cache,item.integrity);
    }
    if ('sha512-' + createHash('sha512').update(body).digest('base64') !== item.integrity) throw Error('npm tarball integrity mismatch');
    await cacache.put(join(cache,'_cacache'),'cueflora:locked:'+item.resolved,body,{integrity:item.integrity});
    records.push({url:item.resolved,version:item.version,integrity:item.integrity,sha256:createHash('sha256').update(body).digest('hex'),bytes:body.length});
  }
}));
writeFileSync(join(cache,'cueflora-npm-inputs.json'),JSON.stringify({offline,packageLockSha256:createHash('sha256').update(readFileSync('package-lock.json')).digest('hex'),files:records.sort((a,b)=>a.url.localeCompare(b.url))},null,2)+'\n');
console.log(`${offline?'Verified offline':'Cached'} ${records.length} exact npm tarballs`);
