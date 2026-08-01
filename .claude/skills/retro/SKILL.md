---
name: retro
description: Quick session retrospective - capture process improvements, research insights, and system feedback into cross-session memory
user-invocable: true
argument-hint: [quick|full]
---

# Session Retrospective

Capture what was learned this session so future sessions benefit. Two modes: **quick** (default, ~1 minute) and **full** (deeper review + consolidation).

## Where memory lives

This skill writes to the Claude Code **per-project memory directory**:
`~/.claude/projects/<slug>/memory/`, where `<slug>` is the absolute project path with `/` and `.` replaced by `-`. Resolve it with:

```bash
python3 -c "import os,re;from pathlib import Path;r=os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd();print(Path.home()/'.claude/projects'/re.sub(r'[/.]','-',str(Path(r).resolve()))/'memory')"
```

This is the same directory the SessionStart hook reads, so anything you save here resurfaces next session.

## Mode: Quick (`/retro` or `/retro quick`)

### Step 1: Reflect

Review the session. Identify 2-5 learnings across three domains:

- **Process:** Workflow patterns that worked or failed; pipeline-order discoveries; approaches worth repeating/avoiding.
- **Research:** Findings, methodology decisions, data insights, domain knowledge. Surprises or corrections.
- **System:** What the assistant did well or poorly; tool issues; prompt patterns that helped or wasted time.

Only include domains with something genuinely worth capturing. Be specific and actionable.

### Memory split

If the corpus-memory add-on is enabled, **research** findings about the literature/corpus belong in `research_memory/` (via `/research-memory`), not here — cross-reference rather than duplicate. **Process** and **System** learnings always get stated in full here, because they're about how the assistant should work in this project. Keep auto-memory lean; it loads every session.

### Step 2: Propose

Present the learnings grouped by domain. Ask: "Want me to save these? Edit anything?" If the user says skip — exit, write nothing.

### Step 3: Save

On approval, write `learning_{YYYY-MM-DD}_{slug}.md` into the memory dir, where `{slug}` is a short kebab-case descriptor. Format:

```yaml
---
name: Short descriptive title
description: One-line summary used for relevance matching in future sessions
metadata:
  type: feedback
domain: process|research|system|mixed
session_date: YYYY-MM-DD
paper_context: my-paper (or "general")
---

## What happened
One sentence on the session context.

## Learnings
- **Process:** …
- **Research:** …
- **System:** …

## Action items
- [ ] Concrete next steps that should carry forward (if any)
```

### Step 4: Update the index

Add a one-line entry to the `## Learnings` section of `MEMORY.md`:
```
- [Title](learning_YYYY-MM-DD_slug.md) — one-line summary
```
Keep the Learnings section to the 5 most recent entries (trim the oldest index line; the file stays).

## Mode: Full (`/retro full`)

Do everything in Quick, plus:
- Review the last ~2 weeks of `learning_*.md` and consolidate duplicates.
- **Promote recurring feedback:** if the same correction shows up 2+ times, propose turning it into a `.claude/rules/*.md` behavior rule, and archive the source feedback memory (move to `memory/_archive/`, note the mapping).
