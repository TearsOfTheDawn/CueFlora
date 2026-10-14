import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
const root = fileURLToPath(new URL('../',import.meta.url));
const python = process.env.CUEFLORA_BUILD_PYTHON || join(root,'.packaging-venv','Scripts','python.exe');
const result = spawnSync(python,[join(root,'packaging','prepare_windows.py'),...process.argv.slice(2)],{cwd:root,stdio:'inherit',shell:false});
if (result.error) { console.error('Pinned Windows preparation environment unavailable. See PUBLIC_RELEASE_PREPARATION.md.'); process.exitCode = 1; }
else process.exitCode = result.status ?? 1;
