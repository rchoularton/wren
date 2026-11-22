#!/usr/bin/env node
/**
 * detect-duplicates.mjs - find likely duplicate items in the Zotero library. READ-ONLY.
 *
 * Groups top-level items by:
 *   1. exact DOI (normalised: lower-case, "https://doi.org/" and "doi:" prefixes stripped)
 *   2. fuzzy title (Jaro-Winkler >= 0.92) among items not already grouped by DOI. To stay fast
 *      on large libraries only candidate pairs are compared: pairs sharing two title tokens
 *      (length >= 4, minus stopwords) or one token of length >= 8 with normalised lengths within
 *      20 percent, or pairs whose normalised titles share their first 12 characters. This trades
 *      some recall for speed. Progress goes to stderr every 1,000 titles. --no-fuzzy skips this
 *      pass (DOI grouping only).
 *
 * Never writes to Zotero: the only requests it makes are GETs through the client.
 * The report goes to stdout, or to a file with --out.
 *
 * Usage:
 *   node scripts/zotero/detect-duplicates.mjs
 *   node scripts/zotero/detect-duplicates.mjs --out outputs/librarian/duplicates.json
 *   node scripts/zotero/detect-duplicates.mjs --limit 500 [--no-fuzzy]
 *   node scripts/zotero/detect-duplicates.mjs --out report.json --proposals dups.proposals.json
 *
 * --proposals FILE also writes one merge_duplicate proposal per group in the librarian proposals
 * shape ({agent, generated, actions}) for scripts/zotero/build-queue.mjs. The keeper is the item
 * with the most non-empty metadata fields; ties go to the earliest dateAdded, then the lowest key.
 * Groups are split by itemType (never a cross-type merge); leftovers go to `mixed_type` in the JSON
 * report. No file is written when there are no same-type groups. Still read-only on the library.
 *
 * Exit codes: 0 success (duplicates found or not), 1 bad arguments or Zotero API error.
 */
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { checkOutputPath } from './_lib/unattended.mjs';
import { createClientFromEnv, projectRoot } from './_lib/zotero-client.mjs';
import { normaliseDoi } from './_lib/crossref-item.mjs';
import { TITLE_THRESHOLD, normaliseTitle, jaroWinkler } from './_lib/dup-match.mjs';

const MIN_TITLE_LENGTH = 15;

function summarise(item) {
  const d = item.data || {};
  return {
    key: item.key || d.key,
    title: d.title || 'Untitled',
    doi: d.DOI || null,
    date: d.date || null,
    itemType: d.itemType || null,
    creators: (d.creators || []).slice(0, 3).map((c) => c.name || `${c.firstName || ''} ${c.lastName || ''}`.trim()),
    tags: (d.tags || []).map((t) => t.tag),
    collections: d.collections || [],
    dateAdded: d.dateAdded || null,
  };
}

const STOPWORDS = new Set(['the', 'and', 'for', 'with', 'from', 'that', 'this', 'into', 'over', 'under', 'their', 'between', 'about', 'using', 'based', 'study', 'analysis']);

function blockTokens(norm) {
  return [...new Set(norm.split(' ').filter((t) => t.length >= 4 && !STOPWORDS.has(t)))];
}

