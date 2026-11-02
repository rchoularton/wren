# Roadmap

Where Wren is headed. Each release below is a GitHub **milestone** — follow the links to
see its issues and live progress. Versions follow [semantic versioning](maintaining.md#versioning-in-one-paragraph):
while Wren is pre-1.0, every release that adds a tool is a MINOR bump.

## Shipped

- **0.8.0** — `/lit-digest` + the scheduled-jobs/email tier (launchd/cron).
- **0.7.0** — `/qc-team`, `/figure` (the sub-agent tier); model-routing tiers + a token-usage report.
- **0.6.0** — `/methods-audit`, `/ref-check`, `/zotero-audit`.
- **0.5.0** — the wren logo across the docs, README, and the terminal.
- **0.4.0** — guided onboarding (`/setup wren`): a tour, an interview, tool setup, first paper.
- **0.3.0** — renamed to **Wren**; published to npm as `create-wren`.

## Planned

Wren is extracted from a private research system that keeps evolving. Each release below
ports the generic part of what that system learned, in the order that pays off soonest:
first what is already built, then what makes the harness *enforce* rigor instead of asking
for it, then the bigger skills.

| Release | Theme | What ships |
|---|---|---|
| **0.9** | Review suite + harness-enforced rigor | `/peer-review` (three referees + a handling editor; built, awaiting merge). Reviewer agents made read-only; the critique tier pinned to the strong model; a review-stage gate hook that blocks a verdict when a prior stage's report is missing; a post-compaction re-pin hook; a model-advisory hook for unpinned sub-agents; a non-blocking stdin fix in the prompt hook |
| **0.10** | Context diet + rules refresh | Standing context trimmed (rule histories to docs, agent examples collapsed, memory index one line each); new rules: always-run-the-check, Wren's own voice, gold-standard versioning; updated archive convention; the Word-prompt approval wording; an AI-detection step before resubmission; a document-to-Markdown cache so PDFs and Word files are read as cheap text |
| **0.11** | Front door + session memory | `/research` rebuilt around a deterministic status script: papers by tier from `STATUS.md` frontmatter with a `next:` line, scheduled-job verdicts, a generated papers table; opt-in session capture + `/recall` over dated session logs |
| **0.12** | Library automation | `/librarian-team` — weekly Zotero audit + discovery with an approval queue; `/pdf-fill` with open-access sources and a configurable institution proxy; orphan-attachment repair |
| **0.13** | Submission-grade audit | `/claim-audit` — enumerated, adversarial manuscript audit; `/code-capsule` — a reproducibility package from the gold standard; journal-submission-prep and reference-manager agents; `/consistency-check` as a multi-paper option |
| **1.0** | Stable release | a light test suite, polish, docs, announcement |
| **1.1** | Parallel sessions (opt-in) | one branch per unit of work and one worktree per session: a branch-discipline rule, `/branch`, `/sessions`, `/wrap-up`, guard hooks, tests; robot worktrees with a scheduled auto-merge for background jobs. Desktop-app aware, off by default |
| **1.2** | Second brain | opt-in Obsidian/wikilink lens on your memory — a map-of-content + graph and an optional vault; your files and the terminal stay primary |
| **1.3** | Collaboration | multi-author paper work — share via a git repo or a OneDrive/Google Drive folder, a shared author roster, shared references, draft/freeze conventions; `/filing` and an append-only guard for the shared folder |

Track live progress on the [milestones](https://github.com/rchoularton/wren/milestones) and
the [project board](https://github.com/rchoularton/wren/projects). Want something sooner, or
have an idea? [Open an issue](https://github.com/rchoularton/wren/issues/new/choose) or 👍 an
existing one — see [Contributing](contributing.md).

---

*Maintainer note: this page is Wren's own roadmap. The `ROADMAP.md` in a scaffolded project
is **your** research-project roadmap, a separate thing.*
