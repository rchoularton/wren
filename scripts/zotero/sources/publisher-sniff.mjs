/**
 * Publisher landing-page sniff: resolve doi.org, read <meta name="citation_pdf_url"> only,
 * then download that URL. No other scraping.
 */
import { fetchPdf, encodeDoi, userAgent } from './download.mjs';

export const NAME = 'publisher-sniff';

export function extractCitationPdfUrl(html) {
  if (!html) return null;
  for (const tag of html.match(/<meta\b[^>]*>/gi) || []) {
    if (!/name=["']citation_pdf_url["']/i.test(tag)) continue;
    const m = tag.match(/content=["']([^"']+)["']/i);
    if (m) return m[1];
  }
  return null;
}

export async function lookup({ doi }, { fetch = globalThis.fetch, env = process.env } = {}) {
  if (!doi) return { ok: false, reason: 'no_doi' };
  let html, landing;
  try {
    const res = await fetch(`https://doi.org/${encodeDoi(doi)}`, {
      redirect: 'follow',
      signal: AbortSignal.timeout(30_000),
      headers: { 'User-Agent': userAgent(env), Accept: 'text/html,application/xhtml+xml' },
    });
    if (!res.ok) return { ok: false, reason: `landing_failed: HTTP ${res.status}` };
    html = await res.text();
    landing = res.url || `https://doi.org/${doi}`;
  } catch (err) {
    return { ok: false, reason: `landing_failed: ${err.message}` };
  }
  const href = extractCitationPdfUrl(html);
  if (!href) return { ok: false, reason: 'no_citation_pdf_url_meta' };
  let pdfUrl;
  try { pdfUrl = new URL(href, landing).toString(); } catch { pdfUrl = href; }
  const dl = await fetchPdf(pdfUrl, { fetch, env });
  if (!dl.ok) return { ok: false, reason: `download_failed: ${dl.reason}`, candidate_url: pdfUrl };
  return { ok: true, source: NAME, buffer: dl.buffer, url: dl.url, license: null };
}
