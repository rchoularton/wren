/**
 * TEST-ONLY fake fetch for the Zotero scripts. Activated by WREN_FAKE_FETCH=<this file>.
 *
 *   WREN_FAKE_FETCH_FIXTURE=<json>  routes: [{ method?, url|urlRegex, bodyIncludes?, response | sequence }]
 *   WREN_FAKE_FETCH_LOG=<jsonl>     every call is appended: { method, url, headers, body, matched }
 *
 * A response is { status?, headers?, json | text | base64 | bytes }. `bytes: N` yields N bytes
 * starting with "%PDF-". A `sequence` array is consumed one response per call (the last repeats).
 * An unmatched call is logged with matched:false and answered with status 599, so tests can
 * assert that nothing unexpected (and nothing real) was requested.
 */
import fs from 'node:fs';

const fixture = process.env.WREN_FAKE_FETCH_FIXTURE
  ? JSON.parse(fs.readFileSync(process.env.WREN_FAKE_FETCH_FIXTURE, 'utf8'))
  : { routes: [] };
const used = new Map();

function build(spec) {
  const status = spec.status ?? 200;
  const headers = new Headers(spec.headers || {});
  let body = null;
  if (spec.json !== undefined) { body = JSON.stringify(spec.json); if (!headers.has('content-type')) headers.set('content-type', 'application/json'); }
  else if (spec.text !== undefined) body = spec.text;
  else if (spec.base64 !== undefined) body = Buffer.from(spec.base64, 'base64');
  else if (spec.bytes !== undefined) { body = Buffer.alloc(spec.bytes, 0x41); body.write('%PDF-1.4\n'); }
  if (status === 204 || status === 304) body = null;
  return new Response(body, { status, headers });
}

export default async function fakeFetch(url, opts = {}) {
  const method = (opts.method || 'GET').toUpperCase();
  const raw = opts.body;
  const body = raw === undefined ? null : typeof raw === 'string' ? raw : `<binary ${raw.length} bytes>`;
  const route = fixture.routes.findIndex((r) =>
    (r.method || 'GET').toUpperCase() === method &&
    (r.url ? String(url).includes(r.url) : new RegExp(r.urlRegex).test(String(url))) &&
    (!r.bodyIncludes || (typeof raw === 'string' && raw.includes(r.bodyIncludes))));
  const entry = { method, url: String(url), headers: opts.headers || {}, body, matched: route >= 0, route };
  if (process.env.WREN_FAKE_FETCH_LOG) fs.appendFileSync(process.env.WREN_FAKE_FETCH_LOG, JSON.stringify(entry) + '\n');
  if (route < 0) return new Response(`unmatched fake route: ${method} ${url}`, { status: 599 });
  const r = fixture.routes[route];
  const n = used.get(route) || 0;
  used.set(route, n + 1);
  const spec = r.sequence ? r.sequence[Math.min(n, r.sequence.length - 1)] : r.response;
  const res = build(spec);
  Object.defineProperty(res, 'url', { value: spec.finalUrl || String(url) });
  return res;
}
