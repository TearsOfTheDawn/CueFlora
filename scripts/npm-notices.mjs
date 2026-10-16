// Original supplemental notices for exact npm packages that omit their terms.
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';

export function supplementalNotices(name, version, options = {}) {
  const policy = options.policy ?? JSON.parse(readFileSync(new URL('../packaging/npm-notices.lock.json', import.meta.url), 'utf8'));
  if (policy?.schema !== 1 || !Array.isArray(policy.packages)) throw Error('Invalid npm notice lock');
  const matches = policy.packages.filter(item => item.name === name);
  if (!matches.length) return [];
  if (matches.length !== 1) throw Error('Duplicate npm notice binding');
  const item = matches[0];
  const lock = options.lock ?? JSON.parse(readFileSync(new URL('../package-lock.json', import.meta.url), 'utf8'));
  const pin = lock.packages?.['node_modules/' + name];
  if (version !== item.version || pin?.version !== version || pin?.integrity !== item.integrity ||
      !/^sha512-[A-Za-z0-9+/]+=*$/.test(item.integrity ?? '') ||
      !/^[A-Za-z0-9._-]+$/.test(item.file ?? '') || ['.', '..'].includes(item.file) ||
      !/^[A-Za-z0-9._-]+$/.test(item.entry ?? '') || ['.', '..'].includes(item.entry) ||
      !/^[a-f0-9]{64}$/.test(item.sha256 ?? '') ||
      !/^https:\/\/raw\.githubusercontent\.com\/[^?#]+$/.test(item.origin ?? ''))
    throw Error('Supplemental npm notice identity mismatch');
  const body = options.read ? options.read(item.file) : readFileSync(new URL('../packaging/notices/' + item.file, import.meta.url));
  if (createHash('sha256').update(body).digest('hex') !== item.sha256) throw Error('Supplemental npm notice hash mismatch');
  return [{ entry: item.entry, sha256: item.sha256, origin: item.origin, content: body.toString('utf8') }];
}
