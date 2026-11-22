#!/usr/bin/env node
/**
 * build-queue.mjs — the deterministic step between the librarian agents and the approval queue.
 *
 *   node scripts/zotero/build-queue.mjs --date YYYY-MM-DD [--dir outputs/librarian] [--out <file>] [--force]
 *
 * Reads every `*_<date>.proposals.json` in --dir, validates each action, drops duplicates (first wins),
 * assigns ids from 1, sets every status to `pending`, records `source_agent`, and writes
 * `approval_queue_<date>.json` atomically. Rejected proposals go to `rejected_<date>.json` with reasons.
 * No network. Exit 0 on success (even with rejections), 1 on argument/file errors or no proposals.
 */
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { normaliseDoi } from './_lib/crossref-item.mjs';
import { isPlaceholder, fixPairsOf, saveQueue, zoteroField } from './approval-queue.mjs';

class UsageError extends Error {}

const KNOWN_TYPES = new Set(['add_item', 'fix_metadata', 'add_tag', 'add_to_collection', 'merge_duplicate']);
const DOI_RE = /^10\.\d{4,9}\/\S+$/;
const nonEmpty = (v) => typeof v === 'string' && v.trim() !== '' && !isPlaceholder(v);
const isDoiField = (f) => typeof f === 'string' && f.trim().toLowerCase() === 'doi';

/** Normalised DOI, or { error }. */
function checkDoi(v) {
  const n = normaliseDoi(typeof v === 'string' ? v : '');
  return DOI_RE.test(n) ? n : { error: `invalid DOI "${v}"` };
}

function checkAuthors(a) {
  if (!Array.isArray(a)) return 'details.authors must be an array of strings or {given, family} objects';
  const ok = a.every((x) => (typeof x === 'string' && nonEmpty(x))
    || (x && typeof x === 'object' && !Array.isArray(x) && (nonEmpty(x.family) || nonEmpty(x.name))));
  return ok ? null : 'details.authors has an entry that is not a real name string or {given, family} object';
}

/** Loser keys of a merge_duplicate, from merge_keys / merge / remove (strings or arrays). */
function loserKeys(d) {
  const out = [];
  for (const v of [d.merge_keys, d.merge, d.remove]) {
    for (const k of Array.isArray(v) ? v : [v]) if (typeof k === 'string' && k.trim()) out.push(k.trim());
  }
  return [...new Set(out)];
}

/** Returns { action } with a cleaned copy, or { reason }. */
export function validateAction(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return { reason: 'action is not an object' };
  const { type } = raw;
  if (!KNOWN_TYPES.has(type)) return { reason: `unknown or unsupported type "${type}"` };
  if (!nonEmpty(raw.title)) return { reason: 'missing or placeholder title' };
  const d = raw.details;
  if (!d || typeof d !== 'object' || Array.isArray(d)) return { reason: 'missing details object' };
  let details = { ...d };

  if (type === 'add_item') {
    const rawDoi = d.doi ?? d.DOI;
    const hasTitle = nonEmpty(d.title);
    const hasDoiValue = rawDoi !== undefined && rawDoi !== null && String(rawDoi).trim() !== '';
    if (!hasDoiValue && !hasTitle) return { reason: 'add_item needs a title or a DOI' };
    if (d.title !== undefined && !hasTitle) return { reason: 'placeholder value in details.title' };
    delete details.DOI;
    delete details.doi;
    if (hasDoiValue) {
      const n = checkDoi(rawDoi);
      if (n.error) return { reason: n.error };
      details.doi = n;
    }
    if (d.authors !== undefined) {
      const why = checkAuthors(d.authors);
      if (why) return { reason: why };
    }
    for (const k of ['venue', 'date', 'abstract', 'url']) {
      if (details[k] !== undefined && isPlaceholder(details[k])) return { reason: `placeholder value in details.${k}` };
    }
    if (details.relevance !== undefined && !['high', 'medium', 'low'].includes(details.relevance)) {
      return { reason: 'details.relevance must be high, medium or low' };
    }
  } else if (type === 'fix_metadata') {
    if (!nonEmpty(d.item_key)) return { reason: 'fix_metadata needs details.item_key' };
    const pairs = fixPairsOf(d);
    if (!pairs.length) return { reason: 'fix_metadata needs at least one change' };
    const bad = pairs.filter(([, v]) => isPlaceholder(v)).map(([f]) => f);
    if (bad.length) return { reason: `placeholder value for: ${bad.join(', ')}` };
    const changes = {};
    for (const [f, v] of pairs) {
      if (isDoiField(f)) {
        const n = checkDoi(v);
        if (n.error) return { reason: n.error };
        changes[f] = n;
      } else changes[f] = v;
    }
    // Canonical shape: proposed_changes only.
    const { field_fixes, field, proposed, proposed_value, ...rest } = details;
    details = { ...rest, proposed_changes: changes };
  } else if (type === 'add_tag') {
    if (!nonEmpty(d.item_key)) return { reason: 'add_tag needs details.item_key' };
    if (!Array.isArray(d.tags) || !d.tags.length || !d.tags.every(nonEmpty)) return { reason: 'add_tag needs details.tags: a non-empty array of real strings' };
    const seenTags = new Set();
    details.tags = d.tags.map((t) => t.trim()).filter((t) => (seenTags.has(t.toLowerCase()) ? false : (seenTags.add(t.toLowerCase()), true)));
  } else if (type === 'add_to_collection') {
    if (!nonEmpty(d.item_key)) return { reason: 'add_to_collection needs details.item_key' };
    if (!nonEmpty(d.collection_key)) return { reason: 'add_to_collection needs details.collection_key' };
  } else if (type === 'merge_duplicate') {
    const keep = typeof d.keep === 'string' ? d.keep.trim() : '';
    if (!nonEmpty(keep)) return { reason: 'merge_duplicate needs details.keep' };
    const losers = loserKeys(d);
    if (!losers.length) return { reason: 'merge_duplicate needs at least one item to merge away (merge_keys, merge or remove)' };
    if (losers.includes(keep)) return { reason: 'merge_duplicate keeper is among the items to merge away' };
    if (!losers.every(nonEmpty)) return { reason: 'placeholder value in merge keys' };
    const { merge, remove, ...rest } = details;
    details = { ...rest, keep, merge_keys: losers };
  }

  const action = { type, title: raw.title.trim() };
  if (raw.paper !== undefined) {
    if (!nonEmpty(raw.paper)) return { reason: 'placeholder value in paper' };
    action.paper = raw.paper;
  }
  action.details = details;
  return { action };
}

