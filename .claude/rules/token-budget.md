# Token Budget — Route Cheap, Reserve the Strong Model for Judgement

Run every task on the **cheapest model + effort that still meets its quality bar**; reserve the strongest for QC gates. Tier definitions live in `.claude/lib/model-policy.mjs`; this rule is the always-on discipline.

| Tier | Model (alias) | Use for |
|---|---|---|
| **critique** | the strong model (`opus`) | adversarial QC, peer review, methodological/figure critique, gold-standard interpretation, final synthesis |
| **produce** | a mid model (`sonnet`) | drafting, journal formatting, submission prep, document extraction, discovery, figure-design iteration |
| **triage** | the cheap model (`haiku`) | metadata fill, file/draft audits, dedup, first-pass classification, scaffolding |

The critique tier is pinned to the `opus` alias in `model-policy.mjs`, so QC gates never silently inherit a cheaper interactive model. `effort` (`low`/`medium`/`high`) is a real lever on the strong/mid models — set it to the task; don't leave everything on `high`.

## The rules

1. **Cheapest tier that meets the bar.** Escalate to the strong model only for critique/QC gates. Unsure between two tiers? Pick the cheaper and note it.
2. **Never run bulk or mechanical work on the main (strong) loop.** Metadata fills, dedup, first-pass classification, and scaffolding belong in a cheap sub-agent.
3. **Isolate heavy reads in sub-agents.** A sub-agent's file reads don't accrue in the main context — only its conclusion returns. Keep the expensive synthesis in one place.
4. **Deterministic pre-pass before any model token.** If a script can resolve rote work (existence checks, exact-match lookups, arithmetic, format validation), run it first and hand the model only what's left.
5. **Set `effort` to the task** — `low`/`medium` for routine, `high` only at QC gates.
6. **Pin a model when you launch an ad-hoc sub-agent.** Built-in search/general agents inherit the caller's model. Pass `sonnet` for search/reading, `haiku` for pure enumeration; inherit the strong model only for genuine judgement fan-out. The `pre-task-model-advisory` hook reminds (non-blocking) when `Explore` or `general-purpose` is launched without a `model`.

Measure, don't guess: `python scripts/utils/token_report.py --date today` (or `--since 7`, `--by-agent`).

**Why:** rigour is expensive per token, so don't spend it where it isn't needed.

Background and examples: docs/rules-history.md.