export function detectDuplicates(items, { fuzzy = true, progress = null } = {}) {
  const clusters = [];
  const keyOf = (it) => it.key || it.data?.key;

  const byDoi = new Map();
  for (const item of items) {
    const doi = normaliseDoi(item.data?.DOI);
    if (!doi) continue;
    if (!byDoi.has(doi)) byDoi.set(doi, []);
    byDoi.get(doi).push(item);
  }
  const doiGrouped = new Set();
  for (const [doi, group] of byDoi) {
    if (group.length < 2) continue;
    clusters.push({ method: 'doi', doi, similarity: 1.0, items: group.map(summarise) });
    for (const g of group) doiGrouped.add(keyOf(g));
  }
  if (!fuzzy) return clusters;

  const titled = items
    .filter((it) => !doiGrouped.has(keyOf(it)))
    .map((item) => ({ item, key: keyOf(item), norm: normaliseTitle(item.data?.title) }))
    .filter((t) => t.norm.length >= MIN_TITLE_LENGTH);
  titled.forEach((t) => { t.tokens = blockTokens(t.norm); });

  // Blocking: a pair is compared only if it meets one of three rules (all still need
  // Jaro-Winkler >= 0.92 to count). An inverted index finds candidates without an O(n^2) scan.
  //   1. shares at least two title tokens (length >= 4, minus stopwords), lengths within 20 percent
  //   2. shares one token of length >= 8, lengths within 20 percent (catches a one-word typo)
  //   3. normalised titles start with the same 12 characters (catches a title plus a subtitle)
  const index = new Map();
  const prefixes = new Map();
  titled.forEach((t, i) => {
    for (const tok of t.tokens) { if (!index.has(tok)) index.set(tok, []); index.get(tok).push(i); }
    const pre = t.norm.slice(0, 12);
    if (!prefixes.has(pre)) prefixes.set(pre, []);
    prefixes.get(pre).push(i);
  });

  const taken = new Set();
  for (let i = 0; i < titled.length; i++) {
    if (progress && i > 0 && i % 1000 === 0) progress(i, titled.length);
    if (taken.has(titled[i].key)) continue;
    const la = titled[i].norm.length;
    const lenOk = (j) => Math.abs(la - titled[j].norm.length) <= 0.2 * Math.max(la, titled[j].norm.length);
    const shared = new Map();
    const longShared = new Set();
    for (const tok of titled[i].tokens) {
      for (const j of index.get(tok)) {
        if (j <= i) continue;
        shared.set(j, (shared.get(j) || 0) + 1);
        if (tok.length >= 8) longShared.add(j);
      }
    }
    const cand = new Set();
    for (const [j, n] of shared) if (lenOk(j) && (n >= 2 || longShared.has(j))) cand.add(j);
    for (const j of prefixes.get(titled[i].norm.slice(0, 12))) if (j > i) cand.add(j);
    const candidates = [...cand].sort((x, y) => x - y);
    const cluster = [{ ...titled[i], similarity: 1.0 }];
    for (const j of candidates) {
      if (taken.has(titled[j].key)) continue;
      const sim = jaroWinkler(titled[i].norm, titled[j].norm);
      if (sim >= TITLE_THRESHOLD) {
        cluster.push({ ...titled[j], similarity: sim });
        taken.add(titled[j].key);
      }
    }
    if (cluster.length > 1) {
      taken.add(titled[i].key);
      clusters.push({ method: 'title-fuzzy', similarity: Math.min(...cluster.map((c) => c.similarity)), items: cluster.map((c) => summarise(c.item)) });
    }
  }
  return clusters;
}

const BOOKKEEPING = new Set(['key', 'version', 'dateAdded', 'dateModified', 'relations']);

/** Number of non-empty metadata fields on a Zotero item's data (bookkeeping fields excluded). */
export function metadataScore(item) {
  const d = item.data || {};
  let n = 0;
  for (const [k, v] of Object.entries(d)) {
    if (BOOKKEEPING.has(k) || v === null || v === undefined) continue;
    if (typeof v === 'string' && v.trim() === '') continue;
    if (Array.isArray(v) && v.length === 0) continue;
    if (typeof v === 'object' && !Array.isArray(v) && Object.keys(v).length === 0) continue;
    n++;
  }
  return n;
}

/** Deterministic keeper: most non-empty fields, then earliest dateAdded, then lowest key. */
export function chooseKeeper(members) {
  const ts = (m) => { const t = Date.parse(m.data?.dateAdded); return Number.isFinite(t) ? t : Infinity; };
  const rank = (m) => ({ score: metadataScore(m), added: ts(m), key: m.key || m.data?.key || '' });
  return [...members].sort((x, y) => {
    const a = rank(x); const b = rank(y);
    if (a.score !== b.score) return b.score - a.score;
    if (a.added !== b.added) return a.added < b.added ? -1 : 1;
    return a.key < b.key ? -1 : a.key > b.key ? 1 : 0;
  })[0];
}

/**
 * Never merge across item types: split each cluster by itemType. Same-type subgroups of two or more
 * become proposals; everything else in a cluster that spans types is reported as mixed_type.
 */
export function splitByType(clusters) {
  const groups = [];
  const mixed = [];
  for (const c of clusters) {
    const byType = new Map();
    for (const it of c.items) {
      const t = it.itemType || '';
      if (!byType.has(t)) byType.set(t, []);
      byType.get(t).push(it);
    }
    const left = [];
    for (const members of byType.values()) {
      if (members.length >= 2) groups.push({ ...c, items: members });
      else left.push(...members);
    }
    if (byType.size > 1 && left.length) mixed.push({ method: c.method, doi: c.doi ?? null, similarity: c.similarity, items: left });
  }
  return { groups, mixed };
}

