#!/usr/bin/env node
/**
 * approval-queue.mjs - review and apply an approval queue of proposed Zotero changes.
 *
 * A queue is a JSON file of proposed actions (see scripts/zotero/README.md for the schema).
 * Nothing in it touches Zotero until you approve an action.
 *
 * Usage:
 *   node scripts/zotero/approval-queue.mjs status <queue-file>
 *   node scripts/zotero/approval-queue.mjs approve <id> <queue-file>
 *   node scripts/zotero/approval-queue.mjs approve-all <queue-file>
 *   node scripts/zotero/approval-queue.mjs reject <id> <queue-file> [reason]
 *   node scripts/zotero/approval-queue.mjs skip <id> <queue-file> [reason]
 *   node scripts/zotero/approval-queue.mjs reconcile <queue-file> [--apply] [--include-manual] [--verbose]
 *
 * Commands:
 *   status       counts by status and by type
 *   approve      execute one action (status pending, approved or failed)
 *   approve-all  execute every action whose status is "approved"; pending ones are untouched
 *   reject/skip  record the decision in the queue file with decided_at (and an optional reason)
 *   reconcile    check pending/approved actions against the live library; dry run unless --apply
 *
 * Every write to Zotero carries the item version (If-Unmodified-Since-Version) and is followed
 * by a re-read. If the re-read does not show the change, the action is marked `failed`, never
 * `applied`. The queue file is rewritten atomically (temp file in the same directory, then rename).
 *
 * Exit codes: 0 success, 1 invalid arguments or file, 2 Zotero API error or a failed action.
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';
import { createClientFromEnv, loadFetch } from './_lib/zotero-client.mjs';
import { fetchCrossrefWork, crossrefWorkToZoteroItem, normaliseDoi } from './_lib/crossref-item.mjs';
import { TITLE_THRESHOLD, normaliseTitle, jaroWinkler } from './_lib/dup-match.mjs';

const EXIT_ARGS = 1;
const EXIT_API = 2;
const PAUSE_MS = 150;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const nowIso = () => new Date().toISOString();

/** Thrown for a write whose re-read did not show the change. */
export class VerifyError extends Error {}

// ---------- Field handling ----------

// Friendly field names used by proposers -> Zotero API field names.
const FIELD_MAP = {
  abstract: 'abstractNote',
  journal: 'publicationTitle',
  doi: 'DOI',
  date: 'date',
  pages: 'pages',
  volume: 'volume',
  issue: 'issue',
};

export const zoteroField = (f) => (f === 'authors' || f === 'creators' ? 'creators' : (FIELD_MAP[f] || f));

// Collection membership and tags are not item fields; they belong to add_to_collection / add_tag.
const NON_FIX_FIELDS = new Set(['collection', 'collections', 'tag', 'tags']);

