---
name: setup
description: Configure the research assistant, or run the guided first-time onboarding (interview + tour + first paper)
user-invocable: true
argument-hint: "[wren | reconfigure]"
---

# Setup

This skill has **two modes**:

- **`/setup wren`** — the guided first-time onboarding: a short tour of the system, an
  interview about the user's research, tool/plugin setup to match, and their first paper
  (or a paper series). Use this for a new project or whenever the user wants the full
  walkthrough.
- **`/setup`** (or `/setup reconfigure`) — the plain reconfigure path: explain and run
  `./setup.sh` to re-render from `research-config.yml`. Use this when the user has edited
  their config and just wants to apply it.

Pick the mode from the argument. If no argument is given, check freshness (see Phase A):
a project that looks freshly scaffolded should be offered the guided onboarding; an
established project defaults to reconfigure. When unsure, ask which they want.

---

# Mode 1 — Guided onboarding (`/setup wren`)

Run this as a **conversation**, not a script. It must obey the kit's own rules:

- **One thing per message** (`.claude/rules/one-at-a-time.md`): ask one question or
  present one chunk at a time, then stop and wait. Never dump the whole tour or a wall
  of questions at once.
- **Propose and confirm** (`.claude/rules/no-unapproved-tasks.md`): never create a file,
  edit config, or scaffold a paper without showing what you'll do and getting a yes.
  Never invent extra tasks.
- **Be honest** (`.claude/rules/rigor.md`): describe only what actually ships. `/qc-team`
  and `/figure` are **planned, not shipped** — say so.
- **Reads are free; writes are confirmed** (`.claude/rules/always-run-the-check.md`):
  read config and files freely; confirm every write. Actions only the user can do
  (obtaining API keys, connecting an MCP server in Claude, `docker compose up`, `npm
  login`) are **guided**, never silently attempted.

Keep the tone warm, plain, and brief — the user is a researcher, not a programmer.

## Phase A — Detect & greet

1. Read `research-config.yml` (identity, project, database, references) to see what the
   scaffolder already captured.
2. Decide freshness: the project is **fresh** if there is no onboarding marker
   (`.wren/onboarded` absent) and there are no real papers yet (only
   `papers/example-paper/` exists). Otherwise treat it as a returning user and offer to
   jump to any phase or to just reconfigure.
3. Greet by name (from `identity.author_name` if set). In ~2 sentences say what the next
   few minutes cover: **a quick tour, a few questions about your research, setting up the
   right tools, and starting your first paper.** Offer to skip any part.
4. Then move to Phase B. Wait for the user between phases.

## Phase B — Quick guided tour

Narrate from `docs/welcome.md` (the single-source guide), pulling detail from
`docs/concepts.md` and `docs/skills.md` as needed. Present **one topic per message**,
end each with a short "want more on this, or move on?" and wait.

Cover, in order:

1. **What Wren is + the four-layer memory model.** Behaviour rules → cross-session
   context → corpus memory (optional) → per-paper deep work. The point: context lands in
   exactly one place, and it persists across sessions.
2. **The 14-phase pipeline + the gold-standard freeze gate.** Every paper moves through
   14 phases tracked in its `STATUS.md`. Phase 7 is the freeze: analysis is verified,
   git-tagged, and archived as canonical **before any prose is written**. This is the
   discipline that stops drafting on numbers that later change.
3. **The skill map**, grouped: *orient & manage* (`/research`, `/paper`, `/setup`);
   *write & submit* (`/draft`, `/cover-letter`, `/revision-response`, `/peer-review`);
   *discover* (`/literature-scan`); *rigor & memory* (`/gold-standard`, `/rigor-check`,
   `/research-memory`, `/retro`).
4. **Audit / QC / peer-review.** Shipped: `/gold-standard` (the freeze/verify gate),
   `/peer-review` (four-stage journal-guideline review), `/rigor-check` (mid-session
   self-audit). **Planned, not shipped:** `/qc-team` (phases 6 & 11) and `/figure`
   (phase 9) — run those phases manually for now.

## Phase C — Interview

One topic per message. After each answer, reflect it back in a word or two and move on.
Do **not** write anything to disk yet — capture answers in the conversation and write
them all in Phase D after the user confirms. Ask about:

1. **Research interests & areas** — what fields/questions they work on. (→ refines
   `project.discipline`.)
2. **Key terms / vocabulary** — the handful of terms the assistant should treat as
   first-class. (→ `domain.key_terms`.)
3. **Data requirements** — what data they work with: kinds, scale, sources, whether it's
   structured/tabular or documents. (→ informs the database-backend recommendation in
   Phase D.)