/** One merge_duplicate proposal per same-type group. `items` are the raw Zotero items the clusters came from. */
export function duplicateProposals(clusters, items, generated) {
  const byKey = new Map(items.map((it) => [it.key || it.data?.key, it]));
  const actions = splitByType(clusters).groups.map((c) => {
    const members = c.items.map((s) => byKey.get(s.key)).filter(Boolean);
    const keeper = chooseKeeper(members);
    const keepKey = keeper.key || keeper.data?.key;
    const mergeKeys = c.items.map((s) => s.key).filter((k) => k !== keepKey).sort();
    const basis = c.method === 'doi' ? `equal DOI ${c.doi}` : `title match (similarity ${c.similarity.toFixed(2)})`;
    return {
      type: 'merge_duplicate',
      title: `Merge ${members.length} duplicates (${basis}): ${keeper.data?.title || 'Untitled'}`.slice(0, 200),
      details: { keep: keepKey, merge_keys: mergeKeys, basis },
    };
  });
  return { agent: 'duplicate-scan', generated, actions };
}

function parseArgs(argv) {
  const a = { out: null, proposals: null, limit: Infinity, fuzzy: true };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--out') a.out = argv[++i];
    else if (argv[i] === '--proposals') a.proposals = argv[++i];
    else if (argv[i] === '--no-fuzzy') a.fuzzy = false;
    else if (argv[i] === '--limit') {
      const n = Number(argv[++i]);
      if (!Number.isInteger(n) || n < 1) throw new Error('--limit needs a positive integer');
      a.limit = n;
    } else throw new Error(`Unknown argument ${argv[i]}. Usage: detect-duplicates.mjs [--out FILE] [--proposals FILE] [--limit N] [--no-fuzzy]`);
  }
  if (a.out === undefined || a.out === '') throw new Error('--out needs a file path');
  if (a.proposals === undefined || a.proposals === '') throw new Error('--proposals needs a file path');
  return a;
}

export async function main(argv) {
  const args = parseArgs(argv);
  const root = projectRoot();
  if (args.out) checkOutputPath(args.out, root, '--out');
  if (args.proposals) checkOutputPath(args.proposals, root, '--proposals');
  const client = await createClientFromEnv();
  console.error('Fetching Zotero library items (read-only)...');
  const all = await client.listTopItems(null, { limit: args.limit });
  const items = all.filter((it) => !['attachment', 'note'].includes(it.data?.itemType));
  console.error(`Scanning ${items.length} items for duplicates...`);
  const clusters = detectDuplicates(items, { fuzzy: args.fuzzy, progress: (i, n) => console.error(`  fuzzy pass: ${i}/${n} titles`) });
  const report = {
    date: new Date().toISOString().split('T')[0],
    items_scanned: items.length,
    duplicate_clusters: clusters.length,
    total_duplicate_items: clusters.reduce((n, c) => n + c.items.length, 0),
    mixed_type: splitByType(clusters).mixed,
    clusters,
  };
  const json = JSON.stringify(report, null, 2);
  if (args.out) {
    fs.mkdirSync(path.dirname(path.resolve(args.out)), { recursive: true });
    fs.writeFileSync(args.out, json + '\n', 'utf8');
    console.error(`Report written to ${args.out}`);
  } else {
    process.stdout.write(json + '\n');
  }
  const doc = args.proposals ? duplicateProposals(clusters, items, report.date) : null;
  if (doc && doc.actions.length > 0) {
    fs.mkdirSync(path.dirname(path.resolve(args.proposals)), { recursive: true });
    fs.writeFileSync(args.proposals, JSON.stringify(doc, null, 2) + '\n', 'utf8');
    console.error(`Proposals written to ${args.proposals} (${doc.actions.length} merge_duplicate actions)`);
  } else if (args.proposals) {
    console.error('No same-type duplicate groups: no proposals file written');
  }
  console.error(`\nDuplicate scan complete: ${clusters.length} clusters (${report.total_duplicate_items} items involved)`);
}

const isMain = process.argv[1] && import.meta.url === pathToFileURL(fs.realpathSync(process.argv[1])).href;
if (isMain) {
  main(process.argv.slice(2)).catch((err) => {
    console.error(`Fatal: ${err.message}`);
    process.exit(1);
  });
}