// Values that are a note to a human, not a value. Whole-value matches only for the bare words,
// so real text that merely starts with a common word ("Missing data in ...") passes.
const PLACEHOLDER_WORDS = /^(unknown|n\/?a|none|null|undefined|tbd|todo|tba|-+|\?+|\.+|untitled|manual|missing)$/i;
const PLACEHOLDER_PHRASES = /^[(<[]?\s*(full\s+)?(fetch\s+(from|via|at|the)\b|crossref\s+(abstract|metadata|lookup|record)\b|apply-time\b|extract (from|via)\b|to be (assigned|determined|confirmed|added|filled|extracted)\b|see (catalogu|report|attached|above|below)|assign\b|\(?missing\))/i;

// Fully bracketed values ("[no title]", "[unknown]", "[n.d.]", "<to be filled>") are notes, not values.
const BRACKETED = /^(\[[^\]]*\]|<[^>]*>)$/;

export function isPlaceholder(v) {
  if (v === undefined || v === null) return true;
  if (Array.isArray(v)) return v.length === 0;
  if (typeof v === 'object') return false;
  const s = String(v).trim();
  return s === '' || PLACEHOLDER_WORDS.test(s) || PLACEHOLDER_PHRASES.test(s) || BRACKETED.test(s);
}

/** Names of creators whose name parts are placeholders (an empty first name is allowed). */
export function placeholderCreators(creators) {
  const bad = [];
  for (const c of creators || []) {
    const main = c.name ?? c.lastName;
    const parts = [main, ...(c.firstName ? [c.firstName] : [])];
    if (parts.some((x) => isPlaceholder(x))) bad.push(JSON.stringify(c.name ?? `${c.firstName || ''} ${c.lastName || ''}`.trim()));
  }
  return bad;
}

/** Normalise any creator representation into Zotero creator objects. */
export function namesToCreators(names, creatorType = 'author') {
  return names.map((n) => {
    const s = String(n).trim();
    if (s.includes(',')) {
      const [family, ...given] = s.split(',');
      return { creatorType, firstName: given.join(',').trim(), lastName: family.trim() };
    }
    const parts = s.split(/\s+/);
    if (parts.length === 1) return { creatorType, name: s };
    return { creatorType, firstName: parts.slice(0, -1).join(' '), lastName: parts[parts.length - 1] };
  });
}

export function toCreators(value) {
  if (!Array.isArray(value)) return [];
  return value.map((c) => {
    if (typeof c === 'string') return namesToCreators([c])[0];
    if (!c || typeof c !== 'object') return null;
    if (c.firstName || c.lastName || c.name) return { creatorType: c.creatorType || 'author', ...c };
    if (c.given || c.family) return { creatorType: 'author', firstName: c.given || '', lastName: c.family || '' };
    return null;
  }).filter(Boolean);
}

const itemKeyOf = (d) => d.item_key || d.key || null;

function tagsWantedOf(d) {
  const arr = Array.isArray(d.tags) ? d.tags
    : Array.isArray(d.proposed_tags) ? d.proposed_tags
      : Array.isArray(d.suggested_tags) ? d.suggested_tags
        : d.tag ? [d.tag] : d.add_tag ? [d.add_tag] : d.proposed_tag ? [d.proposed_tag] : d.suggested_tag ? [d.suggested_tag] : [];
  return arr.filter((t) => typeof t === 'string' && t.trim() !== '').map((t) => t.trim());
}

/**
 * Every (field, value) a fix_metadata action asks to write, across the schemas proposers emit:
 *   proposed_changes: { field: value }   |   field_fixes: [{ field, proposed }]   |   flat { field, proposed }
 * De-duplicated on the Zotero field name; the first schema listed wins. Values are NOT filtered here.
 */
export function fixPairsOf(d) {
  const pairs = new Map();
  const add = (field, value) => {
    if (!field) return;
    const zf = zoteroField(field);
    if (!pairs.has(zf)) pairs.set(zf, [field, value]);
  };
  for (const [field, value] of Object.entries(d.proposed_changes || {})) add(field, value);
  if (Array.isArray(d.field_fixes)) for (const fx of d.field_fixes) if (fx) add(fx.field, fx.proposed);
  if (d.field) add(d.field, d.proposed ?? d.proposed_value);
  return [...pairs.values()];
}

function mergeKeysOf(d) {
  const keep = d.keep || d.keep_key || null;
  const losers = [d.merge, d.remove, d.remove_key, d.merge_away,
    ...(Array.isArray(d.merge_keys) ? d.merge_keys : []),
    ...(Array.isArray(d.keys) ? d.keys.filter((k) => k !== keep) : [])]
    .filter((k) => typeof k === 'string' && k.trim() !== '');
  return { keep, losers: [...new Set(losers)] };
}

const sameCreators = (a, b) => {
  const flat = (cs) => (cs || []).map((c) => `${c.name || ''}|${c.firstName || ''}|${c.lastName || ''}`);
  return JSON.stringify(flat(a)) === JSON.stringify(flat(b));
};

// ---------- Zotero helpers (client + re-read) ----------

const isNotFound = (err) => err && err.status === 404;
const isTrashed = (data) => data?.deleted === 1 || data?.deleted === true;

async function getItemOrNull(ctx, key) {
  try { return await ctx.client.getItem(key); } catch (err) {
    if (isNotFound(err)) return null;
    throw err;
  }
}

/** URI Zotero uses in dc:replaces relations, derived from the configured library. */
function itemURI(ctx, key) {
  const lib = ctx.client.libraryURL().replace('https://api.zotero.org/', '');
  return `http://zotero.org/${lib}/items/${key}`;
}

const typeFieldCache = new Map();
/** Field names valid for an item type, from Zotero's own schema (api.zotero.org/itemTypeFields). */
async function validFieldsFor(ctx, itemType) {
  if (!typeFieldCache.has(itemType)) {
    const res = await ctx.client.request(`https://api.zotero.org/itemTypeFields?itemType=${encodeURIComponent(itemType)}`, { absolute: true });
    if (!Array.isArray(res.data)) throw new Error(`Could not read the valid fields for item type "${itemType}"`);
    typeFieldCache.set(itemType, new Set(res.data.map((f) => f.field)));
  }
  return typeFieldCache.get(itemType);
}

const writeToken = () => crypto.randomBytes(16).toString('hex');

// ---------- Action executors ----------
// Each returns a result object, or throws. A throw marks the action `failed`.

async function verifyCreated(ctx, key, expect) {
  const after = await getItemOrNull(ctx, key);
  const got = after?.data;
  if (!got) throw new VerifyError(`re-read found no item ${key} after create`);
  const problems = [];
  if (isTrashed(got)) problems.push('item is in the trash');
  if (expect.itemType && got.itemType !== expect.itemType) problems.push(`itemType ${got.itemType} != ${expect.itemType}`);
  if (expect.title !== undefined && got.title !== expect.title) problems.push('title differs');
  if (expect.DOI && normaliseDoi(got.DOI) !== normaliseDoi(expect.DOI)) problems.push('DOI differs');
  const gotTags = new Set((got.tags || []).map((t) => t.tag));
  if (!expect.tags.every((t) => gotTags.has(t))) problems.push('tags missing');
  if (problems.length) throw new VerifyError(`item ${key} re-read does not match: ${problems.join('; ')}`);
  return got;
}

async function executeAddItem(action, ctx) {
  const d = action.details || {};
  const tags = ['librarian-team', `source-${action.paper || 'unknown'}`, `relevance-${d.relevance || 'medium'}`];
  const doi = normaliseDoi(d.doi || d.DOI);

  // Never create a second item for an action that may already have created one.
  if (action.created_key) {
    const existing = await getItemOrNull(ctx, action.created_key);
    if (existing && !isTrashed(existing.data)) {
      await verifyCreated(ctx, action.created_key, { DOI: doi, tags });
      return { key: action.created_key, adopted: true, verified: true };
    }
    console.warn(`  note: created_key ${action.created_key} is ${existing ? 'in the trash' : 'gone (404)'}; clearing it and looking for the item again`);
    delete action.created_key;
  }
  // The queue save after a create can fail, so a plain re-approve must not POST again: look for
  // the DOI in the library first, whatever the status, and adopt an existing non-trashed match.
  if (doi) {
    const hits = (await ctx.client.getJson(`/items?${new URLSearchParams({ q: doi, qmode: 'everything', limit: '25' })}`)) || [];
    const hit = hits.find((it) => normaliseDoi(it.data?.DOI) === doi && !isTrashed(it.data));
    if (hit) {
      action.created_key = hit.key;
      return { key: hit.key, adopted: true, note: 'an item with this DOI already existed; adopted instead of creating another', verified: true };
    }
  }

  // With a DOI, Crossref decides the item type and fields. The proposer's metadata is the
  // fallback when there is no DOI, Crossref is unreachable, or the type has no mapping.
  const work = doi ? await fetchCrossrefWork(doi, { fetch: ctx.fetch, mailto: ctx.env.CROSSREF_EMAIL || ctx.env.UNPAYWALL_EMAIL || '' }) : null;
  let item = work ? crossrefWorkToZoteroItem(work) : null;
  let source = 'crossref';
  if (!item) {
    source = 'proposer';
    const abstract = d.abstract || '';
    const title = d.title || action.title || '';
    item = doi
      ? { itemType: 'journalArticle', title, creators: toCreators(d.authors), abstractNote: abstract, publicationTitle: d.venue || '', date: d.date || '', DOI: doi, url: d.url || '' }
      : { itemType: 'webpage', title, creators: toCreators(d.authors), abstractNote: d.venue ? `[Source: ${d.venue}] ${abstract}`.trim() : abstract, date: d.date || '', url: d.url || '' };
  }
  if (isPlaceholder(item.title)) throw new Error(`refused: the item has no usable title (${JSON.stringify(item.title)})`);
  const badNames = placeholderCreators(item.creators);
  if (badNames.length) throw new Error(`refused placeholder creator name(s): ${badNames.join(', ')}`);
  item.tags = tags.map((tag) => ({ tag }));
  item.collections = [];

  const created = await ctx.client.request('/items', { method: 'POST', body: [item], headers: { 'Zotero-Write-Token': writeToken() } });
  const key = created.data?.successful?.['0']?.key || created.data?.success?.['0'];
  if (!key) throw new Error(`Zotero rejected the item: ${JSON.stringify(created.data?.failed ?? created.data)}`);
  // Record the key before verifying, so a crash or a failed verify cannot lead to a second create.
  action.created_key = key;
  try {
    ctx.persist?.();
  } catch (err) {
    console.error(`Item ${key} WAS created in Zotero for action ${action.id}, but saving the queue failed (${err.message}).`);
    console.error(`Add "created_key": "${key}" to action ${action.id} in the queue file by hand before approving it again.`);
    throw new Error(`created item ${key} but could not save the queue: ${err.message}`);
  }

  await verifyCreated(ctx, key, { itemType: item.itemType, title: item.title, DOI: item.DOI, tags });
  return { key, title: item.title, itemType: item.itemType, source, verified: true };
}

async function executeFixMetadata(action, ctx) {
  const d = action.details || {};
  const key = itemKeyOf(d);
  if (!key) throw new Error('fix_metadata action missing item_key');
  const pairs = fixPairsOf(d);
  if (pairs.length === 0) throw new Error('fix_metadata has no field to apply (unrecognised detail schema)');

  const bad = pairs.filter(([, v]) => isPlaceholder(v)).map(([f, v]) => `${f}=${JSON.stringify(v)}`);
  if (bad.length) throw new Error(`refused placeholder value(s): ${bad.join(', ')}. Replace them with real values or reject the action.`);

  const item = await ctx.client.getItem(key);
  const data = item.data || {};
  const valid = await validFieldsFor(ctx, data.itemType);

  const patch = {};
  const warnings = [];
  for (const [field, value] of pairs) {
    const zf = zoteroField(field);
    if (NON_FIX_FIELDS.has(field) || (zf !== 'creators' && !valid.has(zf))) {
      warnings.push(`dropped "${field}": not a valid field for item type ${data.itemType}`);
      continue;
    }
    patch[zf] = zf === 'creators' ? toCreators(value) : value;
  }
  if (patch.creators) {
    const badNames = placeholderCreators(patch.creators);
    if (badNames.length) throw new Error(`refused placeholder creator name(s): ${badNames.join(', ')}`);
    if (patch.creators.length === 0) throw new Error('refused: creators value held no usable creator');
  }
  for (const w of warnings) console.warn(`  warning: ${w}`);
  if (Object.keys(patch).length === 0) throw new Error(`no applicable fields left; ${warnings.join('; ')}`);

  await ctx.client.request(`/items/${key}`, { method: 'PATCH', body: patch, version: item.version ?? data.version });

  const after = (await ctx.client.getItem(key)).data || {};
  const mismatched = Object.entries(patch).filter(([f, v]) => (f === 'creators'
    ? !sameCreators(after.creators, v)
    : String(after[f] ?? '').trim() !== String(v).trim())).map(([f]) => f);
  if (mismatched.length) throw new VerifyError(`re-read does not show the change for: ${mismatched.join(', ')}`);
  return { key, fields_updated: Object.keys(patch), ...(warnings.length ? { warnings } : {}), verified: true };
}

async function executeAddTag(action, ctx) {
  const d = action.details || {};
  const key = itemKeyOf(d);
  if (!key) throw new Error('add_tag action missing item_key');
  const wanted = tagsWantedOf(d);
  if (wanted.length === 0) throw new Error('add_tag has no tag to add (unrecognised detail schema or empty tag)');

  const item = await ctx.client.getItem(key);
  const current = item.data?.tags || [];
  const have = new Set(current.map((t) => t.tag));
  const missing = wanted.filter((t) => !have.has(t));
  if (missing.length) {
    await ctx.client.request(`/items/${key}`, { method: 'PATCH', body: { tags: [...current, ...missing.map((tag) => ({ tag }))] }, version: item.version ?? item.data?.version });
    const after = new Set(((await ctx.client.getItem(key)).data?.tags || []).map((t) => t.tag));
    const still = wanted.filter((t) => !after.has(t));
    if (still.length) throw new VerifyError(`re-read does not show tag(s): ${still.join(', ')}`);
  }
  return { key, tags_added: missing, verified: true };
}

async function executeAddToCollection(action, ctx) {
  const d = action.details || {};
  const key = itemKeyOf(d);
  const col = d.collection_key;
  if (!key || !col) throw new Error('add_to_collection action missing item_key or collection_key');
  const item = await ctx.client.getItem(key);
  const cols = item.data?.collections || [];
  if (!cols.includes(col)) {
    await ctx.client.request(`/items/${key}`, { method: 'PATCH', body: { collections: [...cols, col] }, version: item.version ?? item.data?.version });
    if (!((await ctx.client.getItem(key)).data?.collections || []).includes(col)) {
      throw new VerifyError(`re-read does not show item ${key} in collection ${col}`);
    }
  }
  return { key, collection: col, verified: true };
}

// Emulates Zotero's "Merge Items" through the write API: keeper absorbs the losers' tags and
// collections and records them under dc:replaces; losers' children move to the keeper; losers
// go to the TRASH (deleted: 1, reversible in Zotero), never a hard DELETE. The keeper is
// updated first, so an interruption midway cannot leave a loser trashed with its data unrecorded.
async function executeMergeDuplicate(action, ctx) {
  const { keep: keepKey, losers } = mergeKeysOf(action.details || {});
  if (!keepKey || losers.length === 0) throw new Error('merge_duplicate action missing keep/merge keys');
  if (losers.includes(keepKey)) throw new Error(`refused: the keeper ${keepKey} is also listed as an item to merge away`);

  const keep = await ctx.client.getItem(keepKey);
  const kd = keep.data || {};
  if (isTrashed(kd)) throw new Error(`keeper ${keepKey} is in the trash; refusing to merge into it`);

  // One read per loser serves the similarity check, the tag/collection merge and the version
  // precondition on its trash PATCH, so a change in between gives a 412 instead of a lost tag.
  const live = [];
  for (const lk of losers) {
    const loser = await getItemOrNull(ctx, lk);
    if (!loser || isTrashed(loser.data)) continue; // already gone or trashed
    const ld = loser.data || {};
    const sameType = ld.itemType === kd.itemType;
    const doiK = normaliseDoi(kd.DOI);
    const sameDoi = doiK !== '' && doiK === normaliseDoi(ld.DOI);
    const sim = jaroWinkler(normaliseTitle(kd.title), normaliseTitle(ld.title));
    if (!sameType || !(sameDoi || sim >= TITLE_THRESHOLD)) {
      throw new Error(`refused: ${lk} does not look like a duplicate of ${keepKey} (itemType ${ld.itemType} vs ${kd.itemType}; DOI ${sameDoi ? 'equal' : 'differs or missing'}; title similarity ${sim.toFixed(2)} < ${TITLE_THRESHOLD}). No change was made.`);
    }
    live.push({ key: lk, item: loser });
  }

  const tagSet = new Set((kd.tags || []).map((t) => t.tag));
  const mergedTags = [...(kd.tags || [])];
  const colSet = new Set(kd.collections || []);
  const mergedCols = [...(kd.collections || [])];
  const relations = { ...(kd.relations || {}) };
  const prev = relations['dc:replaces'];
  const replaces = Array.isArray(prev) ? [...prev] : prev ? [prev] : [];
  for (const { key: lk, item: loser } of live) {
    for (const t of loser.data?.tags || []) if (!tagSet.has(t.tag)) { mergedTags.push({ tag: t.tag }); tagSet.add(t.tag); }
    for (const c of loser.data?.collections || []) if (!colSet.has(c)) { mergedCols.push(c); colSet.add(c); }
    const uri = itemURI(ctx, lk);
    if (!replaces.includes(uri)) replaces.push(uri);
  }

  relations['dc:replaces'] = replaces;
  await ctx.client.request(`/items/${keepKey}`, { method: 'PATCH', body: { tags: mergedTags, collections: mergedCols, relations }, version: keep.version ?? kd.version });
  const keepAfter = (await ctx.client.getItem(keepKey)).data || {};
  const haveTags = new Set((keepAfter.tags || []).map((t) => t.tag));
  const haveRel = [].concat(keepAfter.relations?.['dc:replaces'] || []);
  if (!mergedTags.every((t) => haveTags.has(t.tag)) || !mergedCols.every((c) => (keepAfter.collections || []).includes(c)) || !replaces.every((u) => haveRel.includes(u))) {
    throw new VerifyError(`re-read of keeper ${keepKey} does not show the merged tags, collections and dc:replaces; no loser was changed`);
  }

  const trashed = [];
  const reassigned = [];
  for (const { key: lk, item: loser } of live) {
    for (const child of await ctx.client.listChildren(lk)) {
      await ctx.client.request(`/items/${child.key}`, { method: 'PATCH', body: { parentItem: keepKey }, version: child.version ?? child.data?.version });
      if ((await ctx.client.getItem(child.key)).data?.parentItem !== keepKey) throw new VerifyError(`re-read shows child ${child.key} still not under ${keepKey}`);
      reassigned.push(child.key);
    }
    await ctx.client.request(`/items/${lk}`, { method: 'PATCH', body: { deleted: 1 }, version: loser.version ?? loser.data?.version });
    if (!isTrashed((await ctx.client.getItem(lk)).data)) throw new VerifyError(`re-read shows ${lk} not in the trash`);
    trashed.push(lk);
  }
  return { merged: true, keep: keepKey, trashed, tags_added: mergedTags.length - (kd.tags || []).length, collections_added: mergedCols.length - (kd.collections || []).length, children_reassigned: reassigned, verified: true };
}

export const EXECUTORS = {
  add_item: executeAddItem,
  fix_metadata: executeFixMetadata,
  add_tag: executeAddTag,
  add_to_collection: executeAddToCollection,
  merge_duplicate: executeMergeDuplicate,
};

// ---------- Reconcilers (read-only: is this action ALREADY satisfied?) ----------
// Verdicts: 'already_done' (verified satisfied), 'outstanding' (still to do), 'needs-manual'
// (no auto-check, or the target is unresolvable). Conservative: 'already_done' only on a
// positive verification, never on ambiguity.

function isFieldFilled(data, field) {
  if (field === 'authors' || field === 'creators') return Array.isArray(data.creators) && data.creators.length > 0;
  const v = data[zoteroField(field)];
  return v !== undefined && v !== null && String(v).trim() !== '';
}

async function reconAddTag(action, ctx) {
  const d = action.details || {};
  const key = itemKeyOf(d);
  const wanted = tagsWantedOf(d);
  if (!key || wanted.length === 0) return 'needs-manual';
  const item = await getItemOrNull(ctx, key);
  if (!item) return 'needs-manual';
  const tags = new Set((item.data?.tags || []).map((t) => t.tag));
  return wanted.every((t) => tags.has(t)) ? 'already_done' : 'outstanding';
}

const squash = (v) => String(v ?? '').trim().replace(/\s+/g, ' ').toLowerCase();

// 'already_done' only when every concrete proposed value EQUALS the current value. A different
// non-empty value is 'differs' (stays pending for a human); an empty field is 'outstanding'.
async function reconFixMetadata(action, ctx) {
  const d = action.details || {};
  const key = itemKeyOf(d);
  const pairs = fixPairsOf(d).filter(([f, v]) => !NON_FIX_FIELDS.has(f) && !isPlaceholder(v));
  if (!key || pairs.length === 0) return 'needs-manual';
  const item = await getItemOrNull(ctx, key);
  if (!item) return 'needs-manual';
  const data = item.data || {};
  let allEqual = true;
  let differs = false;
  for (const [f, v] of pairs) {
    const zf = zoteroField(f);
    if (zf === 'creators') {
      const flat = (cs) => JSON.stringify((cs || []).map((c) => squash(`${c.name || ''}|${c.firstName || ''}|${c.lastName || ''}`)));
      if (flat(toCreators(v)) === flat(data.creators)) continue;
      allEqual = false;
      if (isFieldFilled(data, 'creators')) differs = true;
      continue;
    }
    if (squash(data[zf]) === squash(v)) continue;
    allEqual = false;
    if (isFieldFilled(data, f)) differs = true;
  }
  if (allEqual) return 'already_done';
  return differs ? 'differs' : 'outstanding';
}

async function reconMergeDuplicate(action, ctx) {
  const { keep: keepKey, losers } = mergeKeysOf(action.details || {});
  if (!keepKey || losers.length === 0) return 'needs-manual';
  const keep = await getItemOrNull(ctx, keepKey);
  // Keeper trashed or gone: the pair was deduplicated the other way round.
  if (!keep || isTrashed(keep.data)) return 'already_done';
  const rel = [].concat(keep.data?.relations?.['dc:replaces'] || []);
  for (const lk of losers) {
    const loser = await getItemOrNull(ctx, lk);
    const handled = !loser || isTrashed(loser.data) || rel.includes(itemURI(ctx, lk));
    if (!handled) return 'outstanding';
  }
  return 'already_done';
}

async function reconAddItem(action, ctx) {
  const d = action.details || {};
  const doi = normaliseDoi(d.doi || d.DOI);
  const title = d.title || action.title;
  const norm = (s) => String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  const search = async (q) => (await ctx.client.getJson(`/items?${new URLSearchParams({ q, qmode: 'everything', limit: '5' })}`)) || [];
  if (doi) {
    if ((await search(doi)).some((it) => normaliseDoi(it.data?.DOI) === doi)) return 'already_done';
  }
  if (title) {
    if ((await search(String(title).slice(0, 60))).some((it) => norm(it.data?.title) === norm(title))) return 'already_done';
    return 'outstanding';
  }
  return 'needs-manual';
}

async function reconAddToCollection(action, ctx) {
  const d = action.details || {};
  const key = itemKeyOf(d);
  if (!key || !d.collection_key) return 'needs-manual';
  const item = await getItemOrNull(ctx, key);
  if (!item) return 'needs-manual';
  return (item.data?.collections || []).includes(d.collection_key) ? 'already_done' : 'outstanding';
}

export const RECONCILERS = {
  add_tag: reconAddTag,
  fix_metadata: reconFixMetadata,
  merge_duplicate: reconMergeDuplicate,
  add_item: reconAddItem,
  add_to_collection: reconAddToCollection,
};

// ---------- Queue file ----------

export class QueueFileError extends Error {}

export function loadQueue(filePath) {
  if (!fs.existsSync(filePath)) throw new QueueFileError(`File not found: ${filePath}`);
  let queue;
  try { queue = JSON.parse(fs.readFileSync(filePath, 'utf8')); } catch (err) { throw new QueueFileError(`Invalid JSON: ${err.message}`); }
  if (!queue || !Array.isArray(queue.actions)) throw new QueueFileError('Queue file has no "actions" array');
  return queue;
}

/** Write to a temp file in the same directory, then rename over the queue. The original survives any failure. */
export function saveQueue(filePath, queue, io = fs) {
  const tmp = path.join(path.dirname(filePath), `.${path.basename(filePath)}.${process.pid}.${Date.now()}.tmp`);
  try {
    const fd = io.openSync(tmp, 'w');
    try { io.writeSync(fd, JSON.stringify(queue, null, 2) + '\n'); io.fsyncSync(fd); } finally { io.closeSync(fd); }
    io.renameSync(tmp, filePath);
  } catch (err) {
    try { io.rmSync(tmp, { force: true }); } catch { /* best effort */ }
    throw err;
  }
}

const parseId = (id) => {
  if (!/^\d+$/.test(String(id))) throw new QueueFileError(`Action id must be a whole number, got "${id}"`);
  return Number(id);
};
const findAction = (queue, id) => queue.actions.find((a) => a.id === parseId(id));

// ---------- Lock ----------
// Commands that write the queue hold <queue>.lock (created with O_EXCL, containing the pid and
// an ISO time) for their whole run, so two commands cannot overwrite each other's decisions.

const STALE_LOCK_MS = 30 * 60 * 1000;

function removeLock(lockPath, onlyIfOwner = false) {
  try {
    if (onlyIfOwner) {
      let held = {};
      try { held = JSON.parse(fs.readFileSync(lockPath, 'utf8')); } catch { /* unreadable: not ours to judge, fall through */ }
      if (held.pid !== undefined && held.pid !== process.pid) return; // another process owns it now
    }
    fs.unlinkSync(lockPath);
  } catch { /* already gone */ }
}

function pidAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return true; // unknown: fall back to the age rule
  try { process.kill(pid, 0); return true; } catch (err) { return err.code !== 'ESRCH'; }
}