4. **Target journals** — where they aim to publish. (→ `journals.default` +
   `journals.targets`.)
5. **Paper idea(s)** — one or more things they want to write. (→ used in Phase E.)

Then summarise everything captured in one compact block and ask them to confirm or
correct before any write.

## Phase D — Tools & plugins setup

From the interview, recommend and (on confirmation) configure the backends. Explain each
recommendation in one plain sentence; let the user override.

1. **Database backend** matched to their data (`database.backend`):
   - `files` (default) — Markdown/CSV/JSON, zero setup. Right for mostly-documents or
     small tables.
   - `sqlite` / `duckdb` — a local file, when they need structured queries.
   - `directus-local` — Docker, when they want an admin UI + API + MCP. Guide
     `docker compose --env-file .env -f data/docker-compose.directus.yml up`.
   - `managed` — any hosted host; needs `database.url`.
2. **Reference manager** (`references.provider`): `bibtex` (default, universal) or
   `zotero`. If Zotero: set `references.zotero.user_id`, and **guide** the user to put
   `ZOTERO_API_KEY` in `.env` and connect the Zotero MCP server in Claude — don't attempt
   it for them.
3. **Integrations / scheduler** (opt-in): Gmail digest, nightly memory, weekly digest.
   Only enable what they ask for.

Then, with confirmation:

- Write the agreed values into `research-config.yml` (the fields above — the renderer
  already reads them; no new schema).
- Re-run `./setup.sh` to apply. This re-renders `CLAUDE.md`, `CLAUDE_REFERENCE.md`, and
  `.mcp.json` — the last now containing exactly the MCP servers turned on (Zotero and/or
  Directus). Read back the verification summary.
- If any secret or MCP connection is still needed, tell the user the exact remaining
  step (which key in `.env`, which server to connect) — those are theirs to do.

## Phase E — First paper, or a paper series

**Ask which they want:** set up a single **first paper** now, or plan a **paper series**
(a small agenda of related papers). Then:

**First paper**
1. Propose an id (kebab-case), title, and target journal from their Phase C paper idea.
2. On confirmation, duplicate the template and seed it:
   ```bash
   cp -r papers/example-paper papers/<id>
   echo "<id>" > .current_paper
   ```
   Then edit `papers/<id>/STATUS.md` frontmatter (`paper_id`, `title`, `journal`,
   `phase: 1`, `status: scoping`) and remove the "▶ RESUME HERE / this is a template"
   note; write the research question into `PLAN.md`.
3. Confirm `.current_paper` is set so the per-paper hook injects its status each turn.

**Paper series**
1. Help outline the agenda: a short ordered list of related papers, each with a working
   title and one-line question. Write it to a brief plan the user approves (e.g.
   `papers/SERIES.md`).
2. Scaffold **the first** paper now exactly as above. Capture the rest as titled ideas in
   the series plan — do **not** batch-create every folder. Offer to scaffold the next one
   whenever they're ready.
3. Confirm one folder at a time.

## Phase F — Finish

1. Write the onboarding marker so the fresh-project nudge stops firing:
   ```bash
   mkdir -p .wren && date > .wren/onboarded
   ```
2. Summarise what was configured (backend, references, integrations) and what was created
   (the paper/series), in a few lines.
3. Hand off: run `/paper` to work on the paper just created, or `/research` to see the
   whole workspace. Suggest `/rigor-check` mid-session and `/retro` at the end.

---

# Mode 2 — Reconfigure (`/setup` / `/setup reconfigure`)

Apply changes after the user has edited `research-config.yml`. This wraps `./setup.sh`
with a plain-language explanation and a confirmation step.

1. **Check for config.** If `research-config.yml` doesn't exist, offer to copy it from
   `research-config.example.yml` and walk the user through the key fields (name,
   namespace, database backend, reference provider). Edit the file with their answers.
   (If this is clearly a brand-new project, suggest `/setup wren` instead.)
2. **Explain what setup will do**, in plain language: render `CLAUDE.md`,
   `CLAUDE_REFERENCE.md`, and `.mcp.json` from templates using their config; generate the
   safety-guard's protected-paths list; make hooks executable; run a verification pass.
   Note that rendered files are git-ignored so nothing personal gets committed.
3. **Confirm**, then run:
   ```bash
   ./setup.sh
   ```
   (Add `--with-schedule` only if they want scheduled background jobs and that module is
   installed.)
4. **Report the result** — read back the verification summary. If anything failed,
   troubleshoot from the message (usually a missing `pyyaml`, or a not-yet-created memory
   dir, which is fine on first run).

Setup is idempotent — re-run any time the user changes a journal, database backend, or
reference provider.
