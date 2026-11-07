# Session memory

Session capture is an **opt-in** add-on that keeps a short, dated log of what each session did and decided, so `/recall` can answer "what did we decide about X?" later. It is off by default.

## Enable it

In `research-config.yml`:

```yaml
tiers:
  session_capture: true
```

## What it stores, and where

After each exchange, the Stop hook starts a detached, time-limited `claude -p --model haiku` call that turns the last exchange into two to five third-person bullets. The bullets are appended to `<auto-memory dir>/context/sessions/YYYY-MM-DD.md`, where `<auto-memory dir>` is `~/.claude/projects/<project-slug>/memory`. A hash file (`sessions/.captured`) prevents the same exchange being written twice; failures go to `sessions/.capture_errors.log`.

- **Cost:** one cheap model call per exchange, on the `haiku` alias (the triage tier).
- **Privacy:** at most about 6,000 characters of the exchange go to that local `claude` call. Nothing is sent anywhere else. The summarizer is told not to record credentials, but the logs are summaries of your work, so review them before sharing the machine or backing up the memory directory.
- **Never blocks:** the hook exits immediately; if no `claude` binary is found it does nothing. Set `WREN_CLAUDE_BIN` to point at a specific binary.
- **Delete the logs:** remove `<auto-memory dir>/context/sessions/` (or one day's file). Turning the toggle off stops new capture but leaves existing logs.

## Using it

- `/recall <topic>` (or `npm run recall -- <terms>`) searches the logs and answers citing the date and session heading. When nothing matches it says so.
- At session start, with capture on, a short "Recent sessions" block from today's and yesterday's logs is added to context: the last 8 bullets, hard-capped at 1,200 bytes. It adds up to 1.2 kB to each session start while enabled. `npm run context:size` reports this as a separate "with session_capture on" line; the budgeted total is measured with capture off.