export function acquireLock(file, { now = Date.now(), warn = console.error } = {}) {
  const lockPath = `${file}.lock`;
  const body = JSON.stringify({ pid: process.pid, at: new Date(now).toISOString() });
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      fs.writeFileSync(lockPath, body, { flag: 'wx' });
      return () => removeLock(lockPath, true);
    } catch (err) {
      if (err.code !== 'EEXIST') throw err;
      let held = {};
      try { held = JSON.parse(fs.readFileSync(lockPath, 'utf8')); } catch { /* unreadable: fall back to mtime */ }
      let since = Date.parse(held.at);
      if (!Number.isFinite(since)) { try { since = fs.statSync(lockPath).mtimeMs; } catch { since = now; } }
      const dead = !pidAlive(held.pid);
      if (!dead && now - since < STALE_LOCK_MS) {
        throw new QueueFileError(`queue is locked by pid ${held.pid ?? 'unknown'} since ${new Date(since).toISOString()} (${lockPath}). If that process is gone, delete the lock file or wait 30 minutes.`);
      }
      warn(`warning: replacing stale lock (${dead ? 'process not running' : 'older than 30 minutes'}; pid ${held.pid ?? 'unknown'}, since ${new Date(since).toISOString()})`);
      removeLock(lockPath);
    }
  }
  throw new QueueFileError(`could not take the queue lock ${lockPath}`);
}

