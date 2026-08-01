---
name: research-memory
description: Query and update the corpus memory - recall findings, log notes, check status across your literature and projects
user-invocable: true
argument-hint: [status|recall <topic>|log <artifact> "<note>"|inspect <artifact>]
---

# Research Memory

Work with the corpus-memory layer in `research_memory/` (see `research_memory/README.md`). Plain Markdown, queried by grep — no external service.

## `/research-memory status`

Summarize the corpus: count external source notes (`episodic/_external/_by-citekey/*.md`), list internal artifacts and their phase/status (from `episodic/_internal/**` frontmatter), and show counts of open questions, gaps, and contradictions from `semantic/`. Read `research_memory/MEMORY.md` for the dashboard.

## `/research-memory recall <topic>`

Grep the whole `research_memory/` tree for the topic and synthesize what's known:
```bash
grep -rin "<topic>" research_memory/ --include=*.md
```
Report the matching sources, which papers they link to, and any related open questions or contradictions. Cite the file paths.

## `/research-memory log <artifact> "<note>"`

Append a dated note to that artifact's internal file (`episodic/_internal/{papers|country|special}/{artifact}.md`), under its `## Manual notes` section. Confirm the target file first. If the artifact has no file yet, offer to create one from the template in `episodic/_internal/papers/example-paper.md`.

## `/research-memory inspect <artifact>`

Print the artifact's internal state file — frontmatter (phase, tier, status, themes, linked sources) and body — so the user can see the corpus's current view of it.

## Adding an external source note

To record a finding from a paper you've read, create `episodic/_external/_by-citekey/{citekey}.md` with frontmatter (`citekey`, `paper_links`, `themes`, `confidence`) and a short findings body, then add a line to `episodic/_external/INDEX.md`. Follow the shape in `research_memory/README.md`.

> The automated Zotero-ingestion module (nightly LLM extraction) is a future add-on — see `research_memory/README.md`. This skill works fully without it.
