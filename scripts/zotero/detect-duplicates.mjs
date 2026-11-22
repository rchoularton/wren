#!/usr/bin/env node
/**
 * detect-duplicates.mjs - find likely duplicate items in the Zotero library. READ-ONLY.
 *
 * Groups top-level items by:
 *   1. exact DOI (normalised: lower-case, "https://doi.org/" and "doi:" prefixes stripped)
 *   2. fuzzy title (Jaro-Winkler >= 0.92) among items not already grouped by DOI. To stay fast
 *      on large libraries, only pairs sharing at least two title tokens (length >= 4, minus a
 *      small stopword list) with normalised lengths within 20 percent are compared, so titles
 *      with fewer than two such tokens are not fuzzy-matched. Progress goes to stderr every
 *      1,000 titles. --no-fuzzy skips this pass (DOI grouping only).
 *
 * Never writes to Zotero: the only requests it makes are GETs through the client.
 * The report goes to stdout, or to a file with --out.
 *
 * Usage:
 *   node scripts/zotero/detect-duplicates.mjs
 *   node scripts/zotero/detect-duplicates.mjs --out outputs/librarian/duplicates.json
 *   node scripts/zotero/detect-duplicates.mjs --limit 500 [--no-fuzzy]
 *
 * Exit codes: 0 success (duplicates found or not), 1 bad arguments or Zotero API error.
 */
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { createClientFromEnv } from './_lib/zotero-client.mjs';
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

  // Blocking: only pairs that share at least two title tokens (length >= 4, minus a small
  // stopword list) and whose normalised lengths differ by at most 20 percent are compared.
  // An inverted index finds those pairs without the O(n^2) scan.
  const index = new Map();
  titled.forEach((t, i) => { for (const tok of t.tokens) { if (!index.has(tok)) index.set(tok, []); index.get(tok).push(i); } });

  const taken = new Set();
  for (let i = 0; i < titled.length; i++) {
    if (progress && i > 0 && i % 1000 === 0) progress(i, titled.length);
    if (taken.has(titled[i].key)) continue;
    const shared = new Map();
    for (const tok of titled[i].tokens) for (const j of index.get(tok)) if (j > i) shared.set(j, (shared.get(j) || 0) + 1);
    const candidates = [...shared].filter(([, n]) => n >= 2).map(([j]) => j).sort((x, y) => x - y);
    const cluster = [{ ...titled[i], similarity: 1.0 }];
    for (const j of candidates) {
      if (taken.has(titled[j].key)) continue;
      const la = titled[i].norm.length;
      const lb = titled[j].norm.length;
      if (Math.abs(la - lb) > 0.2 * Math.max(la, lb)) continue;
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

function parseArgs(argv) {
  const a = { out: null, limit: Infinity, fuzzy: true };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--out') a.out = argv[++i];
    else if (argv[i] === '--no-fuzzy') a.fuzzy = false;
    else if (argv[i] === '--limit') {
      const n = Number(argv[++i]);
      if (!Number.isInteger(n) || n < 1) throw new Error('--limit needs a positive integer');
      a.limit = n;
    } else throw new Error(`Unknown argument ${argv[i]}. Usage: detect-duplicates.mjs [--out FILE] [--limit N] [--no-fuzzy]`);
  }
  if (a.out === undefined || a.out === '') throw new Error('--out needs a file path');
  return a;
}

export async function main(argv) {
  const args = parseArgs(argv);
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
  console.error(`\nDuplicate scan complete: ${clusters.length} clusters (${report.total_duplicate_items} items involved)`);
}

const isMain = process.argv[1] && import.meta.url === pathToFileURL(fs.realpathSync(process.argv[1])).href;
if (isMain) {
  main(process.argv.slice(2)).catch((err) => {
    console.error(`Fatal: ${err.message}`);
    process.exit(1);
  });
}