/**
 * Remove from `action` whatever an earlier action already proposed. `seen` is a Set of keys, updated
 * for what is kept. Returns the (possibly narrowed) action, or null when nothing is left.
 */
export function dedupeAction(action, seen) {
  const d = action.details;
  const take = (k) => (seen.has(k) ? false : (seen.add(k), true));
  if (action.type === 'add_item') {
    const key = d.doi ? `add_item|${d.doi}` : `add_item|title|${String(d.title).toLowerCase().replace(/\s+/g, ' ').trim()}`;
    return take(key) ? action : null;
  }
  if (action.type === 'fix_metadata') {
    const kept = {};
    for (const [f, v] of Object.entries(d.proposed_changes)) if (take(`fix|${d.item_key}|${zoteroField(f)}`)) kept[f] = v;
    return Object.keys(kept).length ? { ...action, details: { ...d, proposed_changes: kept } } : null;
  }
  if (action.type === 'add_tag') {
    const tags = d.tags.filter((t) => take(`tag|${d.item_key}|${t.toLowerCase()}`));
    return tags.length ? { ...action, details: { ...d, tags } } : null;
  }
  if (action.type === 'merge_duplicate') {
    return take(`merge|${d.keep}|${[...d.merge_keys].sort().join(',')}`) ? action : null;
  }
  return take(`coll|${d.item_key}|${d.collection_key}`) ? action : null;
}

function parseArgs(argv) {
  const o = { dir: 'outputs/librarian', force: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--force') o.force = true;
    else if (['--date', '--dir', '--out'].includes(a)) {
      if (argv[i + 1] === undefined || argv[i + 1].startsWith('--')) throw new UsageError(`${a} needs a value`);
      o[a.slice(2)] = argv[++i];
    } else throw new UsageError(`Unknown argument: ${a}`);
  }
  if (!o.date) throw new UsageError('--date YYYY-MM-DD is required');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(o.date)) throw new UsageError(`--date must be YYYY-MM-DD, got "${o.date}"`);
  return o;
}

