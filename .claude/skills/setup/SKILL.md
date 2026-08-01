---
name: setup
description: Configure or reconfigure the research assistant - explains and runs the setup renderer in plain language
user-invocable: true
---

# Setup

Configure the kit for this user, or apply changes after editing `research-config.yml`. This wraps `./setup.sh` with a plain-language explanation and a confirmation step.

## What to do

1. **Check for config.** If `research-config.yml` doesn't exist, offer to copy it from `research-config.example.yml` and walk the user through the key fields (name, namespace, database backend, reference provider). Edit the file with their answers.
2. **Explain what setup will do**, in plain language: render `CLAUDE.md`, `CLAUDE_REFERENCE.md`, and `.mcp.json` from templates using their config; generate the safety-guard's protected-paths list; make hooks executable; run a verification pass. Note that rendered files are git-ignored so nothing personal gets committed.
3. **Confirm**, then run:
   ```bash
   ./setup.sh
   ```
   (Add `--with-schedule` only if they want scheduled background jobs and that module is installed.)
4. **Report the result** — read back the verification summary. If anything failed, troubleshoot from the message (usually a missing `pyyaml`, or a not-yet-created memory dir, which is fine on first run).

## Reconfiguring later

Any time the user edits `research-config.yml` (new journal, different database backend, enabling Zotero), re-run `./setup.sh` to apply it. Setup is idempotent.
