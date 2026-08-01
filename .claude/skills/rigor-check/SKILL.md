---
name: rigor-check
description: Mid-task self-audit against the research rigor rules - catches context drift, shortcuts, and unjustified assumptions during long sessions
user-invocable: true
---

# Rigor Check

A mid-task self-audit. Run this partway through a long analysis or writing session to catch drift before it compounds.

## What to do

Read `.claude/rules/rigor.md` and honestly audit the current session against each rule. For each, state ✓ (holding) or ⚠ (slipping), with one concrete line of evidence from *this* session:

1. **Read existing work first** — did you open and read what already existed, or start building a parallel version / assume its contents?
2. **No embellished figure descriptions** — is every value or feature you've stated about a figure actually verified from the data?
3. **Only frozen pipelines are canonical** — have you presented any un-frozen exploratory result as if it were validated?
4. **No building on stale exploration** — did you reuse an earlier output without checking it matches the current resolution / variables / case universe?
5. **Full defined process, no silent shortcuts** — did any skill or workflow you ran skip a stage? Did you present a headline verdict as if the full process backed it?

Also check the always-on rules: did you batch multiple items into one message (`one-at-a-time.md`)? Did you add any unapproved task to a list (`no-unapproved-tasks.md`)?

## Output

A short report: which rules are holding, which are slipping, and the specific corrective action for each ⚠. If everything is clean, say so in one line and continue. If something slipped, propose the fix and wait for the user before proceeding.
