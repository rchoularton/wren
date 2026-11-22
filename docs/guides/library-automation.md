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

`--headless` runs the full run with no questions, as the `weekly_librarian` scheduled job.
`/librarian-team --headless --review` and `--headless --approve-all` are refused.

**The tool list is not the boundary.** The job's `--allowedTools` list is a convenience, because
project allow rules in `.claude/settings.json` (`Bash(python3:*)`, `Bash(node:*)`, `Bash(npm run:*)` and
others) are additive: a tool you leave off the list may still be allowed by them. Two things that
a model cannot talk its way around enforce the boundary instead.

**1. A hook.** The runner exports `WREN_UNATTENDED=1`. While it is set to anything except empty,
`0`, `false` or `no`, `.claude/hooks/pre-tool-unattended-guard.sh` (registered for `Bash`,
`Write|Edit|MultiEdit|NotebookEdit` and `mcp__.*`) denies every call off this allowlist, whatever
the allow rules say. A hook denial blocks the call (it exits 2 and prints a PreToolUse `deny`):

- **Bash**: only `date +%F`, the duplicate scan (`npm run zotero:duplicates -- --out
  outputs/librarian/duplicates_<date>.json --proposals outputs/librarian/duplicates_<date>.proposals.json`,
  optionally `--limit N` and `--no-fuzzy`), `npm run zotero:build-queue -- --date <date>`, and
  `npm run zotero:queue -- status outputs/librarian/approval_queue_<date>.json`. No shell
  metacharacters (`; & | $ ` > < ( ) { }`, newlines) are accepted.
- **Write**: only `outputs/librarian/cataloguer_<date>.md` and `.proposals.json`,
  `scout_<date>.md` and `.proposals.json`, and `report_<date>.md`, after resolving `..` and
  symlinks. The queue, its lock, the duplicate report and `rejected_<date>.json` are written only by the
  scripts. `Edit`, `MultiEdit` and `NotebookEdit` are always denied.
- **MCP tools**: only the six read-only Zotero tools and the Gmail create-draft tool.

**2. The scripts.** With `WREN_UNATTENDED` set, `approval-queue.mjs` refuses `approve`,
`approve-all`, `reject`, `skip` and `reconcile --apply` before it reads the queue or creates a client;
`pdf-fill.mjs` and `reparent-orphan-attachments.mjs` refuse `--apply`; `build-queue.mjs` refuses `--force`;
and `build-queue.mjs` and `detect-duplicates.mjs` write only inside `outputs/librarian/`. Even attended,
they refuse output paths outside the project root. `status` and a dry `reconcile` still work.

**What stays outside this boundary.** The hook does not restrict `Read`, `Grep`, `Glob`, `WebSearch`,
`WebFetch` or `Agent`, and it does not cover the web-reading sub-agents' own model calls (the scout
reads web pages; its output is treated as data and reaches Zotero only through your review), the optional Gmail draft, or anything you change: loosening
`.claude/settings.json`, removing the hook registration, or editing the generated runner removes
the protection. The hook fails open if it times out or `python3` is missing, so keep the
`claude` run on a machine where `python3` works.

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
