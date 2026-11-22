# Library automation

`/librarian-team` keeps a Zotero library tidy and current without writing to it behind your
back. It needs `references.provider: zotero` (see [References](references.md)).

## The weekly run

`/librarian-team` runs in four phases:

1. **Context.** Today's date, the window (14 days by default, `--since` to change it), your papers, the pending counts of earlier queues (from the queue script), and the latest lit-digest.
2. **Cataloguer and scout, in parallel.** The `librarian-cataloguer` agent audits recently added items for missing or malformed metadata and proposes Crossref-sourced fixes. The `librarian-scout` agent searches for new publications for your papers, rates scooping risk, skips what the library or the digest already has, and proposes `add_item` actions. Both are read-only on the library.
3. **Duplicates.** `npm run zotero:duplicates` groups likely duplicates and writes one `merge_duplicate` proposal per group.
4. **Queue and report.** `npm run zotero:build-queue` validates and de-duplicates every proposal into `outputs/librarian/approval_queue_<date>.json`; the skill writes `report_<date>.md` from script output. With `integrations.gmail.enabled: true` it also creates a Gmail draft of the report (never sends).

Nothing in Zotero changes during the run.

## The review loop

`/librarian-team --review` takes the newest queue with pending actions, shows what a dry
`reconcile` would mark as already done, then presents **one action per message**: type, title,
the exact change and the source agent. You answer approve, reject or skip; the skill runs the
queue script and shows its result line. Each write is re-read from Zotero before the action is
marked `applied`.

`/librarian-team --approve-all` shows the queue summary, asks one confirmation naming the count,
then applies every pending action. Use it only when you have read the report.

## What unattended mode can and cannot do

`--headless` runs the full run with no questions. It can read the library, search the web, run
the duplicate scan and the queue builder, read queue status, and write files under
`outputs/librarian/`. It cannot approve, reject, skip or reconcile-apply anything, write to
Zotero, or send email.

Two independent layers enforce this:

- **The allowlist.** The scheduled command passes an explicit `--allowedTools` list: read and
  write tools, `Agent`, web tools, the read-only Zotero MCP tools, and three narrow `Bash`
  patterns (`date`, the duplicate scan and queue builder, and queue `status`). No bare `Bash`, no `Edit`.
- **The environment guard.** The runner exports `WREN_UNATTENDED=1`. With it set, the queue
  script exits 1 with "refused: unattended run" for every command that changes the library or
  records a decision, before it reads the queue or creates a client. `status` and a dry
  `reconcile` still work.

## Enable the scheduled job

In `research-config.yml`:

```yaml
scheduler:
  platform: launchd        # or cron
  jobs:
    weekly_librarian:
      enabled: true
      day: "Wed"
      at: "09:03"
```

Then run `./setup.sh --with-schedule` and the activation command it prints. Test it once with
`bash scripts/scheduled/weekly_librarian.sh` and read `outputs/_logs/weekly_librarian_<date>.log`.
More in [Scheduled jobs](scheduled-jobs.md). Review the result with `/librarian-team --review`.
