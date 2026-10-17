import { readFileSync, readdirSync } from 'node:fs';
import { createHash, createPublicKey } from 'node:crypto';
import { supplementalNotices } from './npm-notices.mjs';

export function buildProfile(value = 'preview') {
  if (!['preview', 'store-candidate', 'acceptance', 'github'].includes(value)) throw Error('Unknown CueFlora build profile');
  return value;
}
export function chromeIdentity(profile, preview, configuration) {
  profile = buildProfile(profile);
  if (profile === 'preview') return { key: preview.publicKey };
  if (profile === 'store-candidate') return {};
  const key = configuration?.chromePublicKey;
  if (profile === 'github' && configuration?.distribution !== 'github') throw Error('GitHub build needs an explicit GitHub configuration');
  if (typeof key !== 'string' || !/^[A-Za-z0-9+/]+={0,2}$/.test(key)) throw Error('Keyed build needs the release Chrome public key');
  const bytes = Buffer.from(key,'base64');
  if (bytes.length < 64 || bytes.length > 16384 || bytes.toString('base64') !== key) throw Error('Invalid Store public key');
  try { createPublicKey({key:bytes,format:'der',type:'spki'}); } catch { throw Error('Store key must be a valid DER public key, not arbitrary base64'); }
  const id = [...createHash('sha256').update(bytes).digest('hex').slice(0,32)].map(c=>String.fromCharCode(97+parseInt(c,16))).join('');
  if (id !== configuration.extensionIds?.chrome || id === preview.chromeId) throw Error('Acceptance key/identity mismatch or development identity');
  return { key };
}
export function bundledModulesPlugin() {
  return { name: 'cueflora-bundled-inventory', generateBundle(_options, bundle) {
    const modules = new Set();
    for (const output of Object.values(bundle)) if (output.type === 'chunk') {
      for (const module of Object.keys(output.modules)) if (module.includes('/node_modules/')) modules.add(module);
    }
    const packages = new Map();
    const notices = new Map();
    const chunkPackages = {};
    for (const module of modules) {
      const relative = module.split('/node_modules/').at(-1).split('?')[0];
      const name = relative.startsWith('@') ? relative.split('/').slice(0, 2).join('/') : relative.split('/')[0];
      const root = module.slice(0, module.lastIndexOf('/node_modules/')) + '/node_modules/' + name;
      try {
        const pkg = JSON.parse(readFileSync(root + '/package.json', 'utf8'));
        const noticeFiles = readdirSync(root,{withFileTypes:true}).filter(entry=>entry.isFile() && /licen[cs]e|copying|notice|copyright/i.test(entry.name));
        const records = noticeFiles.map(entry=>{const content=readFileSync(root+'/'+entry.name,'utf8'); notices.set(name+'/'+entry.name,content); return {entry:entry.name,sha256:createHash('sha256').update(content).digest('hex')};});
        if (!records.length) for (const {content,...record} of supplementalNotices(name,pkg.version)) {
          notices.set(name+'/'+record.entry,content); records.push(record);
        }
        if (!records.length) throw Error('Bundled package has no retained notice: '+name);
        packages.set(name, { name, version: pkg.version, license: pkg.license, notices:records });
      } catch (error) { throw Error('Bundled dependency licence evidence unavailable: '+name,{cause:error}); }
    }
    const chunks = Object.keys(bundle).sort();
    for (const [file,output] of Object.entries(bundle)) if (output.type === 'chunk') {
      chunkPackages[file] = [...new Set(Object.keys(output.modules).filter(module=>module.includes('/node_modules/')).map(module=>{
        const relative=module.split('/node_modules/').at(-1).split('?')[0];
        return relative.startsWith('@') ? relative.split('/').slice(0,2).join('/') : relative.split('/')[0];
      }))].sort();
    }
    const id = createHash('sha256').update(chunks.join('\n')).digest('hex').slice(0,12);
    this.emitFile({ type: 'asset', fileName: `cueflora-bundled-dependencies-${id}.json`, source: JSON.stringify({ scope: 'Observed Vite chunk modules only; native libraries and build tools are separate.', chunks, chunkPackages, packages: [...packages.values()].sort((a,b)=>a.name.localeCompare(b.name)) }, null, 2) + '\n' });
    const ownLicence = readFileSync(new URL('../LICENSE.md',import.meta.url),'utf8');
    this.emitFile({type:'asset',fileName:`cueflora-third-party-notices-${id}.txt`,source:ownLicence+'\n'+[...notices].sort(([a],[b])=>a.localeCompare(b)).map(([name,content])=>'\n===== '+name+' =====\n'+content).join('\n')});
  } };
}
