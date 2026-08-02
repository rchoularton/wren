/**
 * Model & effort routing policy — the single source of truth for token-efficient work.
 *
 * The idea (see `.claude/rules/token-budget.md`): run each task on the cheapest model that
 * still meets its quality bar, and reserve the strong model for high-consequence reasoning
 * and quality-control gates. This module names three tiers and maps them to models.
 *
 * TWO kinds of consumer:
 *   1. Claude Code sub-agents / skills — put the ALIAS ('opus' | 'sonnet' | 'haiku') in an
 *      agent's `model:` frontmatter, or pass it when dispatching a sub-agent. The harness
 *      accepts these aliases.
 *   2. Raw Node/SDK scripts that call the Anthropic API directly — the API rejects the
 *      aliases, so use MODEL_IDS (real model IDs) via `modelIdFor()`.
 *
 * Cost posture: critique → the strong model (QC gates, adversarial review, synthesis);
 * produce → a mid model (drafting, extraction, bulk generation that still needs judgement);
 * triage → the cheap model (mechanical, low-ambiguity work). `effort` is a real lever on the
 * strong/mid models — set it to the task rather than leaving everything on 'high'.
 */

// Harness aliases — valid in Claude Code (sub-agent `model:` frontmatter, `claude -p --model`).
// NOT valid as raw API model IDs.
export const ALIASES = { critique: 'opus', produce: 'sonnet', triage: 'haiku' };

// Real API model IDs — for raw @anthropic-ai/sdk callers, which reject the aliases above.
// This object is the ONE place to edit when the model generation changes.
export const MODEL_IDS = {
  opus:   'claude-opus-5',
  sonnet: 'claude-sonnet-5',
  haiku:  'claude-haiku-4-5-20251001',
};

// The tier table. `model` is omitted on `critique` so harness-managed callers INHERIT the
// strong main model rather than pinning a literal — the safe default for a QC gate.
export const TIERS = {
  critique: {                    effort: 'high',   desc: 'high-consequence reasoning / QC gates' },
  produce:  { model: 'sonnet',   effort: 'medium', desc: 'drafting / extraction / bulk w/ judgement' },
  triage:   { model: 'haiku',    effort: 'low',    desc: 'mechanical / low-ambiguity' },
};

/**
 * Route a tier to {model, effort} for a Claude Code sub-agent dispatch.
 * `model` is undefined for `critique` — the harness then inherits the strong main model.
 */
export function routeFor(tier) {
  const t = TIERS[tier];
  if (!t) throw new Error(`model-policy: unknown tier "${tier}"`);
  return { model: t.model, effort: t.effort };
}

/**
 * Resolve a tier to a real API model ID for raw-SDK callers.
 * `critique` (no explicit model) resolves to the strong default (opus).
 */
export function modelIdFor(tier, { strongDefault = 'opus' } = {}) {
  const alias = (TIERS[tier] && TIERS[tier].model) || strongDefault;
  const id = MODEL_IDS[alias];
  if (!id) throw new Error(`model-policy: no MODEL_IDS entry for alias "${alias}"`);
  return id;
}

// Coarse task classifier — a first guess only; always let the caller override.
// Order matters (critique > triage > produce). Stems use \w* so inflected forms match
// ("verify", "validate", "methodological" all hit their stem).
const CRITIQUE_HINTS = /\b(?:qc|quality[- ]control|adversarial|peer[- ]?review|critiqu\w*|methodolog\w*|referee|validat\w*|verif\w*|adjudicat\w*|gold[- ]?standard|rigou?r\w*)/i;
const TRIAGE_HINTS   = /\b(?:metadata|dedup\w*|classif\w*|triage|scaffold\w*|first[- ]?pass|renam\w*|tag(?:ging|s)?\b|reference[- ]?check\w*|citation[- ]?check\w*|list marker|inventory)/i;
const PRODUCE_HINTS  = /\b(?:draft\w*|writ\w*|format\w*|extract\w*|summar\w*|discover\w*|generat\w*|design\w*|prepar\w*|compos\w*|rewrit\w*|translat\w*)/i;

/** Classify a task description into a tier name. Defaults to `produce` (safe middle). */
export function tierFor(taskType = '') {
  const s = String(taskType);
  if (CRITIQUE_HINTS.test(s)) return 'critique';
  if (TRIAGE_HINTS.test(s))   return 'triage';
  if (PRODUCE_HINTS.test(s))  return 'produce';
  return 'produce';
}
