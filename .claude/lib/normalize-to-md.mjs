/**
 * Convert a heavy document (PDF / docx / xlsx / pptx) to cached Markdown before a model reads it.
 * Thin node wrapper over `.claude/lib/doc_to_md.py`, which holds the real implementation
 * (conversion needs the Python libraries and, for PDF, pdftotext). Resolves to the path to read.
 *
 * Callers: node scripts (`import { normalizeToMd }`), or the CLI:
 *   node .claude/lib/normalize-to-md.mjs <file> [--force] [--no-cache] [--print] [--max-rows <n>]
 */
import { spawn } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PY = path.join(HERE, 'doc_to_md.py');

/**
 * @param {string} src  source document path
 * @param {{force?:boolean, noCache?:boolean, maxRows?:number}} [opts]
 * @returns {Promise<{mdPath:string, source:string, cached:boolean}>}
 */
export function normalizeToMd(src, opts = {}) {
  const argv = [PY, src];
  if (opts.force) argv.push('--force');
  if (opts.noCache) argv.push('--no-cache');
  if (opts.maxRows != null) argv.push('--max-rows', String(opts.maxRows));

  return new Promise((resolve, reject) => {
    const proc = spawn('python3', argv);
    let out = '', err = '';
    proc.stdout.on('data', d => (out += d));
    proc.stderr.on('data', d => (err += d));
    proc.on('error', reject);
    proc.on('close', code => {
      if (code !== 0) return reject(new Error(err.trim() || `doc_to_md.py exited ${code}`));
      resolve({ mdPath: out.trim(), source: src, cached: err.includes('cache hit') });
    });
  });
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) {
  const args = process.argv.slice(2);
  const mi = args.indexOf('--max-rows');
  const maxRows = mi >= 0 ? Number(args[mi + 1]) : undefined;
  const src = args.find((a, i) => !a.startsWith('--') && i !== mi + 1);
  const usage = 'usage: normalize-to-md.mjs <file> [--force] [--no-cache] [--print] [--max-rows <n>]';
  if (args.includes('--help') || args.includes('-h')) { console.log(usage); process.exit(0); }
  if (!src) { console.error(usage); process.exit(2); }
  if (args.includes('--print')) {
    // --print streams Markdown, which the library function does not return: delegate directly.
    const p = spawn('python3', [PY, ...args], { stdio: 'inherit' });
    p.on('close', code => process.exit(code ?? 1));
  } else {
    normalizeToMd(src, { force: args.includes('--force'), noCache: args.includes('--no-cache'), maxRows })
      .then(r => console.log(r.mdPath))
      .catch(e => { console.error(e.message); process.exit(1); });
  }
}
