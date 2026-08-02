# Scheduled jobs

Runner scripts and registration files for headless, recurring tasks (e.g. the weekly
literature digest) are **generated here** from your `research-config.yml` — they are not
committed. Run:

```bash
./setup.sh --with-schedule       # or: python3 scripts/setup/install_scheduled.py
```

For every enabled job under `scheduler.jobs.*`, this writes:
- `<job>.sh` — the runner (paths resolved for this machine; logs to `outputs/_logs/`)
- **macOS:** `com.<namespace>.<job>.plist` — a launchd agent
- **Linux:** a `crontab` line (printed, not a file)

It **does not register the job for you** — it prints the exact activation command so nothing
touches your system without your say-so.

## Activate

**macOS (launchd):**
```bash
cp scripts/scheduled/com.<namespace>.<job>.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.<namespace>.<job>.plist
launchctl list | grep <namespace>          # confirm it's registered
```

**Linux (cron):** paste the printed line into `crontab -e`.

## Test / disable

```bash
bash scripts/scheduled/<job>.sh            # run it now, without waiting for the schedule
```
- **Disable (macOS):** `launchctl unload ~/Library/LaunchAgents/com.<namespace>.<job>.plist`
- **Disable (Linux):** remove the line from `crontab -e`
- Or set the job's `enabled: false` in `research-config.yml`.

## Notes

- **Exact tool names matter.** A headless `claude -p` run silently skips any step whose tool
  isn't in `--allowedTools`. The digest job includes the Gmail draft tool only when
  `integrations.gmail.enabled: true` — see [the docs](../../docs/guides/scheduled-jobs.md).
- **launchd doesn't wake a sleeping Mac.** A missed run fires on next wake.
- Jobs pick a model by weight (the digest runs on `sonnet`); logs land in `outputs/_logs/`.
