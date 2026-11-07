/**
 * Shared PDF fetcher for the source plugins.
 * Returns { ok: true, buffer, url } or { ok: false, reason }.
 * A valid PDF starts with the %PDF magic bytes and is at most MAX_BYTES (50 MB).
 */
export const MAX_BYTES = 50 * 1024 * 1024;
const TIMEOUT_MS = 60_000;

export function userAgent(env = process.env) {
  const mail = env.UNPAYWALL_EMAIL;
  return mail ? `wren-pdf-fill/1.0 (mailto:${mail})` : 'wren-pdf-fill/1.0';
}

export async function fetchPdf(url, { fetch = globalThis.fetch, env = process.env, maxBytes = MAX_BYTES } = {}) {
  if (!url) return { ok: false, reason: 'no_url' };
  try {
    const res = await fetch(url, {
      redirect: 'follow',
      signal: AbortSignal.timeout(TIMEOUT_MS),
      headers: { 'User-Agent': userAgent(env), Accept: 'application/pdf,*/*' },
    });
    if (!res.ok) return { ok: false, reason: `http_${res.status}` };
    const declared = Number(res.headers.get('content-length'));
    if (Number.isFinite(declared) && declared > maxBytes) {
      return { ok: false, reason: `too_large (${declared} bytes, cap ${maxBytes})` };
    }
    const chunks = [];
    let total = 0;
    const reader = res.body.getReader();
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.length;
      if (total > maxBytes) {
        await reader.cancel();
        return { ok: false, reason: `too_large (over ${maxBytes} bytes)` };
      }
      chunks.push(value);
    }
    const buffer = Buffer.concat(chunks);
    if (buffer.subarray(0, 4).toString('latin1') !== '%PDF') {
      return { ok: false, reason: 'not_pdf (missing %PDF magic bytes)' };
    }
    return { ok: true, buffer, url: res.url || url };
  } catch (err) {
    return { ok: false, reason: err.message };
  }
}

/** Encode a DOI for a URL path, keeping "/" raw. */
export function encodeDoi(doi) {
  return encodeURIComponent(doi).replace(/%2F/gi, '/');
}
