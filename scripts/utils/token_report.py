#!/usr/bin/env python3
"""Token / model-routing report for this project's Claude Code sessions.

Answers "how did routing actually perform?" from the local session transcripts —
no API, no external service, nothing leaves your machine. Aggregates assistant
turns by model, and (with --by-agent) attributes them to the main loop vs each
sub-agent, so you can see whether cheap-tier work really ran on a cheap model.

Usage:
  python scripts/utils/token_report.py                # today
  python scripts/utils/token_report.py --date today   # same as no argument
  python scripts/utils/token_report.py --date 2026-08-01
  python scripts/utils/token_report.py --since 7      # last 7 days (inclusive)
  python scripts/utils/token_report.py --by-agent     # break down by agent role
  python scripts/utils/token_report.py --logs-dir /path/to/project/logs

Source: Claude Code writes one JSONL per session under
  ~/.claude/projects/<mangled-project-path>/            (main loop)
  ~/.claude/projects/<mangled-project-path>/*/subagents/ (sub-agents)
where <mangled-project-path> is the absolute project path with '/' -> '-'.
Each assistant event carries message.model and message.usage.

Note: token counts are a COST PROXY, not billed dollars — strong-model output
costs several times the mid model's per token and far above the cheap model's,
so a model's share of output tokens understates its share of spend.
"""
import argparse
import collections
import glob
import json
import os
import time


def default_logs_dir() -> str:
    root = os.getcwd()
    mangled = root.replace("/", "-")
    return os.path.expanduser(f"~/.claude/projects/{mangled}")


def wanted_dates(args) -> set:
    """Set of 'YYYY-MM-DD' strings to include."""
    if args.since is not None:
        now = time.time()
        return {
            time.strftime("%Y-%m-%d", time.localtime(now - d * 86400))
            for d in range(args.since)
        }
    d = args.date
    if not d or d == "today":
        d = time.strftime("%Y-%m-%d")
    elif d == "yesterday":
        d = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
    else:
        try:
            time.strptime(d, "%Y-%m-%d")
        except ValueError:
            raise SystemExit(f"--date must be YYYY-MM-DD, 'today', or 'yesterday' (got {d!r})")
    return {d}


def meta_for(subjsonl: str) -> dict:
    m = subjsonl[:-6] + ".meta.json"
    if os.path.exists(m):
        try:
            return json.load(open(m))
        except Exception:
            return {}
    return {}


def collect(logs_dir: str, dates: set, by_agent: bool):
    # (label) -> model -> [turns, out, inp, cache_read, cache_write]
    agg = collections.defaultdict(
        lambda: collections.defaultdict(lambda: [0, 0, 0, 0, 0])
    )
    # earliest window bound so we can skip files untouched in range
    t_lo = min(
        time.mktime(time.strptime(d + " 00:00:00", "%Y-%m-%d %H:%M:%S")) for d in dates
    )

    rows = []  # (label, path)
    for f in glob.glob(os.path.join(logs_dir, "*.jsonl")):
        if os.path.getmtime(f) >= t_lo:
            rows.append(("main-loop", f))
    for f in glob.glob(os.path.join(logs_dir, "*/subagents/*.jsonl")):
        if os.path.getmtime(f) < t_lo:
            continue
        if by_agent:
            md = meta_for(f)
            st = (
                md.get("subagentType")
                or md.get("subagent_type")
                or md.get("agentType")
                or "?"
            )
            rows.append((f"sub:{st}", f))
        else:
            rows.append(("sub-agent", f))

    for label, f in rows:
        try:
            lines = open(f, encoding="utf-8").read().splitlines()
        except Exception:
            continue
        for ln in lines:
            if not ln.strip():
                continue
            try:
                e = json.loads(ln)
            except Exception:
                continue
            if e.get("type") != "assistant":
                continue
            if e.get("timestamp", "")[:10] not in dates:
                continue
            m = e.get("message") or {}
            if not isinstance(m, dict):
                continue
            model = (m.get("model") or "unknown").replace("claude-", "")
            u = m.get("usage") or {}
            key = (label, os.path.basename(f)[:14]) if by_agent else label
            cell = agg[key][model]
            cell[0] += 1
            cell[1] += u.get("output_tokens", 0)
            cell[2] += u.get("input_tokens", 0)
            cell[3] += u.get("cache_read_input_tokens", 0)
            cell[4] += u.get("cache_creation_input_tokens", 0)
    return agg


def print_by_model(agg):
    totals = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
    for _, models in agg.items():
        for model, c in models.items():
            t = totals[model]
            for i in range(5):
                t[i] += c[i]
    grand_out = sum(t[1] for t in totals.values()) or 1
    hdr = f"{'model':16} {'turns':>6} {'out_tok':>11} {'in_tok':>9} {'cache_rd':>12} {'cache_wr':>11} {'out%':>6}"
    print(hdr)
    print("-" * len(hdr))
    for model, t in sorted(totals.items(), key=lambda kv: -kv[1][1]):
        print(
            f"{model:16} {t[0]:>6} {t[1]:>11,} {t[2]:>9,} {t[3]:>12,} {t[4]:>11,} {100*t[1]/grand_out:>5.1f}%"
        )
    g = [sum(t[i] for t in totals.values()) for i in range(5)]
    print("-" * len(hdr))
    print(f"{'TOTAL':16} {g[0]:>6} {g[1]:>11,} {g[2]:>9,} {g[3]:>12,} {g[4]:>11,} {100.0:>5.1f}%")


def print_by_agent(agg):
    hdr = f"{'agent (role / id)':34} {'model':16} {'turns':>6} {'out_tok':>10}"
    print(hdr)
    print("-" * len(hdr))
    for (label, short), models in sorted(
        agg.items(), key=lambda kv: -sum(v[1] for v in kv[1].values())
    ):
        for model, c in sorted(models.items(), key=lambda kv: -kv[1][1]):
            print(f"{(label + ' ' + short):34} {model:16} {c[0]:>6} {c[1]:>10,}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--date", help="YYYY-MM-DD, or 'today'/'yesterday' (default: today, local time)")
    g.add_argument("--since", type=int, help="last N days, inclusive of today")
    ap.add_argument("--by-agent", action="store_true", help="break down by agent role instead of by model")
    ap.add_argument("--logs-dir", default=None, help="override the Claude Code project logs dir")
    args = ap.parse_args()

    logs_dir = args.logs_dir or default_logs_dir()
    if not os.path.isdir(logs_dir):
        raise SystemExit(f"logs dir not found: {logs_dir}\n(run from the project root, or pass --logs-dir)")

    dates = wanted_dates(args)
    span = f"since {args.since}d" if args.since is not None else (args.date or "today")
    agg = collect(logs_dir, dates, args.by_agent)

    print(f"token report — {span}  ({min(dates)}..{max(dates)})   logs: {logs_dir}")
    print()
    if args.by_agent:
        print_by_agent(agg)
    else:
        print_by_model(agg)
    print()
    print("note: token counts are a cost proxy, not billed dollars (strong-model output >> mid >> cheap per token).")


if __name__ == "__main__":
    main()
