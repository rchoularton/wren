# {{PROJECT_NAME}} — Reference

Load-on-demand detail. The thin core is in [CLAUDE.md](CLAUDE.md).

---

## Memory Architecture

Four layers. Each has a single home and a clear trigger. The boundary rule is: **paper / project state never goes in auto-memory** — it belongs in `papers/{p}/STATUS.md` (and `research_memory/episodic/_internal/` if the corpus add-on is enabled).

### Layer 1 — Behavior rules (`.claude/rules/`)

| | |
|---|---|
| **Path** | `.claude/rules/*.md` |
| **Loaded by** | Claude Code, auto-loaded by `paths:` frontmatter (or always-on if no `paths:`) |
| **Lifecycle** | Promoted from feedback memory when a pattern stabilizes (a correction recurs 2+ times) |
| **Examples** | `rigor.md`, `one-at-a-time.md`, `no-unapproved-tasks.md` (always-on); `outputs.md` (paths-scoped) |

### Layer 2 — Cross-session context (auto-memory)

| | |
|---|---|
| **Path** | `~/.claude/projects/{{MEMORY_SLUG}}/memory/` |
| **Loaded by** | Claude Code, auto-loads `MEMORY.md` (≤200 lines) at session start |
| **What belongs** | User profile & preferences, durable cross-cutting feedback, dated learnings, pointers to where things live |
| **What does NOT belong** | Paper-specific or project-specific state; active behavior rules (those go in `.claude/rules/`) |
| **Format** | One fact per file with frontmatter (`name`, `description`, `metadata.type` ∈ user/feedback/project/reference); one index line per fact in `MEMORY.md` |

**The capture → index → promote loop:** `/retro` writes a dated `learning_*.md`; a fact gets a one-line entry in `MEMORY.md`; when a feedback memory recurs, promote it into a `.claude/rules/*.md` rule and archive the original.

### Layer 3 — Corpus memory (`research_memory/`) — optional add-on

| | |
|---|---|
| **Path** | `research_memory/` |
| **Schema** | `research_memory/config.json` |
| **Sub-layers** | `episodic/_external/` (one note per literature source), `episodic/_internal/{papers,country,special}/` (rolling per-artifact state), `semantic/` (themes, gaps, contradictions, questions), `reflections/` |
| **What belongs** | All paper / project state; per-source findings; cross-corpus synthesis |

The internal artifact files are the **single source of truth** for paper state.

### Layer 4 — Paper deep work (`papers/{p}/`)

| File | Purpose | Write trigger |
|------|---------|---------------|
| `STATUS.md` | Phase/status dashboard with YAML frontmatter | Phase transitions, freezes |
| `NOTES.md` | Long-form analytical history, dated newest-on-top | After analysis (Research Note Capture) |
| `METHODS_LOG.md` | Methods decisions and pre-registration | Each methods choice |
| `PLAN.md` | Forward-looking task plan | Phase planning |

### Boundary decision tree

When you have something to record, ask:

1. **A behavioral rule that should auto-fire?** → `.claude/rules/`
2. **About a specific paper / project?** → `papers/{p}/STATUS.md` (+ `NOTES.md` for long-form; + `research_memory/episodic/_internal/` if enabled)
3. **A finding from a literature source?** → `research_memory/episodic/_external/` (usually automated)
4. **Cross-cutting context about the user, the project, or how to work?** → auto-memory
5. **A phase transition or status change?** → `papers/{p}/STATUS.md`

If it fits in two places, the deeper / more specific home wins (3 > 2 > 1).

---

## Paper Organization — the 14-phase pipeline

Each paper moves through phases tracked in `STATUS.md` frontmatter (`phase: N`):

1. Scoping  2. Data inventory  3. Exploratory analysis  4. Methods design
5. Analysis build  6. QC review (`/qc-team`)  **7. Gold Standard freeze (`/gold-standard`) ← no drafting before this**
8. Drafting (`/draft`)  9. Figures (`/figure`)  10. Internal review  11. QC of draft
12. Submission prep (`/cover-letter`)  13. Peer review response (`/revision-response`)  14. Publication

**Phase 7 is the critical gate.** Analysis must be verified, git-tagged, and archived as canonical before any prose is written. This prevents drafting on numbers that later change.

### Per-paper template

`papers/{id}/` contains `STATUS.md`, `PLAN.md`, `METHODS_LOG.md`, `NOTES.md`, `config.json`, and `drafts/ figures/ outputs/ reviews/ gold_standard/`. Duplicate `papers/example-paper/` to start a new one.

`STATUS.md` frontmatter shape:
```yaml
---
paper_id: my-paper
title: "…"
journal: "{{JOURNAL_DEFAULT}}"
phase: 1
tier: 2
status: scoping
tags: [paper]
aliases: ["My Paper"]
---
```

---

## Data & Reference Layer

- **Database:** backend chosen in `research-config.yml` (`database.backend`). Tiers: `files` (default), `sqlite`/`duckdb`, `directus-local` (Docker), `managed`. See `docs/database.md`.
- **References:** `references.provider` — `bibtex` (universal, reads `{{BIBTEX_PATH}}`), `zotero` (MCP), or `mendeley` (via .bib export). See `docs/integrations.md`.
- **Add MCP servers as needed:** enable connector blocks in `.mcp.json.template` via config, or add your own. Secrets go in `.env` as `${VARS}` — never inline.

---

## Ambient Notifications

Long-running scripts (>2 min) post desktop notifications and append to `RUNNING.md` via `scripts/utils/notify.py` (Python) or `scripts/utils/notify.sh` (shell). Notifications use `terminal-notifier` on macOS and degrade to log-only elsewhere.

```python
from scripts.utils.notify import notify_run
with notify_run("my_script", detail="scope=baseline"):
    ...  # long-running work
```

For jobs the assistant spawns that run >30s, prefer `run_in_background: true` + the `Monitor` tool over polling `RUNNING.md`.

---

## Model Selection (sub-agents)

Set `model:` per sub-agent in `.claude/agents/*.md`. Rough tiers: routine/mechanical → haiku; standard drafting/analysis → sonnet; adversarial review, synthesis, hard reasoning → opus. Omit to inherit the session model.
