/**
 * Crossref work -> Zotero item, typed by the work's own Crossref `type`.
 *
 * Why: treating every DOI as a journalArticle files a book chapter as a journal
 * article, with the book series in the journal field and no book title. Crossref
 * says what the work is, so the item type follows Crossref's `type`.
 *
 * Only fields valid for the target Zotero item type are set. The Zotero API rejects
 * a create that carries a field the type does not have (for example publicationTitle
 * on a bookSection). The per-type field lists used to check this are kept as test
 * data in tests/data/zotero-type-fields.json (from api.zotero.org/itemTypeFields).
 *
 * Network access goes through an injectable fetch so tests can fake Crossref.
 */

export const CROSSREF_TO_ZOTERO_TYPE = {
  'journal-article': 'journalArticle',
  'posted-content': 'preprint',
  'proceedings-article': 'conferencePaper',
  'report': 'report',
  'report-component': 'report',
  'book-chapter': 'bookSection',
  'book-section': 'bookSection',
  'book-part': 'bookSection',
  'book': 'book',
  'monograph': 'book',
  'edited-book': 'book',
  'reference-book': 'book',
};

/** Lower-case a DOI and strip resolver prefixes ("https://doi.org/", "doi:"). */
export function normaliseDoi(s) {
  if (!s || typeof s !== 'string') return '';
  return s.trim().toLowerCase()
    .replace(/^https?:\/\/(dx\.)?doi\.org\//, '')
    .replace(/^doi:\s*/, '')
    .replace(/[\s.,;)]+$/, '');
}

/**
 * Fetch a Crossref work by DOI. Returns the `message` object, or null on any failure
 * (network error, non-200, malformed body). `mailto` joins the User-Agent so Crossref
 * routes the request to its polite pool.
 */
export async function fetchCrossrefWork(doi, { fetch = globalThis.fetch, mailto = '', timeoutMs = 15000, warn = console.error } = {}) {
  const clean = normaliseDoi(doi);
  if (!clean) return null;
  try {
    const res = await fetch(`https://api.crossref.org/works/${encodeURIComponent(clean)}`, {
      headers: { 'User-Agent': `Wren/1.0 (https://github.com/rchoularton/wren${mailto ? `; mailto:${mailto}` : ''})` },
      signal: AbortSignal.timeout(timeoutMs),
    });
    if (!res.ok) {
      warn(`  (Crossref lookup failed for ${clean}: HTTP ${res.status})`);
      return null;
    }
    const body = JSON.parse(await res.text());
    return body?.message || null;
  } catch (err) {
    warn(`  (Crossref lookup failed for ${clean}: ${err.message})`);
    return null;
  }
}

// Crossref text fields carry HTML entities ("Food &amp; Agriculture").
const ENTITIES = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' };
function decodeEntities(s) {
  return String(s || '').replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, e) => {
    if (e[0] === '#') return String.fromCodePoint(e[1].toLowerCase() === 'x' ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10));
    return ENTITIES[e.toLowerCase()] ?? m;
  });
}

const first = (v) => decodeEntities((Array.isArray(v) ? v[0] : v) || '');
const last = (v) => decodeEntities((Array.isArray(v) ? v[v.length - 1] : v) || '');

function toCreators(people, creatorType) {
  return (people || [])
    .map((p) => (p.family
      ? { creatorType, firstName: (p.given || '').trim(), lastName: p.family.trim() }
      : { creatorType, name: (p.name || '').trim() }))
    .filter((c) => c.lastName || c.name);
}

function dateOf(w) {
  const parts = w.issued?.['date-parts']?.[0]
    || w['published-online']?.['date-parts']?.[0]
    || w['published-print']?.['date-parts']?.[0]
    || [];
  return parts.filter((n) => n != null)
    .map((n, i) => (i === 0 ? String(n) : String(n).padStart(2, '0')))
    .join('-');
}

function abstractOf(w) {
  return decodeEntities((w.abstract || '').replace(/<[^>]+>/g, ' '))
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/^Abstract\s+/i, '');
}

/**
 * Build Zotero item data (no tags/collections) from a Crossref work.
 * Returns null when the Crossref type has no mapping, so the caller can fall
 * back to its own metadata rather than guess.
 */
export function crossrefWorkToZoteroItem(w) {
  const itemType = CROSSREF_TO_ZOTERO_TYPE[w?.type];
  if (!itemType) return null;

  const subtitle = first(w.subtitle);
  const title = [first(w.title), subtitle].filter(Boolean).join(': ');
  const containers = Array.isArray(w['container-title']) ? w['container-title'].filter(Boolean).map(decodeEntities) : [];
  const publisher = decodeEntities(w.publisher);
  const isbn = (w.ISBN || []).join(' ');

  const item = {
    itemType,
    title,
    creators: [...toCreators(w.author, 'author'), ...toCreators(w.editor, 'editor')],
    abstractNote: abstractOf(w),
    date: dateOf(w),
    DOI: w.DOI || '',
    url: w.URL || '',
    language: w.language || '',
    libraryCatalog: 'Crossref',
  };

  switch (itemType) {
    case 'journalArticle':
      Object.assign(item, {
        publicationTitle: first(containers),
        volume: w.volume || '',
        issue: w.issue || '',
        pages: w.page || '',
        ISSN: (w.ISSN || []).join(' '),
        publisher,
      });
      break;
    case 'bookSection':
      // When Crossref gives two containers for a chapter they are series first,
      // book last.
      Object.assign(item, {
        bookTitle: last(containers),
        series: containers.length > 1 ? first(containers) : '',
        publisher,
        pages: w.page || '',
        ISBN: isbn,
      });
      break;
    case 'book':
      Object.assign(item, { series: first(containers), publisher, ISBN: isbn });
      break;
    case 'report':
      Object.assign(item, { institution: publisher, seriesTitle: first(containers), pages: w.page || '', ISBN: isbn });
      break;
    case 'conferencePaper':
      Object.assign(item, {
        proceedingsTitle: last(containers),
        conferenceName: w.event?.name || '',
        publisher,
        volume: w.volume || '',
        pages: w.page || '',
        ISBN: isbn,
      });
      break;
    case 'preprint':
      Object.assign(item, { repository: decodeEntities(w.institution?.[0]?.name) || publisher });
      break;
  }
  return item;
}
