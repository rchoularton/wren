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
`Write|Edit|MultiEdit|NotebookEdit`, `Read|Grep|Glob`, `WebFetch|WebSearch` and `mcp__.*`) denies every call off
this allowlist, whatever the allow rules say. Documented Claude Code behaviour this relies on: PreToolUse
hooks in settings files also fire for sub-agent tool calls; a hook that exits 2 stops the call before
permission rules are evaluated; when hooks disagree, deny beats allow; any other non-zero exit is a
non-blocking error and the call proceeds, so the wrapper turns every outcome except exit 0 or 2 (a
missing `python3`, a crash) into a deny. The hook denies with a `deny` JSON and exit 2:

- **Bash**: only `date +%F`, the duplicate scan (`npm run zotero:duplicates -- --out
  outputs/librarian/duplicates_<date>.json --proposals outputs/librarian/duplicates_<date>.proposals.json`,
  optionally `--limit N` and `--no-fuzzy`), `npm run zotero:build-queue -- --date <date>`, and
  `npm run zotero:queue -- status outputs/librarian/approval_queue_<date>.json` (an absolute path that resolves to that same file inside the project is also allowed). No shell
  metacharacters (`; & | $ ` > < ( ) { }`, newlines) are accepted.
- **Write**: only `outputs/librarian/cataloguer_<date>.md` and `.proposals.json`,
  `scout_<date>.md` and `.proposals.json`, and `report_<date>.md`, after resolving `..` and
  symlinks. The queue, its lock, the duplicate report and `rejected_<date>.json` are written only by the
  scripts. `Edit`, `MultiEdit` and `NotebookEdit` are always denied.
- **MCP tools**: only the six read-only Zotero tools and the Gmail create-draft tool.
- **Read, Grep, Glob**: a positive allowlist. A path argument is required (`file_path` for Read, `path` for
  Grep and Glob), and its resolved real path must be inside `papers/`, `outputs/`, `research_memory/`,
  `references/`, `docs/`, `.claude/agents/` or `.claude/skills/`, or be `scripts/zotero/README.md`,
  `research-config.yml` or `README.md`. Everything else is denied, including `package.json`, `.env.example`
  and the rest of `scripts/`. Inside those places it still denies a file whose lower-cased name is `.env`,
  starts with `.env.` , or is `.mcp.json`, `settings.local.json` or `.npmrc`, anything under `.git/`, and any
  file with the same device and inode as the project's `.env*` files, `.mcp.json` or
  `.claude/settings.local.json` (so a hard link does not work). A filename filter (Grep's `glob` argument and Glob's `pattern` argument; Grep's `pattern` is a content regex and is not filtered) that contains
  `.e`, `[`, `{`, `?` or a dot followed by a wildcard is denied, as is a Glob pattern that is absolute (`/` or `~`) or has a `..` segment, because it could match `.env` on a
  case-insensitive filesystem.
- **WebFetch**: `https` only, no userinfo in the URL.
- **Secret values**: for every tool the hook sees, a call is denied if its input contains a value (12+
  characters) of a variable whose name has `KEY`, `TOKEN`, `SECRET`, `PASSWORD` or `PASSWD` as a whole
  underscore-separated word (`MONKEY_BUSINESS` does not count) from `<project>/.env` or the hook's
  environment, in raw, URL-encoded or base64 form. The reason never repeats the value. This closes the
  obvious route for sending the Zotero API key (which can write to your library) to a web request; it blocks
  those literal forms and does not claim to stop every possible encoding. If `<project>/.env` exists but cannot
  be read, every guarded call is denied ("cannot read .env to protect secrets").

**2. The scripts.** With `WREN_UNATTENDED` set, `approval-queue.mjs` refuses `approve`,
`approve-all`, `reject`, `skip` and `reconcile --apply` before it reads the queue or creates a client;
`pdf-fill.mjs` and `reparent-orphan-attachments.mjs` refuse `--apply`; `build-queue.mjs` refuses `--force`;
and `build-queue.mjs` and `detect-duplicates.mjs` write only inside `outputs/librarian/`. Even attended,
they refuse output paths outside the project root. `status` and a dry `reconcile` still work.

**What stays outside this boundary.** The hook does not scan or restrict `Agent` input (that matcher only runs the
model-advisory hook), and it does not cover the sub-agents' own model calls. `WebSearch` input is scanned for secrets,
but a search can still carry anything that is not a known secret. The Gmail create-draft tool is allowed by the MCP
rule and its input is scanned for secrets; its recipient and wording are not restricted. Loosening
`.claude/settings.json`, removing the hook registration, or editing the generated runner removes the protection.
The hook fails closed if `python3` is missing or the guard crashes. Claude Code documents that a hook timeout does
not block the call; behaviour on a hook timeout is not verified here.

Two more limits. A secret whose variable name has no separator before `KEY` or `TOKEN` (for example
`ZOTERO_APIKEY`) is not recognised by the value scan, so name secrets with an underscore. And if an allowed
directory such as `papers/` is a symlink to another location, unattended reads of it are denied, because the
resolved path is outside the allowed roots.

## What no hook can remove

- The run reads text written by other people (web pages, Crossref records, Zotero fields). The control is
  keeping secrets out of its reach, not detecting every way they could be encoded.
- Web search and fetch send search terms and paper titles to third parties. That is how discovery works.
- Proposals still depend on your review. `/librarian-team --approve-all` approves everything with one
  confirmation, so read the report first.
- Anyone who can edit `.claude/settings.json` or the generated runner can remove the boundary.

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

Run this job only in a project folder you have trusted. In an untrusted folder `claude -p` ignores project
allow rules but still runs settings hooks, so the behaviour would differ from what is described here.