async function withLock(file, fn) {
  if (!fs.existsSync(file)) throw new QueueFileError(`File not found: ${file}`);
  const release = acquireLock(file);
  const onSignal = (sig) => () => { release(); process.exit(sig === 'SIGINT' ? 130 : 143); };
  const handlers = ['SIGINT', 'SIGTERM'].map((sig) => [sig, onSignal(sig)]);
  for (const [sig, h] of handlers) process.once(sig, h);
  try {
    return await fn();
  } finally {
    for (const [sig, h] of handlers) process.removeListener(sig, h);
    release();
  }
}

async function runAction(action, ctx) {
  const executor = EXECUTORS[action.type];
  if (!executor) throw new Error(`Unknown action type: ${action.type}`);
  return executor(action, ctx);
}

function recordResult(action, result) {
  action.status = 'applied';
  action.applied_at = nowIso();
  action.result = result;
  delete action.error;
  delete action.failed_at;
}

function recordFailure(action, err) {
  action.status = 'failed';
  action.failed_at = nowIso();
  action.error = err.message;
}

// ---------- Commands ----------

async function cmdApprove(id, file, ctx, { retry = false } = {}) {
  const queue = loadQueue(file);
  const action = findAction(queue, id);
  if (!action) throw new QueueFileError(`Action ID ${id} not found in queue`);
  if (action.status === 'failed' && !retry) {
    throw new QueueFileError(`Action ${id} failed earlier (${action.error || 'no reason recorded'}). Check Zotero for a partial change, then re-run with --retry.`);
  }
  if (!['approved', 'pending', 'failed'].includes(action.status)) {
    throw new QueueFileError(`Action ${id} has status "${action.status}" - cannot execute`);
  }
  ctx.retry = retry || action.status === 'failed';
  ctx.persist = () => saveQueue(file, queue);
  let failed = false;
  try {
    recordResult(action, await runAction(action, ctx));
    console.log(`✓ Action ${id} (${action.type}): applied`);
    console.log(`  ${JSON.stringify(action.result)}`);
  } catch (err) {
    recordFailure(action, err);
    failed = true;
    console.error(`✗ Action ${id} (${action.type}): ${err.message}`);
  }
  saveQueue(file, queue);
  return failed ? EXIT_API : 0;
}

