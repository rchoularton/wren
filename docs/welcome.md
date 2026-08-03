# Welcome to Wren

New here? Open your project in Claude Code and run:

```
/setup wren
```

That starts a guided onboarding — a short tour, a few questions about your research, the
right tools set up to match, and your first paper — so you leave with real momentum
instead of a blank page. This page is the same tour in written form; read it here or let
`/setup wren` walk you through it.

Wren is an agentic research assistant for [Claude Code](https://claude.com/claude-code).
You drive everything from the terminal by asking; there is nothing else to open, and
nothing external is required to start.

---

## 1. A memory that persists

Wren keeps context in a **four-layer memory model**, each layer with one home so nothing
lands in the wrong place:

1. **Behaviour rules** (`.claude/rules/`) — always-on guidance the assistant follows.
2. **Cross-session context** (`~/.claude/projects/.../memory/`) — who you are, durable
   preferences, and dated learnings, loaded at the start of every session.
3. **Corpus memory** (`research_memory/`, optional add-on) — findings across your
   literature and projects, queryable with `/research-memory`.
4. **Per-paper deep work** (`papers/{id}/`) — each paper's status, notes, and methods log.

The rule of thumb: paper and project state lives with the paper, never in general memory.
Full detail in [Concepts → the four-layer memory model](concepts.md#the-four-layer-memory-model).

## 2. The 14-phase pipeline and the gold-standard gate

Every paper moves through **14 phases**, tracked in its `STATUS.md` (`phase: N`), from
scoping through data, analysis, drafting, review, and publication.

**Phase 7 is the gate: the gold-standard freeze.** Before you write a word of prose, the
analysis is verified, git-tagged, and archived as canonical. That is the discipline that
stops you drafting on numbers that later change — run `/gold-standard` to do it. See the
full pipeline diagram in [Concepts → the 14-phase pipeline](concepts.md#the-14-phase-paper-pipeline).

## 3. The skills

Type these as slash commands once your project is open. All 18 ship in the box —
[full reference](skills.md).

- **Orient & manage** — `/research`, `/paper`, `/setup`
- **Write & submit** — `/draft`, `/cover-letter`, `/revision-response`, `/peer-review`
- **Discover** — `/literature-scan`
- **Rigor & memory** — `/gold-standard`, `/rigor-check`, `/research-memory`, `/retro`

## 4. Audit, QC, and peer review

The rigor gates that keep the research honest:

- **`/gold-standard`** — freeze and verify an analysis as canonical (the Phase 7 gate).
- **`/peer-review`** — an agentic reviewer that evaluates a draft against its target
  journal's guidelines in four stages, and scores it.
- **`/rigor-check`** — a mid-session self-audit that catches drift, shortcuts, and
  unjustified assumptions during long working sessions.

Two more are **planned, not yet shipped**: `/qc-team` (adversarial QC of a draft, phases
6 and 11) and `/figure` (figure design and critique, phase 9). Until they land, run those
phases manually — see the [Roadmap](roadmap.md).

## 5. Pluggable tools

Beyond Claude Code itself, nothing in the core needs a database, a reference manager, or any other account. You choose the
backends per project in `research-config.yml`, and `/setup wren` sets them up to match
your data:

- **Database** — `files` (default, zero setup) → `sqlite`/`duckdb` (local, structured) →
  `directus-local` (Docker, admin UI + API) → `managed` (any host).
- **References** — `bibtex` (default, universal) or `zotero` (live, via MCP).

Switching later is a config change plus `./setup.sh`. Detail in
[Databases](guides/databases.md) and [References & integrations](guides/references.md).

---

## Where to go next

- Run `/setup wren` if you haven't — it does everything above and sets up your first paper.
- Already set up? Run `/paper` to start or resume a paper, or `/research` to see the whole
  workspace.
- Prefer to read first? Continue to the [Getting Started](getting-started.md) walkthrough.
