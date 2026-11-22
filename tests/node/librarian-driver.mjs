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
} else if (cmd === 'crossref-odd') {
  const cr = await mod('scripts/zotero/_lib/crossref-item.mjs');
  const w = { type: 'journal-article', title: ['T'], DOI: '10.1/x' };
  const odd = { ...w, issued: { 'date-parts': [[null]] }, 'published-online': { 'date-parts': [[2024, 5]] } };
  const created = { ...w, issued: { 'date-parts': [[null]] }, created: { 'date-parts': [[2023, 1, 2]] } };
  out({ role_fallback: cr.creatorTypeFor('bookSection', 'reviewedAuthor'), role_kept: cr.creatorTypeFor('journalArticle', 'reviewedAuthor'), date_null_parts: cr.crossrefWorkToZoteroItem(odd).date, date_created: cr.crossrefWorkToZoteroItem(created).date });
} else if (cmd === 'doi-cases') {
  const cr = await mod('scripts/zotero/_lib/crossref-item.mjs');
  const cases = [
    ['https://www.doi.org/10.1234/ABC', '10.1234/abc'], ['https://doi.org/10.1234/abc.', '10.1234/abc'], ['doi:10.1234/abc;', '10.1234/abc'],
    ['10.1234%2Fabc', '10.1234/abc'], ['10.1234/abc)', '10.1234/abc'], ['10.1234/abc(1)', '10.1234/abc(1)'], ['10.1234/abc(1),', '10.1234/abc(1)'],
  ];
  out(cases.map(([raw, want]) => [raw, { got: cr.normaliseDoi(raw), want }]));
} else if (cmd === 'persist-fail') {
  // add_item whose queue save throws right after the create succeeds.
  const q = await mod('scripts/zotero/approval-queue.mjs');
  const queue = q.loadQueue(arg);
  const ctx = { ...(await q.createContext()), retry: false, persist: () => { throw new Error('disk full'); } };
  let thrown = null;
  try { await q.EXECUTORS.add_item(queue.actions[0], ctx); } catch (e) { thrown = e.message; }
  out({ thrown });
} else if (cmd === 'lock-steal') {
  // The lock file is replaced by another process's lock while we hold ours; release must not remove it.
  const q = await mod('scripts/zotero/approval-queue.mjs');
  const release = q.acquireLock(arg);
  fs.writeFileSync(`${arg}.lock`, JSON.stringify({ pid: 1, at: new Date().toISOString() }));
  release();
  const still = fs.existsSync(`${arg}.lock`);
  out({ still_there: still, body_pid: still ? JSON.parse(fs.readFileSync(`${arg}.lock`, 'utf8')).pid : null });
} else if (cmd === 'save-fail') {
  const q = await mod('scripts/zotero/approval-queue.mjs');
  const dir = path.dirname(arg);
  const io = { ...fs, renameSync() { throw new Error('simulated rename failure'); } };
  let thrown = null;
  try { q.saveQueue(arg, { date: 'x', actions: [{ id: 99, type: 'add_tag', status: 'applied' }] }, io); } catch (e) { thrown = e.message; }
  out({ thrown, content: fs.readFileSync(arg, 'utf8'), leftovers: fs.readdirSync(dir).filter((f) => f.endsWith('.tmp')) });
}
