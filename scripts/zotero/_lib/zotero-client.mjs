/**
 * Minimal Zotero Web API client. Node built-ins only (fetch, crypto, fs).
 *
 *   const client = createClient({ fetch, env });   // inject fetch in tests
 *   const client = await createClientFromEnv();    // loads .env, honours WREN_FAKE_FETCH
 *
 * Env: ZOTERO_API_KEY, ZOTERO_LIBRARY_ID, optional ZOTERO_LIBRARY_TYPE (user|group).
 *
 * WREN_FAKE_FETCH=<path> is TEST-ONLY: it points at an ES module whose default
 * export replaces fetch (see tests/node/fake-fetch.mjs). Never set it in real use.
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const API_BASE = 'https://api.zotero.org';

/** Project root: $CLAUDE_PROJECT_DIR, else the repo root (three levels above _lib). */
export function projectRoot(env = process.env) {
  return env.CLAUDE_PROJECT_DIR || path.resolve(HERE, '..', '..', '..');
}

/** Parse `KEY=value` lines. Handles comments, `export `, single/double quotes. */
export function parseEnv(text) {
  const out = {};
  for (const raw of String(text).split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith('#')) continue;
    const m = line.replace(/^export\s+/, '').match(/^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/);
    if (!m) continue;
    let val = m[2].trim();
    const q = val[0];
    let close = -1;
    if (q === '"' || q === "'") {
      for (let i = 1; i < val.length; i++) {
        if (val[i] === '\\' && q === '"') { i++; continue; }
        if (val[i] === q) { close = i; break; }
      }
    }
    if (close > 0) {
      // Quoted value: anything after the closing quote (e.g. ` # comment`) is ignored.
      val = val.slice(1, close);
      if (q === '"') val = val.replace(/\\n/g, '\n').replace(/\\"/g, '"');
    } else {
      val = val.replace(/\s+#.*$/, '').trim(); // inline comment on unquoted value
    }
    out[m[1]] = val;
  }
  return out;
}

/** Load <root>/.env into `env` without overriding variables that are already set. */
export function loadDotEnv(env = process.env, root = projectRoot(env)) {
  const file = path.join(root, '.env');
  if (!fs.existsSync(file)) return {};
  const parsed = parseEnv(fs.readFileSync(file, 'utf8'));
  // WREN_FAKE_* is test-only and must come from the process environment, never a file.
  for (const k of Object.keys(parsed)) if (k.startsWith('WREN_FAKE_')) delete parsed[k];
  for (const [k, v] of Object.entries(parsed)) if (env[k] === undefined) env[k] = v;
  return parsed;
}

/** Resolve the fetch to use: the test-only fake when WREN_FAKE_FETCH is set. */
export async function loadFetch(env = process.env) {
  if (env.WREN_FAKE_FETCH) {
    const mod = await import(pathToFileURL(path.resolve(env.WREN_FAKE_FETCH)).href);
    return mod.default;
  }
  return globalThis.fetch;
}

export class ZoteroError extends Error {
  constructor(message, { status, code, body } = {}) {
    super(message);
    this.name = 'ZoteroError';
    this.status = status;
    this.code = code;
    this.body = body;
  }
}

const defaultSleep = (ms) => new Promise((r) => setTimeout(r, ms));

export function createClient({ fetch = globalThis.fetch, env = process.env, sleep = defaultSleep, maxRetries = 3 } = {}) {
  function libraryURL(lib = {}) {
    const type = (lib.type || env.ZOTERO_LIBRARY_TYPE || 'user').toLowerCase();
    if (type !== 'user' && type !== 'group') {
      throw new ZoteroError(`ZOTERO_LIBRARY_TYPE must be "user" or "group", got "${type}"`);
    }
    const id = lib.id || env.ZOTERO_LIBRARY_ID;
    if (!id) throw new ZoteroError('ZOTERO_LIBRARY_ID is not set (add it to .env)');
    return `${API_BASE}/${type}s/${id}`;
  }

  function headers(extra = {}) {
    if (!env.ZOTERO_API_KEY) throw new ZoteroError('ZOTERO_API_KEY is not set (add it to .env)');
    return { 'Zotero-API-Key': env.ZOTERO_API_KEY, 'Zotero-API-Version': '3', ...extra };
  }

  const MAX_WAIT_S = 60;
  const secs = (v) => {
    if (v === null || v === undefined || String(v).trim() === '') return null;
    const n = Number(v);
    return Number.isFinite(n) && n >= 0 ? Math.min(n, MAX_WAIT_S) : null;
  };

  /**
   * request('/items?limit=1', { method, body, form, version, headers, library })
   * `body` is sent as JSON, `form` (object) as x-www-form-urlencoded.
   * `version` sets If-Unmodified-Since-Version (writes). Returns { status, headers, data }.
   */
  async function request(p, { method = 'GET', body, form, version, headers: extra = {}, library, absolute = false } = {}) {
    const url = absolute ? p : libraryURL(library) + p;
    const h = headers(extra);
    let payload;
    if (form !== undefined) {
      h['Content-Type'] = 'application/x-www-form-urlencoded';
      payload = new URLSearchParams(form).toString();
    } else if (body !== undefined) {
      h['Content-Type'] = 'application/json';
      payload = JSON.stringify(body);
    }
    if (version !== undefined && version !== null && method !== 'GET') {
      h['If-Unmodified-Since-Version'] = String(version);
    }
    for (let attempt = 0; ; attempt++) {
      const res = await fetch(url, { method, headers: h, body: payload });
      const wait = secs(res.headers.get('Retry-After')) ?? secs(res.headers.get('Backoff-After')) ?? secs(res.headers.get('Backoff'));
      if (res.status === 429) {
        if (attempt >= maxRetries) {
          throw new ZoteroError(`Zotero rate limit (429) persisted after ${maxRetries} retries: ${method} ${p}`, { status: 429, code: 'rate_limited' });
        }
        await sleep(Math.min(wait ?? 2 ** attempt, MAX_WAIT_S) * 1000);
        continue;
      }
      const text = await res.text();
      if (res.status === 412) {
        throw new ZoteroError(`Zotero version conflict (412): ${method} ${p} was rejected because the object changed since it was read. Re-read it and retry.`, { status: 412, code: 'version_conflict', body: text });
      }
      if (res.status === 403) {
        throw new ZoteroError(`Zotero refused the request (403): ${method} ${p}. Check that ZOTERO_API_KEY has write access to this library and that ZOTERO_LIBRARY_ID/ZOTERO_LIBRARY_TYPE are right.`, { status: 403, code: 'forbidden', body: text });
      }
      if (!res.ok) {
        throw new ZoteroError(`Zotero HTTP ${res.status}: ${method} ${p} ${text.slice(0, 300)}`, { status: res.status, code: 'http_error', body: text });
      }
      if (wait && res.status !== 429) await sleep(wait * 1000); // honour Backoff on success
      let data = null;
      if (text) {
        try { data = JSON.parse(text); } catch { data = text; }
      }
      return { status: res.status, headers: res.headers, data };
    }
  }

  const getJson = async (p, opts) => (await request(p, opts)).data;
  const qs = (params) => {
    const s = new URLSearchParams(params).toString();
    return s ? `?${s}` : '';
  };

  /** Top-level items of a collection (or the library when collectionKey is null), paged. */
  async function listTopItems(collectionKey = null, { limit = 100000, start = 0 } = {}) {
    const base = collectionKey ? `/collections/${collectionKey}/items/top` : '/items/top';
    const items = [];
    let cursor = start;
    while (items.length < limit) {
      const page = Math.min(100, limit - items.length);
      const rows = await getJson(`${base}${qs({ limit: page, start: cursor })}`);
      if (!Array.isArray(rows) || !rows.length) break;
      items.push(...rows);
      if (rows.length < page) break;
      cursor += rows.length;
    }
    return items;
  }

  async function listItemsByKeys(keys) {
    const out = [];
    for (let i = 0; i < keys.length; i += 50) {
      out.push(...(await getJson(`/items${qs({ itemKey: keys.slice(i, i + 50).join(',') })}`)));
    }
    return out;
  }

  const listChildren = (key) => getJson(`/items/${key}/children`);
  const getItem = (key, opts) => getJson(`/items/${key}`, opts);

  /**
   * Attach a local PDF as a child of itemKey (Zotero's documented file upload):
   *   1. POST /items            create the imported_file attachment item
   *   2. POST /items/<k>/file   upload authorisation (md5, filename, filesize, mtime)
   *   3. POST <returned url>    upload prefix + file + suffix   (skipped when exists: 1)
   *   4. POST /items/<k>/file   register the upload
   * Returns { attachmentKey, deduped }. A 204 on step 4 is not proof; callers re-read.
   */
  async function attachPdfToItem(itemKey, filePath, { title } = {}) {
    const buf = fs.readFileSync(filePath);
    const filename = path.basename(filePath);
    const md5 = crypto.createHash('md5').update(buf).digest('hex');

    const created = await request('/items', {
      method: 'POST',
      body: [{ itemType: 'attachment', linkMode: 'imported_file', title: title || filename, filename, contentType: 'application/pdf', charset: '', parentItem: itemKey }],
      headers: { 'Zotero-Write-Token': crypto.randomBytes(16).toString('hex') },
    });
    const ok = created.data?.successful?.['0'];
    const attachmentKey = ok?.key || created.data?.success?.['0'];
    if (!attachmentKey) {
      throw new ZoteroError(`Could not create attachment item: ${JSON.stringify(created.data?.failed ?? created.data)}`);
    }

    try {
      const auth = (await request(`/items/${attachmentKey}/file`, {
        method: 'POST',
        form: { md5, filename, filesize: String(buf.length), mtime: String(Date.now()) },
        headers: { 'If-None-Match': '*' },
      })).data;
      if (auth?.exists === 1) return { attachmentKey, deduped: true };
      if (!auth?.url || !auth?.uploadKey) {
        throw new ZoteroError(`Unexpected upload authorisation: ${JSON.stringify(auth)}`);
      }
      const up = await fetch(auth.url, {
        method: 'POST',
        headers: { 'Content-Type': auth.contentType || 'application/octet-stream' },
        body: Buffer.concat([Buffer.from(auth.prefix || ''), buf, Buffer.from(auth.suffix || '')]),
      });
      if (!up.ok) throw new ZoteroError(`File upload to storage failed: HTTP ${up.status}`, { status: up.status });
      await request(`/items/${attachmentKey}/file`, {
        method: 'POST',
        form: { upload: auth.uploadKey },
        headers: { 'If-None-Match': '*' },
      });
      return { attachmentKey, deduped: false };
    } catch (err) {
      // Remove the empty attachment shell so a failed upload leaves nothing behind.
      try {
        const stub = await getItem(attachmentKey);
        await request(`/items/${attachmentKey}`, { method: 'DELETE', version: stub.version });
      } catch { /* keep the original error */ }
      throw err;
    }
  }

  return { libraryURL, headers, request, getJson, listTopItems, listItemsByKeys, listChildren, getItem, attachPdfToItem, env };
}

/** Load .env, pick the (possibly fake) fetch, return a client. */
export async function createClientFromEnv(env = process.env) {
  loadDotEnv(env);
  return createClient({ fetch: await loadFetch(env), env });
}

/** True if any child is a PDF attachment with an uploaded file (md5 present). */
/** A PDF attachment item with no uploaded file (empty md5): a shell left by a failed upload. */
export function hasPdfStub(children) {
  return children.some((c) => c.data?.itemType === 'attachment' && c.data?.contentType === 'application/pdf' && !c.data?.md5);
}

export function hasPdfAttachment(children) {
  return children.some((c) => {
    const d = c.data;
    return d && d.itemType === 'attachment' && d.contentType === 'application/pdf' && Boolean(d.md5) && (d.filesize === undefined || d.filesize > 0);
  });
}
