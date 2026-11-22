# Scheduled jobs & email

An optional add-on that runs recurring, headless tasks — like a weekly literature digest
drafted to your inbox — without you being at the keyboard. It's off by default; nothing is
scheduled until you enable a job and activate it yourself.

## How it works

You declare jobs in `research-config.yml`; a generator turns the enabled ones into runner
scripts + a launchd agent (macOS) or a cron line (Linux). Each job is a headless
`claude -p "<slash-command>"` (or a plain script) that logs to `outputs/_logs/`.

```yaml
scheduler:
  platform: launchd            # launchd (macOS) | cron (Linux) | none
  jobs:
    weekly_digest:
      enabled: true
      day: "Mon"
      at: "08:47"
    nightly_memory:
      enabled: false
      at: "02:30"
```

- **`weekly_digest`** → runs `/lit-digest` (a cross-paper literature sweep → a digest + an
  optional Gmail draft).
- **`nightly_memory`** → runs `npm run memory:audit` (a corpus-memory health check).

## Set it up

1. Enable a job and set its time in `research-config.yml` (above), and set
   `scheduler.platform` to `launchd` or `cron`.
2. Generate the runners:
   ```bash
   ./setup.sh --with-schedule        # or: python3 scripts/setup/install_scheduled.py
   ```
   This writes `scripts/scheduled/<job>.sh` (+ a `.plist` on macOS) and **prints the exact
   command to activate it** — it never registers the job for you.
3. Run that activation command (`launchctl load …` on macOS, or paste the line into
   `crontab -e` on Linux).
4. Test it immediately, without waiting for the schedule:
   ```bash
   bash scripts/scheduled/weekly_digest.sh
   ```

Full activate / test / disable steps: [`scripts/scheduled/README.md`](https://github.com/rchoularton/wren/blob/main/scripts/scheduled/README.md).

## Email (the Gmail draft)

The digest can draft itself to your inbox — as a **draft**, never sent.

1. **Connect a Gmail MCP in your Claude account** (Claude's Gmail connector, or a community
   Gmail MCP server).
2. Set `integrations.gmail.enabled: true` and re-run the generator.

The generator then adds the Gmail draft tool to that job's `--allowedTools`. **This is the one
subtle gotcha:** a headless run silently skips any step whose tool isn't listed by its exact
name. The default is Claude's connector tool `mcp__claude_ai_Gmail__create_draft`; if your
Gmail MCP exposes its draft tool under a different name, edit the generated runner's
`--allowedTools` to match.

## The weekly librarian job

`weekly_librarian` runs `/librarian-team --headless` (Wednesdays 09:03 by default). It is
proposals-only. Its runner exports `WREN_UNATTENDED=1`, which turns on
`.claude/hooks/pre-tool-unattended-guard.sh`: that hook, not the `--allowedTools` list, restricts the
run to a handful of exact commands, the librarian report and proposal files, and read-only Zotero
tools. You review the queue yourself with `/librarian-team --review`. See
[Library automation](library-automation.md) for exactly what is allowed and what stays outside the boundary.

## Cross-platform notes

- **macOS** uses launchd; **Linux** uses cron; **`none`** generates the runners but registers
  nothing (run them by hand or wire your own scheduler).
- Desktop notifications use `terminal-notifier` if present (macOS); everywhere else, runs still
  log to `outputs/_logs/` and `RUNNING.md`.
- launchd does not wake a sleeping Mac — a missed run fires on next wake.
