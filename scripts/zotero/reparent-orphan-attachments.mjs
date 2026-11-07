#!/usr/bin/env node
/**
 * Give parentless Zotero attachments a parent item. Dry run unless --apply.
 *
 * Plan file: a JSON array of entries, each one of:
 *   create:  { attachmentKey, item: { itemType, title, creators?, date?, ... }, attachmentTitle? }
 *   attach:  { attachmentKey, existingParentKey, attachmentTitle? }
 *   trash:   { attachmentKey, action: "trash", reason }
 * Optional per-entry libraryType / libraryId (default: ZOTERO_LIBRARY_TYPE / ZOTERO_LIBRARY_ID).
 *
 * For each entry: read the attachment (must be parentless, not trashed); resolve or create the
 * parent; PATCH the attachment; then re-read it and check the change landed (a 204 is not proof).
 * Applied results are appended to the JSONL log; an attachmentKey already logged as ok is skipped.
 *
 * Usage:
 *   node scripts/zotero/reparent-orphan-attachments.mjs <plan.json> [--apply] [--only K1,K2] [--log file.jsonl]
 * Default log: outputs/pdf-fill/reparent.jsonl. Exit: 0 all ok, 1 bad args, 2 any entry failed.
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { createClientFromEnv, projectRoot } from './_lib/zotero-client.mjs';

const argv = process.argv.slice(2);
const flagVal = (f) => (argv.includes(f) ? argv[argv.indexOf(f) + 1] : null);
const planPath = argv.find((a, i) => !a.startsWith('--') && !['--only', '--log'].includes(argv[i - 1]));
const apply = argv.includes('--apply');
if (argv.includes('--only') && (!flagVal('--only') || flagVal('--only').startsWith('--'))) {
  console.error('--only needs a comma-separated list of attachment keys');
  process.exit(1);
}
const only = flagVal('--only') ? new Set(flagVal('--only').split(',')) : null;
if (!planPath) {
  console.error('Usage: reparent-orphan-attachments.mjs <plan.json> [--apply] [--only K1,K2] [--log file.jsonl]');
  process.exit(1);
}
const root = projectRoot();
const logPath = flagVal('--log') || path.join(root, 'outputs', 'pdf-fill', 'reparent.jsonl');

const client = await createClientFromEnv();
const pace = process.env.WREN_FAKE_FETCH ? 0 : 300;
const sleep = (ms) => (ms ? new Promise((r) => setTimeout(r, ms)) : null);
const plan = JSON.parse(fs.readFileSync(planPath, 'utf8'));

const done = new Set();
const createdParents = new Map(); // attachmentKey -> parent created by an earlier run whose PATCH failed
if (fs.existsSync(logPath)) {
  for (const line of fs.readFileSync(logPath, 'utf8').split('\n').filter(Boolean)) {
    try {
      const r = JSON.parse(line);
      if (r.ok && r.apply) done.add(r.attachmentKey);
      else if (r.createdParentKey && r.stage === 'patch') createdParents.set(r.attachmentKey, r.createdParentKey);
    } catch { /* ignore bad line */ }
  }
}

const lib = (e) => ({ type: e.libraryType, id: e.libraryId });
const templates = {};
async function template(e) {
  const t = e.item.itemType;
  if (!templates[t]) templates[t] = await client.getJson(`/items/new?itemType=${encodeURIComponent(t)}`, { library: lib(e) });
  return templates[t];
}

async function buildItem(e, att) {
  const tpl = await template(e);
  const out = { ...tpl };
  const dropped = [];
  for (const [k, v] of Object.entries(e.item)) (k in tpl ? (out[k] = v) : dropped.push(k));
  out.creators ??= [];
  out.collections = e.item.collections ?? att.data.collections ?? [];
  out.tags = e.item.tags ?? att.data.tags ?? [];
  return { item: out, dropped };
}

