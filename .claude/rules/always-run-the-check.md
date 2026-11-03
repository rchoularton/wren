---
description: Verify before asserting, including asides. Read and verify without asking; ask before writing shared state. Always on.
---

# Always Run the Check

If a check would settle a question, **run it**. Do not state an unverified claim, and do not ask permission to verify.

## 1. Verify before asserting — always

Every factual claim with a resolvable source gets checked before it is stated: reference metadata (Crossref, OpenAlex, the primary PDF), a record in the reference library, file contents, line numbers, computed values, what a document or codebase contains, what a URL actually serves.

This applies to **asides and supporting details**, not just headline findings. A throwaway claim ("this record is the right one", "the citation is at reference 41") is still a claim. If it bears on a decision, check it first.

Where a check genuinely cannot be run, say so explicitly and label the claim unverified. Never let it read as established. When a check overturns your own earlier statement, correct it openly in the record.

## 2. Split verification from mutation

These are different questions and must never be bundled:

| Action | Behaviour |
|---|---|
| **Read / verify**: lookups, resolving a record, fetching a source, reading a file, running a search | **Do it. Never ask.** Report the result. |
| **Write**: a reference-library entry, a manuscript, a frozen artifact, a metadata update, any shared state | **Ask**, unless the change is already an approved decision (see §3). |

The failure this rule exists to stop: "Shall I confirm the record and apply the fix?" bundles a read that needed no permission with a write that did. Ask about the write only.

## 3. Recorded decisions are standing approval for the write

Where the user has already approved a change and it is recorded as an `AUTHOR DECISION` line in the paper's files, **apply it without asking again.** Apply recorded decisions one write per message, per `one-at-a-time.md`, unless the user asked for all at once. Report each write with its before and after, and confirm the value landed by re-reading it.

This does not extend scope. Apply exactly what was decided, nothing adjacent. Anything beyond the recorded decision is a new item and needs approval (see `no-unapproved-tasks.md`).

## 4. A success code is not proof

An API write that returns success is not evidence the field changed. Some services silently ignore a field that is invalid for the record type: the write returns success and nothing changes. Always verify a write by re-reading the record and comparing the value to what you intended.

## Why

An unchecked aside carries the same weight as a checked claim to the reader, so it is where unverified errors enter. Running the check costs little; a wrong assertion in a validated output costs a lot.

## How to apply

Before stating a fact, ask: did I check it, or am I recalling it? If recalled, run the check or label it unverified. Before a write, ask: is this already a recorded decision? If not, ask first. After a write, re-read the value.

Related: `rigor.md` (no assumptions, no silent shortcuts), `wren-voice.md` (how verified and unchecked claims are worded).
