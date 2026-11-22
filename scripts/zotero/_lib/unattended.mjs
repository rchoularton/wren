/**
 * Unattended-run helpers shared by the Zotero scripts.
 *
 * isUnattended(env): fail closed. WREN_UNATTENDED counts as set unless it is empty (or whitespace),
 * or one of 0 / false / no (any case). Anything else, including a typo, means unattended.
 *
 * resolveInside(target, base): resolve `target` (symlinks and ".." included, even for a file that does
 * not exist yet) and return it only if it lies inside `base`; otherwise return null.
 */
import fs from 'node:fs';
import path from 'node:path';

export function isUnattended(env = process.env) {
  const v = env.WREN_UNATTENDED;
  if (v === undefined || v === null) return false;
  return !['', '0', 'false', 'no'].includes(String(v).trim().toLowerCase());
}

/** realpath of the deepest existing ancestor, with the not-yet-existing tail appended. */
export function realResolve(p) {
  let cur = path.resolve(p);
  const tail = [];
  for (;;) {
    try { return path.join(fs.realpathSync(cur), ...tail.reverse()); } catch { /* keep climbing */ }
    const parent = path.dirname(cur);
    if (parent === cur) return path.join(cur, ...tail.reverse());
    tail.push(path.basename(cur));
    cur = parent;
  }
}

export function resolveInside(target, base) {
  const t = realResolve(target);
  const b = realResolve(base);
  return t === b || t.startsWith(b + path.sep) ? t : null;
}

/** Output-path policy: always inside the project root; when unattended, inside <root>/outputs/librarian. */
export function checkOutputPath(target, root, label, env = process.env) {
  if (isUnattended(env)) {
    if (!resolveInside(target, path.join(root, 'outputs', 'librarian'))) {
      throw new Error(`refused: unattended run may only write inside outputs/librarian/ (${label}: ${target})`);
    }
  } else if (!resolveInside(target, root)) {
    throw new Error(`refused: ${label} must be inside the project root (${target})`);
  }
}
