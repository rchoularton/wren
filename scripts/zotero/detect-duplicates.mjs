#!/usr/bin/env node
/**
 * detect-duplicates.mjs - find likely duplicate items in the Zotero library. READ-ONLY.
 *
 * Groups top-level items by:
 *   1. exact DOI (normalised: lower-case, "https://doi.org/" and "doi:" prefixes stripped)
 *   2. fuzzy title (Jaro-Winkler >= 0.92) among items not already grouped by DOI
 *
 * Never writes to Zotero: the only requests it makes are GETs through the client.
 * The report goes to stdout, or to a file with --out.
 *
 * Usage:
 *   node scripts/zotero/detect-duplicates.mjs
 *   node scripts/zotero/detect-duplicates.mjs --out outputs/librarian/duplicates.json
 *   node scripts/zotero/detect-duplicates.mjs --limit 500
 *
 * Exit codes: 0 success (duplicates found or not), 1 bad arguments or Zotero API error.
 */
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { createClientFromEnv } from './_lib/zotero-client.mjs';
import { normaliseDoi } from './_lib/crossref-item.mjs';

export const TITLE_THRESHOLD = 0.92;
const MIN_TITLE_LENGTH = 15;

export function normaliseTitle(s) {
  if (!s) return '';
  return String(s).toLowerCase()
    .replace(/[‐-―-]/g, ' ') // dash variants -> space
    .replace(/[^\w\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

export function jaro(a, b) {
  if (!a || !b) return 0;
  if (a === b) return 1;
  const window = Math.max(0, Math.floor(Math.max(a.length, b.length) / 2) - 1);
  const am = new Array(a.length).fill(false);
  const bm = new Array(b.length).fill(false);
  let matches = 0;
  for (let i = 0; i < a.length; i++) {
    for (let j = Math.max(0, i - window); j < Math.min(b.length, i + window + 1); j++) {
      if (bm[j] || a[i] !== b[j]) continue;
      am[i] = bm[j] = true;
      matches++;
      break;
    }
  }
  if (!matches) return 0;
  let transpositions = 0;
  let k = 0;
  for (let i = 0; i < a.length; i++) {
    if (!am[i]) continue;
    while (!bm[k]) k++;
    if (a[i] !== b[k]) transpositions++;
    k++;
  }
  return (matches / a.length + matches / b.length + (matches - transpositions / 2) / matches) / 3;
}

export function jaroWinkler(a, b, prefixScale = 0.1) {
  const j = jaro(a, b);
  if (j < 0.7) return j;
  let prefix = 0;
  for (let i = 0; i < Math.min(4, a.length, b.length); i++) {
    if (a[i] === b[i]) prefix++; else break;
  }
  return j + prefix * prefixScale * (1 - j);
}

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

export function detectDuplicates(items) {
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

  const titled = items
    .filter((it) => !doiGrouped.has(keyOf(it)))
    .map((item) => ({ item, key: keyOf(item), norm: normaliseTitle(item.data?.title) }))
    .filter((t) => t.norm.length >= MIN_TITLE_LENGTH)
    .sort((a, b) => a.norm.localeCompare(b.norm));

  const taken = new Set();
  for (let i = 0; i < titled.length; i++) {
    if (taken.has(titled[i].key)) continue;
    const cluster = [{ ...titled[i], similarity: 1.0 }];
    for (let j = i + 1; j < titled.length; j++) {
      if (taken.has(titled[j].key)) continue;
      if (Math.abs(titled[i].norm.length - titled[j].norm.length) > 20) continue;
      const sim = jaroWinkler(titled[i].norm, titled[j].norm);
      if (sim >= TITLE_THRESHOLD) {
        cluster.push({ ...titled[j], similarity: sim });
        taken.add(titled[j].key);
      }
    }
    if (cluster.length > 1) {
      taken.add(titled[i].key);
      clusters.push({
        method: 'title-fuzzy',
        similarity: Math.min(...cluster.map((c) => c.similarity)),
        items: cluster.map((c) => summarise(c.item)),
      });
    }
  }
  return clusters;
}

function parseArgs(argv) {
  const a = { out: null, limit: Infinity };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--out') a.out = argv[++i];
    else if (argv[i] === '--limit') {
      const n = Number(argv[++i]);
      if (!Number.isInteger(n) || n < 1) throw new Error('--limit needs a positive integer');
      a.limit = n;
    } else throw new Error(`Unknown argument ${argv[i]}. Usage: detect-duplicates.mjs [--out FILE] [--limit N]`);
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
  const clusters = detectDuplicates(items);
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
