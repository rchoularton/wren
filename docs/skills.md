# Skills

Type these as slash commands in Claude Code once your project is open. All 17 ship in the box, grouped by what they do.

## Orient & manage

| Skill | What it does |
|---|---|
| `/research` | Access and navigate your research workspaces — papers, notes, and the corpus memory. The workspace entry point. |
| `/paper` `[paper-id]` | Paper portfolio management — check status, resume work, navigate papers, start a new paper. |
| `/setup` | Configure or reconfigure the research assistant — explains and runs the setup renderer in plain language. |

## Write & submit

| Skill | What it does |
|---|---|
| `/draft` `[paper-id] [section]` | Turn frozen analysis outputs into paper sections — journal mode or working-paper mode. |
| `/cover-letter` `[paper-id]` | Draft a journal-specific cover letter from a paper's frozen findings. |
| `/revision-response` `[paper-id]` | Structure a point-by-point response to peer reviewer comments for a journal revision. |
| `/ref-check` `[paper-id] [--format] [--gaps] [--zotero]` | Validate a draft's citations against your library, find uncited claims, check journal formatting. |
| `/peer-review` `[paper-id] [--journal "Journal Name"] [--skip-examples] [--section "name"]` | Agentic peer reviewer that evaluates a paper against its target journal's guidelines in four stages. |
| `/figure` `[paper-id] [--figure N] [--all] [--score-only]` | Designer → Critic loop that iterates a figure to publication quality (8-dimension scoring, journal compliance). |

## Discover

| Skill | What it does |
|---|---|
| `/literature-scan` `[topic-or-paper-id]` | Search recent publications on a topic — flag scooping risks, find citation gaps. |
| `/zotero-audit` `[--collection <name>] [--since <date>] [--fix]` | Scan your Zotero library for items missing metadata, tags, PDFs, or collections; auto-complete from Crossref. Needs the `zotero` provider. |

## Rigor & memory

| Skill | What it does |
|---|---|
| `/gold-standard` `[paper-id]` | Freeze an analysis as canonical — verify outputs, git-tag, and archive as the paper's gold standard (Phase 7 gate). See [Concepts](concepts.md#the-14-phase-paper-pipeline). |
| `/rigor-check` | Mid-task self-audit against the research rigor rules — catches context drift, shortcuts, and unjustified assumptions during long sessions. |
| `/methods-audit` `[paper-id] [--fix]` | Audit a paper's analysis scripts for exploration artifacts, stale values, and reproducibility gaps before you freeze. |
| `/qc-team` `[paper-id] [--skeptic-only]` | Three-agent adversarial QC (Skeptic → Responder → Team Leader) — verifies stats against source data, produces a Must-Fix / Should-Fix verdict. |
| `/research-memory` `[status\|recall <topic>\|log <artifact> "<note>"\|inspect <artifact>]` | Query and update the corpus memory — recall findings, log notes, check status across your literature and projects. See [Corpus memory](guides/corpus-memory.md). |
| `/retro` `[quick\|full]` | Quick session retrospective — capture process improvements, research insights, and system feedback into cross-session memory. |

All shipped skills are available today. Future work is on the [roadmap](roadmap.md).
