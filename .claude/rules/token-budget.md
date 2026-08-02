# Token Budget — Route Cheap, Reserve the Strong Model for Judgement

Tokens are money, and with Wren you're spending your own. Run every task on the **cheapest
model + effort that still meets its quality bar**, and reserve the strongest model for
high-consequence reasoning and quality-control gates. The tier definitions live in
`.claude/lib/model-policy.mjs`; this rule is the always-on discipline.

## The tiers

| Tier | Model (alias) | Use for |
|---|---|---|
| **critique** | the strong model (`opus`) | adversarial QC, peer review, methodological/figure critique, gold-standard interpretation, final synthesis |
| **produce** | a mid model (`sonnet`) | drafting, journal formatting, submission prep, document extraction, discovery, figure-design iteration |
| **triage** | the cheap model (`haiku`) | metadata fill, file/draft audits, dedup, first-pass classification, scaffolding |

`effort` (`low`/`medium`/`high`) is a real lever on the strong/mid models — set it to the
task; don't leave everything on `high`. The cheap tier's saving is the cheap model itself.

## The rules

1. **Cheapest tier that meets the bar.** Escalate to the strong model only for critique/QC
   gates. Unsure between two tiers? Pick the cheaper and note it — a QC pass catches an
   under-powered result; an over-powered one just costs more.
2. **Never run bulk or mechanical work on the main (strong) loop.** Metadata fills, dedup,
   first-pass classification, and scaffolding belong in a cheap sub-agent, not the main session.
3. **Isolate heavy reads in sub-agents.** A sub-agent's file reads don't accrue in the main
   context — only its conclusion returns. Fan out searches and document reads; keep the
   expensive synthesis in one place.
4. **Deterministic pre-pass before any model token.** If a script can resolve rote work
   (existence checks, exact-match lookups, arithmetic, format validation), run it first and
   hand the model only what's left.
5. **Set `effort` to the task** — `low`/`medium` for routine, `high` only at QC gates.
6. **Pin a model when you launch an ad-hoc sub-agent.** Built-in search/general agents inherit
   the caller's model — which on the main loop is the strong one. Pass `sonnet` for
   search/reading, `haiku` for pure enumeration; let it inherit the strong model only for
   genuine judgement fan-out. This is the biggest silent leak.

## Measure, don't guess

`python scripts/utils/token_report.py --date today` (or `--since 7`, `--by-agent`) reports
output/input/cache tokens by model and by agent role from your local session logs — so "did
routing actually hold?" is one command, not a guess.

## Why

Wren's whole value is gold-standard rigour, and rigour is expensive per token — so the way to
afford it is to *not spend it where it isn't needed*. Match the spend to the task, do the
mechanical part with scripts, and read each source in its cheapest form once.