async function cmdApproveAll(file, ctx) {
  const queue = loadQueue(file);
  const todo = queue.actions.filter((a) => a.status === 'approved');
  if (todo.length === 0) { console.log('No approved actions to execute.'); return 0; }
  console.log(`Executing ${todo.length} approved actions...\n`);
  ctx.retry = false;
  ctx.persist = () => saveQueue(file, queue);
  let ok = 0;
  let failed = 0;
  for (const action of todo) {
    try {
      recordResult(action, await runAction(action, ctx));
      ok++;
      console.log(`  ✓ [${action.id}] ${action.type}: ${action.title || ''}`);
    } catch (err) {
      recordFailure(action, err);
      failed++;
      console.error(`  ✗ [${action.id}] ${action.type}: ${err.message}`);
    }
    saveQueue(file, queue); // persist after each action so an interruption loses nothing
    await ctx.sleep(PAUSE_MS);
  }
  console.log(`\nDone: ${ok} applied, ${failed} failed.`);
  return failed ? EXIT_API : 0;
}

function countBy(actions, key) {
  const counts = {};
  for (const a of actions) counts[a[key]] = (counts[a[key]] || 0) + 1;
  return counts;
}

export function cmdStatus(file) {
  const queue = loadQueue(file);
  console.log(`Queue: ${file}`);
  console.log(`Date: ${queue.date ?? '(none)'}`);
  console.log(`Total actions: ${queue.actions.length}`);
  console.log('By status:');
  for (const [k, v] of Object.entries(countBy(queue.actions, 'status'))) console.log(`  ${k}: ${v}`);
  console.log('By type:');
  for (const [k, v] of Object.entries(countBy(queue.actions, 'type'))) console.log(`  ${k}: ${v}`);
  return 0;
}

