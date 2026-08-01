---
name: revision-response
description: Structure a point-by-point response to peer reviewer comments for a journal revision
user-invocable: true
argument-hint: [paper-id]
---

# Revision Response

Structure a point-by-point response to journal reviewer comments. Organizes the revision systematically, tracking which comments require text changes, new analysis, or rebuttal. Post-submission phase.

## Usage

```bash
/revision-response example-paper                 # Start response document
/revision-response example-paper --reviewer 2    # Focus on a specific reviewer
```

## Workflow

### Step 1: Gather materials

1. Read `papers/{id}/STATUS.md` for submission details.
2. Read `papers/{id}/config.json` for the target journal (falls back to `research-config.yml` `journals.default`).
3. Ask the user to provide the reviewer comments (paste them or give a file path in `papers/{id}/reviews/`).
4. Read the submitted manuscript in `papers/{id}/drafts/`.
5. Read the frozen outputs in `papers/{id}/gold_standard/` for any data verification the response will need.

### Step 2: Parse reviewer comments

Extract and categorize each comment:

| # | Reviewer | Type | Summary | Effort |
|---|----------|------|---------|--------|
| 1 | R1 | Major | Requests an additional robustness check | High |
| 2 | R1 | Minor | Typo in Table 2 | Low |
| 3 | R2 | Major | Questions a threshold selection | Medium |
| 4 | Editor | Structural | Requests a shortened introduction | Medium |

**Comment types:**
- **Major** — Requires new analysis, significant rewriting, or methodological justification.
- **Minor** — Small corrections, clarifications, formatting.
- **Structural** — Reorganization, length changes.
- **Positive** — Praise (acknowledge but no action needed).

### Step 3: Triage

Present comments grouped by effort and ask the user to confirm the approach for each. Present them **one at a time** and wait for a decision before the next (`.claude/rules/one-at-a-time.md`).

**High effort (may require new analysis):**
- Comment R1.1: "Additional robustness check..." → Run a sensitivity analysis?
- Comment R2.3: "Compare against an alternative approach..." → New analysis needed?

**Medium effort (rewriting / justification):**
- Comment R2.1: "Justify the threshold selection..." → Expand the methods section?

**Low effort (corrections):**
- Comment R1.2: "Typo in Table 2" → Fix directly.

Do not add scope beyond the comments and the user's approved approach (`.claude/rules/no-unapproved-tasks.md`).

### Step 4: Draft the response document

Draft every answer to the **canonical standard in
[`.claude/rules/reviewer-response-prose.md`](../../rules/reviewer-response-prose.md)** (read it
before drafting). Each answer follows the five-part structure — verbatim reviewer quote →
formal acknowledgement → one-or-two-sentence overall response → detailed academic prose →
a concise bulleted "Changes made" change-log (the only place shorthand is allowed).
Depth is proportionate to the comment (full structure for Major/Moderate; brief but
still formal prose for Minor). Write in complete academic prose, not shorthand.

```markdown
# Response to Reviewers — {id}

**Manuscript:** {title}
**Journal:** {journal}
**Submission Date:** {date}

---

## Response to Reviewer 1

### Comment R1.1 (Major)
> [Exact reviewer quote — verbatim, abridged with […] if long; never paraphrased]

We thank the reviewer for [recognise the point]. [Overall response: one or two
sentences on how we address it.]

[Detailed response in academic prose — what, why, and the evidence. Work through
sub-points in their own short paragraphs. Defend any decline with evidence.]

**Changes made:**
- `[n]` / Section / Table: [location of change]
- New display item / file path: [analysis or display item added]

---

### Comment R1.2 (Minor)
> [Exact reviewer quote]

We thank the reviewer for catching this; we have corrected it. [Brief formal prose —
one or two sentences. No bare shorthand.]

**Changes made:**
- `[n]`: changed "X" to "Y".
```

### Step 5: Track changes

Maintain a changes checklist:

| # | Comment | Status | Manuscript Change | New Analysis |
|---|---------|--------|-------------------|--------------|
| R1.1 | Robustness check | [ ] | Section 3.2 | sensitivity script |
| R1.2 | Typo | [x] | Table 2 | — |
| R2.1 | Threshold justification | [ ] | Methods 2.3 | — |

### Step 6: Save and next steps

1. Save the response to `papers/{id}/reviews/revision_response_v{N}.md`.
2. Save the changes checklist to `papers/{id}/reviews/revision_checklist.md`.
3. Update `papers/{id}/STATUS.md` with the revision phase.
4. If new analysis is needed:
   - Warn: "New analysis required — this will break the gold standard freeze."
   - Suggest: "Run new analysis → QC → re-freeze with `/gold-standard` → update the draft with `/draft`."

## Response writing guidelines

**The canonical standard is [`.claude/rules/reviewer-response-prose.md`](../../rules/reviewer-response-prose.md)** —
read it before drafting or editing any answer. In summary:

- **Quote the reviewer verbatim** — never paraphrase the comment.
- **Open formal and deferential, then confident** — acknowledge the point, then state
  plainly what was done and why; defend declines with evidence; never dismiss.
- **Write in complete academic prose, not shorthand** — bullets only in "Changes made".
- **Be specific and quantitative** — exact figures, indicator names, location anchors `[n]`.
- **Match depth to the comment** — full structure for Major/Moderate; brief formal prose for Minor.
- **Reference the frozen gold standard outputs** for any data claim (`.claude/rules/rigor.md`).
- **Must not read as AI-written** — no em-dashes, no formulaic connectives, varied rhythm;
  follow the anti-AI checklist in `.claude/rules/reviewer-response-prose.md` as a finishing pass
  over the full document before resubmission.

## When done

Update the STATUS.md phase history.
Re-read the response document against `.claude/rules/reviewer-response-prose.md` and address any flags.
Ask about saving session notes to the paper's notes.
