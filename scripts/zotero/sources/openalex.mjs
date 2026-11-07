/**
 * OpenAlex: DOI -> open_access.oa_url / primary_location.pdf_url / any location.pdf_url.
 * https://docs.openalex.org/ - free, no key. UNPAYWALL_EMAIL, when set, is sent as the polite-pool mailto.
 */
import { fetchPdf, encodeDoi } from './download.mjs';

export const NAME = 'openalex';

export async function lookup({ doi }, { fetch = globalThis.fetch, env = process.env } = {}) {
  if (!doi) return { ok: false, reason: 'no_doi' };
  let work;
  try {
    const mailto = env.UNPAYWALL_EMAIL ? `?mailto=${encodeURIComponent(env.UNPAYWALL_EMAIL)}` : '';
    const res = await fetch(`https://api.openalex.org/works/doi:${encodeDoi(doi)}${mailto}`, { signal: AbortSignal.timeout(20_000) });
    if (!res.ok) return { ok: false, reason: `lookup_failed: HTTP ${res.status}` };
    work = await res.json();
  } catch (err) {
    return { ok: false, reason: `lookup_failed: ${err.message}` };
  }
  const candidates = [work?.open_access?.oa_url, work?.primary_location?.pdf_url, ...(work?.locations || []).map((l) => l?.pdf_url)].filter(Boolean);
  const unique = [...new Set(candidates)];
  for (const url of unique) {
    const dl = await fetchPdf(url, { fetch, env });
    if (dl.ok) {
      return { ok: true, source: NAME, buffer: dl.buffer, url: dl.url, license: work?.primary_location?.license || work?.open_access?.license || null };
    }
  }
  return { ok: false, reason: unique.length ? `all_candidates_failed (${unique.length} tried)` : 'no_pdf_url_in_metadata' };
}