// Dry run by default; --apply writes verified already_done / needs-manual statuses back.
async function cmdReconcile(file, { apply, includeManual, verbose }, ctx) {
  const queue = loadQueue(file);
  const wanted = includeManual ? ['pending', 'approved', 'needs-manual'] : ['pending', 'approved'];
  const targets = queue.actions.filter((a) => wanted.includes(a.status));
  const buckets = { already_done: [], outstanding: [], differs: [], 'needs-manual': [], error: [] };

  for (const action of targets) {
    const recon = RECONCILERS[action.type];
    let verdict;
    if (!recon) {
      verdict = 'needs-manual'; // flag_* and unknown types have no executor
    } else {
      try { verdict = await recon(action, ctx); } catch (err) { verdict = 'error'; action.reconcile_error = err.message; }
      await ctx.sleep(PAUSE_MS);
    }
    buckets[verdict].push(action);
    if (!apply) continue;
    if (verdict === 'already_done') {
      Object.assign(action, { status: 'already_done', reconciled_at: nowIso(), reconciled_note: 'verified already satisfied in Zotero' });
    } else if (verdict === 'needs-manual') {
      Object.assign(action, { status: 'needs-manual', reconciled_at: nowIso(), reconciled_note: 'no auto-executor or unresolvable target key' });
    } else if (verdict === 'outstanding' && action.status === 'needs-manual') {
      Object.assign(action, { status: 'pending', reconciled_at: nowIso(), reconciled_note: 'reopened: reconcile found this still actionable' });
    }
  }
  if (apply) saveQueue(file, queue);

  const label = (a) => `    [${a.id}] ${a.type} (${itemKeyOf(a.details || {}) || a.details?.keep || '-'}): ${(a.title || '').slice(0, 60)}`;
  console.log(`Reconcile: ${file}`);
  console.log(`  scanned: ${targets.length}`);
  for (const [k, v] of Object.entries(buckets)) console.log(`  ${k}: ${v.length}`);
  console.log(apply ? '  -> applied: already_done / needs-manual written back; outstanding left as is'
    : '  -> dry run: nothing written (pass --apply to persist)');
  if (buckets.outstanding.length) { console.log('\n  OUTSTANDING (still to do):'); buckets.outstanding.forEach((a) => console.log(label(a))); }
  if (buckets.differs.length) { console.log('\n  DIFFERS (the field already holds a different value; left pending for you to decide):'); buckets.differs.forEach((a) => console.log(label(a))); }
  if (verbose) {
    for (const k of ['already_done', 'needs-manual', 'error']) {
      if (buckets[k].length) { console.log(`\n  ${k.toUpperCase()}:`); buckets[k].forEach((a) => console.log(label(a) + (k === 'error' ? ` - ${a.reconcile_error}` : ''))); }
    }
  }
  return buckets.error.length ? EXIT_API : 0;
}

