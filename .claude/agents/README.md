# Sub-agents

Each `*.md` file here defines a **sub-agent** — a focused persona Claude Code can run in its
own isolated context via the Agent (Task) tool. Skills invoke them to get work done in a
clean context with its own tool budget, so a long orchestration doesn't blow the main
session's context, and adversarial roles can't see each other's reasoning.

## File format

```markdown
---
name: qc-skeptic            # kebab-case; how skills address the agent
description: "One or two sentences on what this agent does and when it's invoked."
model: opus                 # opus | sonnet | haiku — omit to inherit the session model
color: red                  # optional UI colour
---

The system prompt for the agent — its role, inputs, task, output format, and hard rules.
```

`model:` sets the tier this agent runs at (see the token-budget rule and
`.claude/lib/model-policy.mjs` once the token-management add-on is enabled): adversarial
review / synthesis → `opus`; standard drafting/analysis → `sonnet`; routine/mechanical →
`haiku`. Omit it to inherit whatever model the session is on.

## What ships here

- `qc-skeptic`, `qc-responder`, `qc-team-leader` — the three-agent adversarial QC review,
  orchestrated by the `/qc-team` skill.
- `figure-designer`, `scientific-graphics-reviewer` — the figure-iteration loop, orchestrated
  by the `/figure` skill.

Agents are invoked **by skills**, not typed as slash commands. Add your own by dropping a new
`name.md` here and referencing it from a skill.
