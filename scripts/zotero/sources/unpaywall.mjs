/**
 * Unpaywall: DOI -> best open-access PDF URL. https://unpaywall.org/products/api
 * Requires a contact email (UNPAYWALL_EMAIL in .env); skipped with a notice when unset.
 */
import { fetchPdf, encodeDoi } from './download.mjs';

export const NAME = 'unpaywall';

export function available(env = process.env) {
  return env.UNPAYWALL_EMAIL
    ? { ok: true }
    : { ok: false, reason: 'UNPAYWALL_EMAIL is not set in .env; skipping Unpaywall' };
}

export async function lookup({ doi }, { fetch = globalThis.fetch, env = process.env } = {}) {
  if (!doi) return { ok: false, reason: 'no_doi' };
  const avail = available(env);
  if (!avail.ok) return { ok: false, skipped: true, reason: avail.reason };

  let meta;
  try {
    const res = await fetch(`https://api.unpaywall.org/v2/${encodeDoi(doi)}?email=${encodeURIComponent(env.UNPAYWALL_EMAIL)}`, { signal: AbortSignal.timeout(20_000) });
    if (!res.ok) return { ok: false, reason: `lookup_failed: HTTP ${res.status}` };
    meta = await res.json();
  } catch (err) {
    return { ok: false, reason: `lookup_failed: ${err.message}` };
  }
  const pdfUrl = meta?.best_oa_location?.url_for_pdf || meta?.oa_locations?.find((l) => l.url_for_pdf)?.url_for_pdf;
  if (!pdfUrl) return { ok: false, reason: 'no_oa_pdf' };
  const dl = await fetchPdf(pdfUrl, { fetch, env });
  if (!dl.ok) return { ok: false, reason: `download_failed: ${dl.reason}`, candidate_url: pdfUrl };
  return { ok: true, source: NAME, buffer: dl.buffer, url: dl.url, license: meta?.best_oa_location?.license || null };
}
