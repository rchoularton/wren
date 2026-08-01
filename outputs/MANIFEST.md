# Outputs Manifest

Registry of every directory under `outputs/`. Add a one-line entry when you create a new output directory (enforced by `.claude/rules/outputs.md` and the post-write hook). This keeps `outputs/` from sprawling into version-ambiguous duplicates.

**Status key:** `authoritative` · `current` · `stale` · `empty` · `archived`

| Directory | Status | What it holds | Produced by |
|-----------|--------|---------------|-------------|
| `_logs/` | current | Processing logs from scripts | (various) |

_Add rows as you create output directories. Name directories after the analysis script (snake_case)._