export function main(argv) {
  const o = parseArgs(argv);
  const dir = path.resolve(o.dir);
  if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) throw new UsageError(`Directory not found: ${o.dir}`);
  const suffix = `_${o.date}.proposals.json`;
  const files = fs.readdirSync(dir).filter((f) => f.endsWith(suffix)).sort();
  if (!files.length) throw new UsageError(`No proposals file for ${o.date} in ${o.dir} (expected *${suffix}). Run the librarian agents first.`);

  const out = path.resolve(o.out || path.join(dir, `approval_queue_${o.date}.json`));

  const accepted = [];
  const rejected = [];
  const dupes = [];
  const seen = new Set();
  const fileErrors = [];
  const agents = [];

  for (const f of files) {
    let data;
    try { data = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')); } catch (err) { fileErrors.push(`${f}: invalid JSON (${err.message})`); continue; }
    if (!data || !Array.isArray(data.actions)) { fileErrors.push(`${f}: no "actions" array`); continue; }
    const agent = typeof data.agent === 'string' && data.agent ? data.agent : f.slice(0, -suffix.length);
    agents.push(agent);
    data.actions.forEach((raw, idx) => {
      const { action, reason } = validateAction(raw);
      if (!action) { rejected.push({ source_file: f, source_agent: agent, index: idx, reason, proposal: raw }); return; }
      const kept = dedupeAction(action, seen);
      if (!kept) { dupes.push({ source_file: f, source_agent: agent, index: idx, proposal: raw }); return; }
      accepted.push({ ...kept, source_agent: agent });
    });
  }

  const rejectedPath0 = path.join(path.dirname(out), `rejected_${o.date}.json`);
  if (fileErrors.length && !accepted.length && !rejected.length && !dupes.length) {
    for (const e of fileErrors) console.error(`ERROR ${e}`);
    throw new UsageError('No readable proposals file.');
  }
  if (!accepted.length) {
    console.log(`no actions proposed (${files.length} proposals file(s) read; rejected: ${rejected.length}, duplicates dropped: ${dupes.length}). No queue written.`);
    for (const r of rejected) console.log(`  rejected  ${r.source_file} #${r.index}: ${r.reason}`);
    for (const e of fileErrors) console.log(`  FILE ERROR ${e}`);
    if (rejected.length || dupes.length || fileErrors.length) {
      saveQueue(rejectedPath0, { date: o.date, rejected, duplicates_dropped: dupes, file_errors: fileErrors });
      console.log(`Details: ${rejectedPath0}`);
    }
    return 0;
  }
  if (fs.existsSync(out)) {
    if (!o.force) throw new UsageError(`Queue already exists: ${out}. Use --force to rebuild (refused if any action has been decided).`);
    let existing;
    try { existing = JSON.parse(fs.readFileSync(out, 'utf8')); } catch (err) { throw new UsageError(`Existing queue is unreadable (${err.message}); not overwriting. Move it aside first.`); }
    const decided = (existing.actions || []).filter((a) => a.status !== 'pending');
    if (decided.length) throw new UsageError(`Refusing --force: ${decided.length} action(s) in the existing queue are no longer pending (${[...new Set(decided.map((a) => a.status))].join(', ')}). Decisions must not be lost.`);
  }


  const actions = accepted.map((a, i) => {
    const { type, title, paper, details, source_agent } = a;
    return { id: i + 1, type, status: 'pending', title, ...(paper !== undefined ? { paper } : {}), details, source_agent };
  });
  const queue = { date: o.date, source: `librarian-team: ${agents.join(', ') || 'none'}`, actions };
  const rejectedPath = path.join(path.dirname(out), `rejected_${o.date}.json`);
  const rejectedBody = { date: o.date, rejected, duplicates_dropped: dupes, file_errors: fileErrors };

  fs.mkdirSync(path.dirname(out), { recursive: true });
  saveQueue(out, queue);
  saveQueue(rejectedPath, rejectedBody);

  console.log(`Queue written: ${out}`);
  console.log(`  accepted: ${actions.length}   rejected: ${rejected.length}   duplicates dropped: ${dupes.length}`);
  for (const r of rejected) console.log(`  rejected  ${r.source_file} #${r.index}: ${r.reason}`);
  for (const d of dupes) console.log(`  duplicate ${d.source_file} #${d.index}: already proposed`);
  for (const e of fileErrors) console.log(`  FILE ERROR ${e}`);
  if (rejected.length || dupes.length || fileErrors.length) console.log(`Details: ${rejectedPath}`);
  return 0;
}

const isMain = process.argv[1] && import.meta.url === pathToFileURL(fs.realpathSync(process.argv[1])).href;
if (isMain) {
  try {
    process.exit(main(process.argv.slice(2)));
  } catch (err) {
    console.error(err instanceof UsageError ? `Error: ${err.message}` : `Error: ${err.stack || err}`);
    process.exit(1);
  }
}
