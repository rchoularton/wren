# Tooling & Workflow Rules

## 1. Terminal-first — no browse-layer UIs

This system is driven from the terminal by asking the assistant. Don't propose browse-layer tools as system improvements: Obsidian vaults, Streamlit dashboards, Notion mirrors, Kanban boards, web cockpits, React frontends. If a feature requires the user to open something **other** than their terminal (and their editor) to get value, it's the wrong shape for this system.

Legitimate improvements work through skills (`/command`), hooks, scheduled background jobs, memory, and ambient signals (`RUNNING.md`, desktop notifications).

**Why:** a researcher who can just ask the assistant shouldn't have to browse a separate app. (If you personally want a dashboard, that's a preference — build it, but don't file it as a system improvement the assistant should push.)

## 2. Tool output may not be visible in the editor

In an editor extension, **Read-tool output and plan-file contents may not render** in the chat view. Don't assume the user can see what you just read.

- When the user says "show me" or "pull up" a file → `open <filepath>` via Bash, or print the key content in your message
- When working on plans → summarize the plan content in chat text, don't rely on the plan file being visible
- When the user needs to review changes → open the file in the editor rather than relying on Read output

Background and examples: docs/rules-history.md.
