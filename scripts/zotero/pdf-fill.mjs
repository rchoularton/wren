#!/usr/bin/env node
/**
 * pdf-fill.mjs - attach missing PDFs to the items of a paper's Zotero collection.
 *
 * Usage:
 *   node scripts/zotero/pdf-fill.mjs <paper-id> [--dry-run | --apply] [--keys K1,K2] [--only unpaywall|openalex|sniff]
 *   node scripts/zotero/pdf-fill.mjs --collection KEY [...]
 *
 * Collection key: `zotero_collection` in papers/<id>/config.json, or --collection KEY.
 * Default is a dry run (reads Zotero and the sources, writes nothing). --apply uploads,
 * then verifies each attachment by re-reading the item's children (a 204 is not proof).
 * Sources run in order: Unpaywall, OpenAlex, publisher sniff. Items still without a PDF are
 * listed as DOI links (prefixed with INSTITUTION_PROXY_PREFIX when set) in
 * outputs/pdf-fill/<paper>-manual.md for you to open yourself. No browser automation.
 *
 * Exit codes: 0 done, 1 bad arguments, 2 Zotero/config failure.
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createClientFromEnv, hasPdfAttachment, hasPdfStub, loadFetch, projectRoot } from './_lib/zotero-client.mjs';
import * as unpaywall from './sources/unpaywall.mjs';
import * as openalex from './sources/openalex.mjs';
import * as sniff from './sources/publisher-sniff.mjs';

const SOURCES = [unpaywall, openalex, sniff];
const ONLY = { unpaywall: unpaywall.NAME, openalex: openalex.NAME, sniff: sniff.NAME };

const STUB_NOTE = 'attachment shell without a file; delete it in Zotero or fix manually';

function usage(msg) {
  if (msg) console.error(msg);
  console.error('Usage: pdf-fill.mjs <paper-id> | --collection KEY  [--dry-run | --apply] [--keys K1,K2] [--only unpaywall|openalex|sniff]');
  process.exit(1);
}

export function parseArgs(argv) {
  const a = { paper: null, collection: null, keys: null, only: null, apply: false, dryRun: false };
  for (let i = 0; i < argv.length; i++) {
    const t = argv[i];
    if (t === '--apply') a.apply = true;
    else if (t === '--dry-run') a.dryRun = true;
    else if (t === '--collection') a.collection = argv[++i];
    else if (t === '--keys') a.keys = (argv[++i] || '').split(',').map((s) => s.trim()).filter(Boolean);
    else if (t === '--only') a.only = argv[++i];
    else if (t.startsWith('--')) usage(`Unknown flag ${t}`);
    else if (!a.paper) a.paper = t;
    else usage(`Unexpected argument ${t}`);
  }
  if (a.apply && a.dryRun) usage('--apply and --dry-run are mutually exclusive');
  if (a.only && !ONLY[a.only]) usage(`--only must be one of: ${Object.keys(ONLY).join(', ')}`);
  if (!a.paper && !a.collection && !a.keys) usage('Give a paper id, --collection KEY, or --keys K1,K2');
  return a;
}

function collectionKeyFor(args, root) {
  if (args.collection) return args.collection;
  const cfgPath = path.join(root, 'papers', args.paper, 'config.json');
  if (!fs.existsSync(cfgPath)) throw new Error(`No ${cfgPath}. Check the paper id.`);
  const key = (JSON.parse(fs.readFileSync(cfgPath, 'utf8')).zotero_collection || '').trim();
  if (!key) throw new Error(`papers/${args.paper}/config.json has an empty "zotero_collection". Set the 8-character collection key (the URL of the collection in Zotero web ends /collections/<KEY>) or pass --collection KEY.`);
  return key;
}

function summarise(item) {
  const d = item.data || {};
  return {
    key: item.key,
    title: d.title || '(no title)',
    doi: (d.DOI || '').trim().replace(/^https?:\/\/(dx\.)?doi\.org\//i, '') || null,
    url: d.url || null,
    firstAuthor: (d.creators || []).find((c) => c.lastName)?.lastName || '',
    year: (d.date || '').match(/\d{4}/)?.[0] || '',
  };
}

function filenameFor(it) {
  const t = it.title.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 60);
  return `${it.firstAuthor || 'unknown'}_${it.year || 'nd'}_${t}.pdf`;
}

function manualMarkdown(label, rows, prefix) {
  const lines = [`# PDFs to fetch manually: ${label}`, '', prefix
    ? `Links use your INSTITUTION_PROXY_PREFIX. Open each yourself, download the PDF, and attach it in Zotero.`
    : `No INSTITUTION_PROXY_PREFIX set, so these are plain DOI links. Open each yourself, download the PDF, and attach it in Zotero.`, ''];
  for (const r of rows) {
    const target = r.doi ? `https://doi.org/${r.doi}` : r.url;
    const link = target ? prefix + target : '(no DOI or URL)';
    lines.push(`- \`${r.key}\` ${r.firstAuthor} ${r.year}: ${r.title} - ${link}${r.note ? ` (${r.note})` : ''}`);
  }
  return lines.join('\n') + '\n';
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const root = projectRoot();
  const apply = args.apply;
  const client = await createClientFromEnv();
  const env = client.env;
  const ctx = { fetch: await loadFetch(env), env }; // sources share the client's fetch

  const sources = SOURCES.filter((s) => !args.only || s.NAME === ONLY[args.only]);
  const label = args.keys ? `keys (${args.keys.length})` : null;
  let collection = null;
  if (!args.keys) collection = collectionKeyFor(args, root);
  const slug = args.paper || (collection ? `collection-${collection}` : 'keys');
  console.log(`pdf-fill ${args.paper || ''} ${collection ? 'collection ' + collection : label} [${apply ? 'APPLY' : 'DRY RUN'}]`);

  const raw = args.keys ? await client.listItemsByKeys(args.keys) : await client.listTopItems(collection);
  const items = raw.filter((it) => !['attachment', 'note'].includes(it.data?.itemType)).map(summarise);
  console.log(`  ${items.length} bibliographic items`);

  const counts = { items: items.length, already_had_pdf: 0, found: 0, attached: 0, manual: 0, stub: 0, failed: 0 };
  const manual = [];
  const log = [];
  const notified = new Set();

  for (const [i, item] of items.entries()) {
    const tag = `[${i + 1}/${items.length}] ${item.key} ${item.firstAuthor} ${item.year}`;
    const rec = { at: new Date().toISOString(), key: item.key, doi: item.doi, apply };
    try {
      const children = await client.listChildren(item.key);
      if (hasPdfAttachment(children)) {
        counts.already_had_pdf++;
        continue;
      }
      if (hasPdfStub(children)) {
        console.log(`  ${tag}: PDF attachment shell without a file, not attaching a second PDF`);
        counts.stub++;
        manual.push({ ...item, note: STUB_NOTE });
        log.push({ ...rec, status: 'stub' });
        continue;
      }
    } catch (err) {
      console.warn(`  ${tag}: could not list children: ${err.message}`);
      counts.failed++;
      log.push({ ...rec, status: 'failed', error: err.message });
      continue;
    }
    if (!item.doi) {
      console.log(`  ${tag}: no DOI, manual`);
      counts.manual++; manual.push(item); log.push({ ...rec, status: 'manual', reason: 'no_doi' });
      continue;
    }

    let hit = null;
    const attempts = [];
    for (const src of sources) {
      const res = await src.lookup({ doi: item.doi }, ctx);
      if (res.skipped) {
        if (!notified.has(src.NAME)) { console.log(`  notice: ${res.reason}`); notified.add(src.NAME); }
        attempts.push({ source: src.NAME, skipped: true });
        continue;
      }
      attempts.push({ source: src.NAME, ok: res.ok, reason: res.reason || null });
      if (res.ok) { hit = res; break; }
    }
    if (!hit) {
      console.log(`  ${tag}: not found in open sources, manual`);
      counts.manual++; manual.push(item); log.push({ ...rec, status: 'manual', attempts });
      continue;
    }
    counts.found++;
    if (!apply) {
      console.log(`  ${tag}: would attach via ${hit.source} (${(hit.buffer.length / 1024).toFixed(1)} KB)`);
      log.push({ ...rec, status: 'attachable', source: hit.source });
      continue;
    }

    const tmp = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'wren-pdf-')), filenameFor(item));
    try {
      fs.writeFileSync(tmp, hit.buffer);
      const { attachmentKey, deduped } = await client.attachPdfToItem(item.key, tmp, { title: filenameFor(item) });
      // Verify by re-reading: a successful write response is not proof.
      const after = await client.listChildren(item.key);
      const verified = after.some((c) => c.key === attachmentKey && c.data?.contentType === 'application/pdf' && c.data?.md5);
      if (!verified) throw new Error(`verify failed: attachment ${attachmentKey} has no uploaded PDF on re-read`);
      console.log(`  ${tag}: attached via ${hit.source} (verified${deduped ? ', deduped' : ''})`);
      counts.attached++;
      log.push({ ...rec, status: 'attached', source: hit.source, attachmentKey, verified: true });
    } catch (err) {
      console.warn(`  ${tag}: FAILED via ${hit.source}: ${err.message}`);
      counts.failed++;
      log.push({ ...rec, status: 'failed', source: hit.source, error: err.message });
    } finally {
      fs.rmSync(path.dirname(tmp), { recursive: true, force: true });
    }
  }

  const prefix = env.INSTITUTION_PROXY_PREFIX || '';
  if (apply) {
    const dir = path.join(root, 'outputs', 'pdf-fill');
    fs.mkdirSync(dir, { recursive: true });
    const stamp = new Date().toISOString().slice(0, 10);
    const logPath = path.join(dir, `${slug}-${stamp}.jsonl`);
    fs.appendFileSync(logPath, log.map((r) => JSON.stringify(r)).join('\n') + (log.length ? '\n' : ''));
    console.log(`\nLog: ${path.relative(root, logPath)}`);
    if (manual.length) {
      const mp = path.join(dir, `${slug}-manual.md`);
      fs.writeFileSync(mp, manualMarkdown(slug, manual, prefix));
      console.log(`Manual list: ${path.relative(root, mp)}`);
    }
  } else if (manual.length) {
    console.log(`\nManual (would be written to outputs/pdf-fill/${slug}-manual.md on --apply):`);
    for (const r of manual) console.log(`  ${r.key} ${r.doi ? prefix + 'https://doi.org/' + r.doi : r.url || '(no DOI or URL)'}${r.note ? ` (${r.note})` : ''}`);
  }
  console.log(`\nfound=${counts.found} attached=${counts.attached} manual=${counts.manual} stub=${counts.stub} failed=${counts.failed} already_had_pdf=${counts.already_had_pdf}${apply ? '' : ' (dry run, nothing written)'}`);
  console.log(`SUMMARY ${JSON.stringify({ ...counts, apply })}`);
  process.exit(counts.failed ? 2 : 0);
}

main().catch((err) => {
  console.error(err.message || err);
  process.exit(2);
});
