#!/usr/bin/env python3
"""Wren status report: the deterministic half of `/research`. Spends no model tokens.

Gathers two blocks:

  papers          every papers/*/STATUS.md frontmatter (phase, tier, status, next),
                  grouped by tier, the active paper (.current_paper) marked
  scheduled jobs  job keys discovered from outputs/_logs/<key>_<YYYY-MM-DD>.log,
                  each with its newest run, a one-word verdict from the log tail
                  (ok / failed / unknown) and whether it is overdue

Usage:
    python3 scripts/utils/wren_status.py            # summary: short Markdown (default)
    python3 scripts/utils/wren_status.py --full     # one line per paper and job
    python3 scripts/utils/wren_status.py --json     # machine-readable
    python3 scripts/utils/wren_status.py --repo DIR # project root (default: cwd)

Exit 0 on a valid project; exit 2 with a message if papers/ is missing.
Entry point for: npm run status
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

DEFAULT_CADENCE_DAYS = 8  # used when research-config.yml does not say how often a job runs

# Tier labels as they appear in STATUS.md frontmatter, in report order.
TIER_ORDER = {"1": 0, "active": 0, "2": 1, "3": 2, "optional": 3}

# ----------------------------------------------------------------- papers ---


def _unquote(value: str) -> str:
    """One YAML scalar: a quoted string keeps everything inside the quotes; an
    unquoted one loses a trailing `# comment`."""
    v = value.strip()
    if not v:
        return ""
    if v[0] in "\"'":
        q = v[0]
        end = v.find(q, 1)
        while end != -1 and v[end - 1] == "\\":
            end = v.find(q, end + 1)
        return v[1:end] if end != -1 else v[1:]
    return re.split(r"\s+#", v, maxsplit=1)[0].strip()


def parse_frontmatter(text: str) -> dict[str, str]:
    """The flat `key: value` lines between the first two `---` fences. Lists and
    nested maps are ignored; the report only needs scalars."""
    if not text.startswith("---"):
        return {}
    out: dict[str, str] = {}
    for line in text.splitlines()[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if not m or m.group(2).startswith(("[", "{")):
            continue
        out[m.group(1)] = _unquote(m.group(2))
    return out


@dataclass
class PaperRow:
    paper_id: str
    title: str
    journal: str
    phase: str
    tier: str
    status: str
    next: str
    path: str
    active: bool = False


def read_current_paper(repo: Path) -> str:
    try:
        return (repo / ".current_paper").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def collect_papers(papers_dir: Path, active: str = "") -> tuple[list[PaperRow], list[str]]:
    """(parsed rows ordered by tier then id, ids of STATUS.md files without frontmatter)."""
    rows: list[PaperRow] = []
    unparsed: list[str] = []
    for d in sorted(papers_dir.iterdir()):
        status = d / "STATUS.md"
        if not d.is_dir() or not status.is_file():
            continue
        fm = parse_frontmatter(status.read_text(encoding="utf-8", errors="replace"))
        if not fm:
            unparsed.append(d.name)
            continue
        pid = fm.get("paper_id") or d.name
        rows.append(PaperRow(
            paper_id=pid, title=fm.get("title", ""), journal=fm.get("journal", ""),
            phase=fm.get("phase", ""), tier=fm.get("tier", ""), status=fm.get("status", ""),
            next=fm.get("next", ""), path=str(status),
            active=bool(active) and active in (pid, d.name),
        ))
    rows.sort(key=lambda r: (TIER_ORDER.get(r.tier.lower(), 9), r.paper_id))
    return rows, unparsed


# ---------------------------------------------------------- scheduled jobs ---

_LOG_RE = re.compile(r"^(?P<key>.+)_(?P<date>\d{4}-\d{2}-\d{2})\.log$")
_OK_RE = re.compile(r"\bOK\b|\bdone\b|\bsuccess", re.I)
_FAIL_RE = re.compile(r"ERROR|FAIL|Traceback", re.I)


@dataclass
class JobRow:
    key: str
    last_run: str  # YYYY-MM-DD
    verdict: str   # ok | failed | unknown
    overdue: bool
    cadence_days: int
    log: str


def _tail(path: Path, n: int = 20) -> list[str]:
    try:
        data = path.read_bytes()[-20000:]
    except OSError:
        return []
    return data.decode("utf-8", errors="replace").splitlines()[-n:]


def verdict_from_tail(lines: list[str]) -> str:
    """The last non-empty line that carries a verdict word decides."""
    for line in reversed(lines):
        if _FAIL_RE.search(line):
            return "failed"
        if _OK_RE.search(line):
            return "ok"
    return "unknown"


def job_cadences(config: Path) -> dict[str, int]:
    """Cadence in days per job key from research-config.yml, without a YAML
    library: `scheduler.jobs.<key>` with a `day:` is weekly (7), without is daily (1).
    Anything unreadable is simply absent, and the caller falls back to the default."""
    try:
        lines = config.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    out: dict[str, int] = {}
    in_jobs, jobs_indent, key, key_indent = False, 0, None, 0
    for raw in lines:
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        text = line.strip()
        if re.match(r"^jobs:\s*$", text):
            in_jobs, jobs_indent, key = True, indent, None
            continue
        if not in_jobs:
            continue
        if indent <= jobs_indent:
            in_jobs, key = False, None
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*$", text)
        if m and (key is None or indent <= key_indent):
            key, key_indent = m.group(1), indent
            out[key] = 1
        elif key and re.match(r"^day:\s*\S", text):
            out[key] = 7
    return out


def collect_jobs(logs_dir: Path, cadences: dict[str, int], today: date) -> list[JobRow]:
    newest: dict[str, tuple[str, Path]] = {}
    if logs_dir.is_dir():
        for p in logs_dir.iterdir():
            m = _LOG_RE.match(p.name)
            if m and p.is_file() and (m["key"] not in newest or m["date"] > newest[m["key"]][0]):
                newest[m["key"]] = (m["date"], p)
    rows = []
    for key in sorted(newest):
        last, path = newest[key]
        cadence = cadences.get(key, DEFAULT_CADENCE_DAYS)
        # A daily or weekly job is overdue once it has missed a full extra day.
        limit = cadence + 1 if key in cadences else cadence
        try:
            overdue = (today - date.fromisoformat(last)).days > limit
        except ValueError:
            overdue = True
        rows.append(JobRow(key, last, verdict_from_tail(_tail(path)), overdue, cadence, str(path)))
    return rows


# ------------------------------------------------------------------ report ---


def build(repo: Path, today: date | None = None) -> dict:
    today = today or date.today()
    papers, unparsed = collect_papers(repo / "papers", read_current_paper(repo))
    jobs = collect_jobs(repo / "outputs" / "_logs", job_cadences(repo / "research-config.yml"), today)
    return {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "papers": [asdict(p) for p in papers],
        "unparsed": unparsed,
        "jobs": [asdict(j) for j in jobs],
    }


def _tier_label(t: str) -> str:
    t = t.lower()
    if t in ("1", "active"):
        return "Tier 1"
    if t == "optional":
        return "Optional"
    return f"Tier {t}" if t else "Untiered"


def _md(s: str) -> str:
    return (s or "").replace("\n", " ").strip()


def clip_next(text: str, limit: int = 90) -> str:
    """The first clause of a `next:` line (up to the first `;`), cut at `limit`
    with an ellipsis. The full text is in STATUS.md."""
    t = (text or "").strip()
    if not t:
        return "—"
    first = t.split(";", 1)[0].strip()
    if len(first) > limit:
        cut = first[: limit - 1]
        if " " in cut[limit // 2:]:
            cut = cut[: cut.rfind(" ")]
        if cut.count("(") > cut.count(")"):
            cut = cut[: cut.rfind("(")]
        first = cut.rstrip(" ,:;(") + " …"
    elif first != t:
        first += " …"
    return first


def readable_status(status: str) -> str:
    """`pipeline_complete-review_pending` -> `pipeline complete, review pending`."""
    t = re.sub(r"\s+", " ", (status or "").strip().replace("_", " ").replace("-", " "))
    t = re.sub(r"\b(complete|done|frozen|submitted) (?=\w)", r"\1, ", t)
    return t or "?"


def short_title(title: str, limit: int = 50) -> str:
    t = _md(title) or "(untitled)"
    return t if len(t) <= limit else t[: limit - 1].rstrip() + "…"


def _job_flags(j: dict) -> list[str]:
    flags = []
    if j["verdict"] != "ok":
        flags.append(j["verdict"])
    if j["overdue"]:
        flags.append("overdue")
    return flags


def render_summary(rep: dict) -> str:
    L: list[str] = ["**Papers** (▶ = active)"]
    cur = None
    for p in rep["papers"]:
        lab = _tier_label(p["tier"])
        if lab != cur:
            L += ["", f"**{lab}**"]
            cur = lab
        mark = "▶ " if p["active"] else ""
        L.append(f"- {mark}**{p['paper_id']}** · {short_title(p['title'])} — phase {p['phase'] or '?'}, "
                 f"{readable_status(p['status'])}. Next: {_md(clip_next(p['next']))}")
    if not rep["papers"]:
        L.append("- no papers with frontmatter yet")
    if rep["unparsed"]:
        L += ["", "**Unparsed** (STATUS.md has no frontmatter): " + ", ".join(rep["unparsed"])]
    L += ["", _jobs_summary(rep["jobs"])]
    for j in rep["jobs"]:
        flags = _job_flags(j)
        if flags:
            L.append(f"- {j['key']}: last run {j['last_run']} — {', '.join(flags)}")
    return "\n".join(L).rstrip() + "\n"


def _jobs_summary(jobs: list[dict]) -> str:
    if not jobs:
        return "**Scheduled jobs:** no scheduled jobs have run."
    fine = sum(1 for j in jobs if not _job_flags(j))
    return f"**Scheduled jobs:** {fine} of {len(jobs)} ok and on schedule."


def render_full(rep: dict) -> str:
    L: list[str] = ["## Papers"]
    cur = None
    for p in rep["papers"]:
        lab = _tier_label(p["tier"])
        if lab != cur:
            L.append(lab)
            cur = lab
        mark = "▶" if p["active"] else " "
        L.append(f" {mark} {p['paper_id']} · {_md(p['title']) or '(untitled)'} · {p['journal'] or '?'} · "
                 f"phase {p['phase'] or '?'} · {p['status'] or '?'}")
        L.append(f"      next: {p['next']}" if p["next"] else "      next: (none set)")
    if rep["unparsed"]:
        L.append("Unparsed (no frontmatter): " + ", ".join(rep["unparsed"]))
    L += ["", "## Scheduled jobs"]
    if not rep["jobs"]:
        L.append("no scheduled jobs have run.")
    for j in rep["jobs"]:
        L.append(f"  {j['key']:<24} last {j['last_run']}  {j['verdict']}"
                 f"{'  OVERDUE' if j['overdue'] else ''}  (expected every {j['cadence_days']}d)")
    return "\n".join(L).rstrip() + "\n"


def papers_table(rows: list[dict]) -> str:
    """Markdown table of id, title, journal, phase, status, for papers/README.md."""
    def cell(s: str) -> str:
        return _md(s).replace("|", "\\|") or "—"
    L = ["| Paper | Title | Journal | Phase | Status |", "|---|---|---|---|---|"]
    for p in rows:
        L.append(f"| `{p['paper_id']}` | {cell(p['title'])} | {cell(p['journal'])} | "
                 f"{cell(p['phase'])} | {cell(p['status'])} |")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--summary", action="store_true", help="short Markdown (default)")
    mode.add_argument("--full", action="store_true", help="one line per paper and job")
    mode.add_argument("--json", action="store_true", help="machine-readable")
    ap.add_argument("--repo", type=Path, default=None, help="project root (default: cwd)")
    ap.add_argument("--today", default=None, help=argparse.SUPPRESS)  # YYYY-MM-DD, for tests
    args = ap.parse_args(argv)
    repo = (args.repo or Path.cwd()).resolve()
    if not (repo / "papers").is_dir():
        print(f"wren_status: no papers/ directory in {repo}", file=sys.stderr)
        return 2
    rep = build(repo, date.fromisoformat(args.today) if args.today else None)
    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    elif args.full:
        sys.stdout.write(render_full(rep))
    else:
        sys.stdout.write(render_summary(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
