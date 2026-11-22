// Test-only driver for the librarian scripts. Prints JSON.
//   librarian-driver.mjs crossref-map          every mapped Crossref type -> built item
//   librarian-driver.mjs save-fail <queue>     saveQueue with a rename that throws
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', '..');
const mod = (p) => import(pathToFileURL(path.join(root, p)).href);
const [cmd, arg] = process.argv.slice(2);
const out = (v) => console.log(JSON.stringify(v));

if (cmd === 'crossref-map') {
  const cr = await mod('scripts/zotero/_lib/crossref-item.mjs');
  const base = {
    title: ['A title'], subtitle: ['sub'], 'container-title': ['Series name', 'Container name'], publisher: 'Pub', ISBN: ['111'], ISSN: ['2222-3333'],
    volume: '3', issue: '2', page: '1-9', issued: { 'date-parts': [[2025, 3]] }, DOI: '10.1234/x', URL: 'https://doi.org/10.1234/x', language: 'en',
    author: [{ given: 'A', family: 'Author' }], editor: [{ given: 'E', family: 'Editor' }], event: { name: 'Conf' }, institution: [{ name: 'Inst' }], abstract: '<p>Abstract text</p>',
  };
  const items = {};
  for (const type of Object.keys(cr.CROSSREF_TO_ZOTERO_TYPE)) items[type] = cr.crossrefWorkToZoteroItem({ ...base, type });
  out({ mapping: cr.CROSSREF_TO_ZOTERO_TYPE, items, unmapped: cr.crossrefWorkToZoteroItem({ ...base, type: 'dataset' }) });
} else if (cmd === 'save-fail') {
  const q = await mod('scripts/zotero/approval-queue.mjs');
  const dir = path.dirname(arg);
  const io = { ...fs, renameSync() { throw new Error('simulated rename failure'); } };
  let thrown = null;
  try { q.saveQueue(arg, { date: 'x', actions: [{ id: 99, type: 'add_tag', status: 'applied' }] }, io); } catch (e) { thrown = e.message; }
  out({ thrown, content: fs.readFileSync(arg, 'utf8'), leftovers: fs.readdirSync(dir).filter((f) => f.endsWith('.tmp')) });
}