const results = [];
for (const e of plan) {
  if (only && !only.has(e.attachmentKey)) continue;
  if (done.has(e.attachmentKey)) { console.log(`skip ${e.attachmentKey}: already applied (in log)`); continue; }
  const rec = { attachmentKey: e.attachmentKey, at: new Date().toISOString(), apply };
  const L = lib(e);
  const get = (key) => client.getItem(key, { library: L });
  try {
    const att = await get(e.attachmentKey);
    if (att.data.parentItem) throw new Error(`already has parent ${att.data.parentItem}`);
    if (att.data.deleted) throw new Error('attachment is in the trash');
    const patch = (body) => client.request(`/items/${e.attachmentKey}`, { method: 'PATCH', body, version: att.version, library: L });

    if (e.action === 'trash') {
      rec.action = 'trash'; rec.reason = e.reason;
      console.log(`${apply ? 'APPLY' : 'DRY'} ${e.attachmentKey} [${att.data.title}] -> TRASH (${e.reason || 'no reason given'})`);
      if (apply) {
        await patch({ deleted: 1 });
        await sleep(pace);
        const after = await get(e.attachmentKey);
        if (!(after.data.deleted === 1 || after.data.deleted === true)) throw new Error('verify failed: attachment not marked deleted');
      }
    } else {
      let parentKey;
      const parentHint = e.existingParentKey || createdParents.get(e.attachmentKey);
      if (parentHint) {
        rec.action = 'attach-existing';
        if (!e.existingParentKey) console.log(`  note ${e.attachmentKey}: reusing parent ${parentHint} created by an earlier run`);
        const p = await get(parentHint);
        if (p.data.deleted || ['attachment', 'note'].includes(p.data.itemType)) throw new Error(`existing parent ${parentHint} unusable (type ${p.data.itemType}, deleted ${p.data.deleted})`);
        console.log(`${apply ? 'APPLY' : 'DRY'} ${e.attachmentKey} [${att.data.title}] -> existing ${p.data.itemType} ${parentHint}: "${p.data.title}"`);
        parentKey = parentHint;
      } else {
        rec.action = 'create';
        const { item, dropped } = await buildItem(e, att);
        if (dropped.length) { rec.droppedFields = dropped; console.log(`  warn ${e.attachmentKey}: fields not in ${item.itemType} template dropped: ${dropped.join(', ')}`); }
        console.log(`${apply ? 'APPLY' : 'DRY'} ${e.attachmentKey} [${att.data.title}] -> new ${item.itemType}: "${item.title}"`);
        if (apply) {
          const post = await client.request('/items', { method: 'POST', body: [item], library: L, headers: { 'Zotero-Write-Token': crypto.randomBytes(16).toString('hex') } });
          parentKey = post.data?.successful?.['0']?.key;
          if (!parentKey) throw new Error(`create failed: ${JSON.stringify(post.data?.failed)}`);
          await sleep(pace);
          // Record the new parent BEFORE the PATCH so a failed PATCH never leaves it orphaned on rerun.
          fs.mkdirSync(path.dirname(logPath), { recursive: true });
          fs.appendFileSync(logPath, JSON.stringify({ attachmentKey: e.attachmentKey, createdParentKey: parentKey, ok: false, stage: 'patch', apply: true, at: new Date().toISOString() }) + '\n');
        }
      }
      if (apply) {
        rec.parentKey = parentKey;
        await patch({ parentItem: parentKey, collections: [], ...(e.attachmentTitle ? { title: e.attachmentTitle } : {}) });
        await sleep(pace);
        const after = await get(e.attachmentKey);
        rec.verifiedParent = after.data.parentItem;
        if (after.data.parentItem !== parentKey) throw new Error(`verify failed: attachment parentItem is ${after.data.parentItem}`);
        console.log(`  OK parent=${parentKey} (re-read confirms)`);
      }
    }
    rec.ok = true;
    if (!apply) rec.dryRun = true;
  } catch (err) {
    rec.ok = false;
    rec.error = err.message;
    console.log(`! ${e.attachmentKey}: ${err.message}`);
  }
  results.push(rec);
  if (apply) {
    fs.mkdirSync(path.dirname(logPath), { recursive: true });
    fs.appendFileSync(logPath, JSON.stringify(rec) + '\n');
  }
  await sleep(pace);
}
const okN = results.filter((r) => r.ok).length;
console.log(`\n${apply ? 'applied' : 'dry run'}: ${okN}/${results.length} ok`);
process.exit(okN === results.length ? 0 : 2);
