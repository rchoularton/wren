# Skills

Type these as slash commands in Claude Code once your project is open. All 12 ship in the box, grouped by what they do.

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
| `/peer-review` `[paper-id] [--journal "Journal Name"] [--skip-examples] [--section "name"]` | Agentic peer reviewer that evaluates a paper against its target journal's guidelines in four stages. |

## Discover

| Skill | What it does |
|---|---|
| `/literature-scan` `[topic-or-paper-id]` | Search recent publications on a topic — flag scooping risks, find citation gaps. |

## Rigor & memory

| Skill | What it does |
|---|---|
| `/gold-standard` `[paper-id]` | Freeze an analysis as canonical — verify outputs, git-tag, and archive as the paper's gold standard (Phase 7 gate). See [Concepts](concepts.md#the-14-phase-paper-pipeline). |
| `/rigor-check` | Mid-task self-audit against the research rigor rules — catches context drift, shortcuts, and unjustified assumptions during long sessions. |
| `/research-memory` `[status\|recall <topic>\|log <artifact> "<note>"\|inspect <artifact>]` | Query and update the corpus memory — recall findings, log notes, check status across your literature and projects. See [Corpus memory](guides/corpus-memory.md). |
| `/retro` `[quick\|full]` | Quick session retrospective — capture process improvements, research insights, and system feedback into cross-session memory. |

## Planned (not shipped)

These need an agent-team tier not yet in the kit. They are **not** available in v0.2.0 — see [`ROADMAP.md`](roadmap.md).

| Skill | What it would do |
|---|---|
| `/qc-team` | Adversarial QC review of a draft — a Skeptic / Responder / Team Leader agent trio, covering pipeline phase 6 (QC review) and phase 11 (QC of draft). |
| `/figure` | Figure design and critique loop for publication-quality graphics, covering pipeline phase 9 (Figures). |

Good first contributions to the kit include porting these two skills — see [Contributing](contributing.md).
