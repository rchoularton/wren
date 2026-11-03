# Rules history

The always-on rules in `.claude/rules/` are kept short because they load into every session. The rationale, history and worked examples that used to sit inside them live here. Nothing here adds or relaxes a requirement; the rule files are authoritative. See [Concepts](concepts.md) for where rules sit in the memory model, and run `npm run context:size` to see what each source costs.

## always-run-the-check

- **Aside claims.** A throwaway claim ("this record is the right one", "the citation is at reference 41") is still a claim. An unchecked aside carries the same weight as a checked claim to the reader, so it is where unverified errors enter.
- **The failure the read/write split stops.** "Shall I confirm the record and apply the fix?" bundles a read that needed no permission with a write that did. Ask about the write only.
- **Success codes.** Some services silently ignore a field that is invalid for the record type: the write returns success and nothing changes.
- **Why it matters.** Running the check costs little; a wrong assertion in a validated output costs a lot.
- **How to apply.** Before stating a fact, ask whether you checked it or are recalling it. Before a write, ask whether it is already a recorded decision. After a write, re-read the value.

## gold-standard

- **Tag convention.** `{id}-gold-v{n}`, for example `{id}-gold-v1`.
- **Decimal versions.** `v3.1` or `v3.2` is by construction a patch to v3 rather than a new version, which is the pattern the rule exists to stop.
- **Why.** A result is only as reproducible as the version it cites. Edits to a frozen artifact make the citation point at something other than what was checked. Integer versions with written rationales keep every result traceable to the exact state that produced it.
- **Archiving.** Every freeze is kept; superseded freezes are archived in place so live and historical artifacts are distinguishable at a glance.

## no-unapproved-tasks

- **Why.** Unapproved tasks create scope creep, waste the user's time and tokens, and erode trust in the task list as a faithful record of agreed work.
- **How to apply.** Separate agreed work from ideas. Ideas are asked about, one at a time (see `one-at-a-time`). Agreed work is recorded. Before listing anything, check: did a referee or editor mandate it, or did the user explicitly approve it?

## one-at-a-time

- **Why.** The user applies each change (in Word, in code) and reviews it before moving to the next. Dumping multiple items into one window breaks focus and wastes time. Batching many items and then asking for one bulk agreement invites context drift, lets the assistant make assumptions, and creates rework that wastes both time and tokens.
- **Default cadence.** Present item, stop, wait for "next" or feedback, present the next item. Keep each message scoped to a single item. When in doubt, present less.
- **Pre-approval.** A blanket sign-off means the direction is agreed; it does not mean the assistant should present items in bulk or auto-advance through them.

## outputs

- **Why no `*_v2/` directories.** Organic version growth produces duplicated datasets and version-ambiguous directories that are painful to clean up later.
- **Archive example.** `figures/` becomes `figures_archived_2026-11-02/`, and the new version reuses the name `figures/`.

## reviewer-response-prose

No rationale was removed from this rule; the full text stays in the rule file.

## rigor

- **Rule 1, why.** The system is built on gold-standard research rigor, and skipping steps or assuming answers undermines the whole approach. Build on existing work, not instead of it.
- **Rule 2, why.** High-consequence academic QC: fabricated observations lead to incorrect methodological conclusions.
- **Rule 4, background.** Earlier exploration was often at a different resolution, on partial data, or from an outdated extraction.
- **Rule 5, why.** A competent-looking shortcut is worse than no answer, because it hides the gap. The system's value is gold-standard rigor.
- **Enforcement.** For `/peer-review` and `/qc-team` this is enforced structurally: the `post-agent-review-gate` hook blocks a verdict when a required prior-stage file is missing; a missing comparative analysis only warns, so a skipped Stage 2 is surfaced rather than silent.

## token-budget

- **Why.** Rigour is expensive per token, so the way to afford it is to not spend it where it isn't needed.
- **Model routing.** Match the spend to the task, do the mechanical part with scripts, and read each source in its cheapest form once.
- **Rule 6, background.** Built-in search and general agents inherit the caller's model, which on the main loop is the strong one. This is the biggest silent leak.
- **Rule 3, instruction.** A sub-agent's file reads don't accrue in the main context, so fan out searches and document reads while keeping the synthesis in one place.

## tooling

- **Why terminal-first.** A researcher who can just ask the assistant shouldn't have to go browse a separate app. If you personally want a dashboard, that's a preference: build it, but don't file it as a system improvement the assistant should push.
- **Editor visibility.** Users often run Claude Code inside an editor extension where Read-tool output and plan-file contents are not rendered in the chat view.

## wren-voice

- **Whose voice.** Wren's voice is distinct from the author's and the paper's. Wren is the research assistant reporting evidence to researchers; it is not the lead author.
- **Why.** Wren's findings are read by researchers who act on them. A calibrated voice lets them tell a verified result from a reading of one.
- **How to apply.** Before sending a findings report, check that every number is tied to a referent and a source, that each claim is pitched at the confidence the evidence supports, that no figure detail was left unverified, and that the text is Wren's own rather than text authored in the user's name.
- **Examples of calibrated phrasing.** Established: "the data show…". A reading: "one interpretation is…", "tentatively,…". Open: "the data don't distinguish between X and Y".
