---
name: recall
description: Search the opt-in session logs - "what did we decide about X?" answered with dates and session headings
user-invocable: true
argument-hint: <topic>
---

# Recall - search past session summaries

Answers "what did we decide about X?" from the dated logs written by session
capture (`<auto-memory dir>/context/sessions/YYYY-MM-DD.md`). Read-only.

## Step 0: Is capture on?

Check `tiers.session_capture` in `research-config.yml`. If it is not `true`,
say: "Session capture is off, so there are no logs to search. Enabling
`tiers.session_capture: true` makes one cheap model call per exchange and sends
up to ~6,000 characters of it to the Anthropic API (see
docs/guides/session-memory.md)."
Stop there.

## Step 1: Search

Run the script with 2-5 terms, including likely synonyms (terms are OR-combined,
case-insensitive; logs may use different words than the question):

```bash
bash scripts/utils/recall_context.sh <term> [term ...]
```

If the first search misses, try once more with different terms.

## Step 2: Read around hits

Open the matching `sessions/YYYY-MM-DD.md` and read the whole entry; a single
bullet often lacks the context in its neighbours. Never read raw transcripts.

## Step 3: Answer with citations

- Quote or closely paraphrase the bullets; add nothing.
- Cite date and session heading for every claim: "(2026-11-01, 09:12 - session ab12cd34)".
- Name the source file.

## If nothing matches

Say plainly: "nothing captured matches (searched: <terms>)". Do not reconstruct
an answer from general knowledge. Fallbacks: `papers/{p}/NOTES.md`, the git log.

Logs are summaries, not transcripts; they only cover days capture was on.