function cmdDecide(status, id, file, reason) {
  const queue = loadQueue(file);
  const action = findAction(queue, id);
  if (!action) throw new QueueFileError(`Action ID ${id} not found in queue`);
  if (['applied', 'already_done'].includes(action.status)) {
    throw new QueueFileError(`Action ${id} is already ${action.status}; cannot mark it ${status}`);
  }
  action.status = status;
  action.decided_at = nowIso();
  if (reason) action.reason = reason;
  saveQueue(file, queue);
  console.log(`Action ${id} (${action.type}): marked ${status}${reason ? ` - ${reason}` : ''}`);
  return 0;
}

// ---------- Main ----------

const USAGE = 'Usage: approval-queue.mjs <status|approve|approve-all|reject|skip|reconcile> ...  (see the header of this file)';

export async function createContext() {
  const client = await createClientFromEnv();
  for (const v of ['ZOTERO_API_KEY', 'ZOTERO_LIBRARY_ID']) {
    if (!client.env[v]) throw new QueueFileError(`${v} is not set. Add it to .env (see scripts/zotero/README.md).`);
  }
  return { client, env: client.env, fetch: await loadFetch(client.env), sleep };
}

export async function main(argv) {
  const [command, ...rest] = argv;
  const need = (n, usage) => { if (rest.length < n) throw new QueueFileError(`Usage: approval-queue.mjs ${usage}`); };
  const makeCtx = createContext;
  switch (command) {
    case 'status': need(1, 'status <queue-file>'); return cmdStatus(rest[0]);
    case 'reject': need(2, 'reject <id> <queue-file> [reason]'); parseId(rest[0]); return withLock(rest[1], async () => cmdDecide('rejected', rest[0], rest[1], rest.slice(2).join(' ') || null));
    case 'skip': need(2, 'skip <id> <queue-file> [reason]'); parseId(rest[0]); return withLock(rest[1], async () => cmdDecide('skipped', rest[0], rest[1], rest.slice(2).join(' ') || null));
    case 'approve': {
      const args = rest.filter((a) => a !== '--retry');
      need(2, 'approve <id> <queue-file> [--retry]');
      parseId(args[0]);
      return withLock(args[1], async () => cmdApprove(args[0], args[1], await makeCtx(), { retry: rest.includes('--retry') }));
    }
    case 'approve-all': need(1, 'approve-all <queue-file>'); return withLock(rest[0], async () => cmdApproveAll(rest[0], await makeCtx()));
    case 'reconcile': {
      const file = rest.find((a) => !a.startsWith('--'));
      need(1, 'reconcile <queue-file> [--apply] [--include-manual] [--verbose]');
      const opts = { apply: rest.includes('--apply'), includeManual: rest.includes('--include-manual'), verbose: rest.includes('--verbose') };
      const go = async () => cmdReconcile(file, opts, await makeCtx());
      return opts.apply ? withLock(file, go) : (loadQueue(file), go());
    }
    default: throw new QueueFileError(USAGE);
  }
}

const isMain = process.argv[1] && import.meta.url === pathToFileURL(fs.realpathSync(process.argv[1])).href;
if (isMain) {
  main(process.argv.slice(2)).then((code) => process.exit(code), (err) => {
    console.error(err instanceof QueueFileError ? err.message : `Fatal: ${err.message}`);
    process.exit(err instanceof QueueFileError ? EXIT_ARGS : EXIT_API);
  });
}
