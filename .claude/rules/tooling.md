# Tooling & Workflow Rules

## 1. Terminal-first — no browse-layer UIs

This system is designed to be driven from the terminal by asking the assistant. Don't propose browse-layer tools as system improvements: Obsidian vaults, Streamlit dashboards, Notion mirrors, Kanban boards, web cockpits, React frontends. If a feature requires the user to open something **other** than their terminal (and their editor) to get value, it's the wrong shape for this system.

Legitimate system improvements work through:

- Skills (`/command`)
- Hooks (fire automatically)
- Scheduled background jobs (notifications, email digests)
- Memory (persistent context)
- Ambient signals (`RUNNING.md`, desktop notifications)

**Why:** A researcher who can just ask the assistant shouldn't have to go browse a separate app to get an answer. (If you personally *want* a dashboard, that's a preference — build it, but don't file it as a system improvement the assistant should push.)

## 2. Tool output may not be visible in the editor

The user often runs Claude Code inside an editor extension where **Read-tool output and plan-file contents are not rendered** in the chat view. Don't assume the user can see what you just read.

**How to apply:**
- When the user says "show me" or "pull up" a file → use `open <filepath>` via Bash to open it in their editor, or print the key content directly in your chat message
- When working on plans → summarize the plan content in chat text, don't rely on the plan file being visible
- When the user needs to review changes → open the file in the editor rather than relying on Read output
