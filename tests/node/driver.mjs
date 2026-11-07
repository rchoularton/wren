// Test-only driver: exercises zotero-client / download.mjs pieces and prints JSON.
//   driver.mjs urls | attach <file> | patch | download <url> | env <text-file> | dotenv <root>
import fs from 'node:fs';
import { pathToFileURL } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', '..');
const lib = await import(pathToFileURL(path.join(root, 'scripts/zotero/_lib/zotero-client.mjs')).href);
const dl = await import(pathToFileURL(path.join(root, 'scripts/zotero/sources/download.mjs')).href);
const [cmd, arg] = process.argv.slice(2);
const out = (v) => console.log(JSON.stringify(v));
const fakeFetch = await lib.loadFetch(process.env);
const err = (e) => ({ error: { message: e.message, code: e.code, status: e.status } });

try {
  if (cmd === 'urls') {
    const calls = [];
    const stub = async (url, opts) => { calls.push({ url, headers: opts.headers }); return new Response('[]', { status: 200 }); };
    const results = {};
    for (const [name, env] of Object.entries({
      user: { ZOTERO_API_KEY: 'k1', ZOTERO_LIBRARY_ID: '42' },
      group: { ZOTERO_API_KEY: 'k2', ZOTERO_LIBRARY_ID: '77', ZOTERO_LIBRARY_TYPE: 'group' },
    })) {
      const c = lib.createClient({ fetch: stub, env });
      await c.request('/items?limit=1');
      results[name] = { base: c.libraryURL(), call: calls[calls.length - 1] };
    }
    out(results);
  } else if (cmd === 'attach') {
    const c = lib.createClient({ fetch: fakeFetch, env: process.env });
    out(await c.attachPdfToItem('PARENT01', arg, { title: 'My title' }));
  } else if (cmd === 'patch') {
    const c = lib.createClient({ fetch: fakeFetch, env: process.env });
    out(await c.request('/items/ITEM0001', { method: 'PATCH', body: { title: 'x' }, version: 5 }));
  } else if (cmd === 'retry429') {
    const sleeps = [];
    const c = lib.createClient({ fetch: fakeFetch, env: process.env, sleep: async (ms) => { sleeps.push(ms); } });
    const r = await c.request('/items/ITEM0001');
    out({ status: r.status, sleeps });
  } else if (cmd === 'download') {
    const r = await dl.fetchPdf(arg, { fetch: fakeFetch });
    out({ ok: r.ok, reason: r.reason, length: r.buffer?.length });
  } else if (cmd === 'env') {
    out(lib.parseEnv(fs.readFileSync(arg, 'utf8')));
  } else if (cmd === 'dotenv') {
    const env = { CLAUDE_PROJECT_DIR: arg, PRESET: 'keep' };
    lib.loadDotEnv(env);
    out(env);
  }
} catch (e) {
  out(err(e));
}
