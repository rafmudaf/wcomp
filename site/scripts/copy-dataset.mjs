// Copies the generated data (see `wcomp/dataset.py`) into the site's `public/`
// directory so it's served as static JSON, fetched by the browser at runtime.
// This keeps building the site (this script + `astro build`) fully decoupled
// from generating the data (Python, run separately -- see repo root README).
import { cpSync, existsSync, rmSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const siteRoot = path.resolve(fileURLToPath(import.meta.url), '..', '..');
const source = path.join(siteRoot, '..', 'dataset');
const dest = path.join(siteRoot, 'public', 'dataset');

if (!existsSync(source)) {
  console.error(
    `Dataset not found at ${source}.\n` +
    `Generate it first: conda run -n wcomp python -m wcomp.dataset`
  );
  process.exit(1);
}

rmSync(dest, { recursive: true, force: true });
cpSync(source, dest, { recursive: true });
console.log(`Copied dataset from ${source} to ${dest}`);
