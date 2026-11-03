"""Guards for the standing-context diet (#21).

1. Size budget: the total measured by scripts/utils/context_size.py must stay at
   or below BUDGET_BYTES, so a future PR cannot silently regrow what loads into
   every session.
2. Obligations: no sentence containing MUST, never, always or "do not" may be
   removed from a rule file.
"""
from __future__ import annotations

import importlib.util
import json
import re

from conftest import REPO_ROOT

# The measured total (32,240 bytes at the diet) rounded up to the next 1,000.
BUDGET_BYTES = 33_000

RULES = REPO_ROOT / ".claude" / "rules"
SNAPSHOT = REPO_ROOT / "tests" / "data" / "rule_obligations.json"
# "always-on" / "always-run-the-check" are names, not obligations, hence (?!-).
OBLIGATION = re.compile(r"\b(must|never|always(?!-)|do not)\b", re.I)


def _load_context_size():
    spec = importlib.util.spec_from_file_location(
        "context_size", REPO_ROOT / "scripts" / "utils" / "context_size.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _norm(s: str) -> str:
    s = re.sub(r"[*_`]", "", s)
    s = re.sub(r"^\s*(?:[-#>]+|\d+\.)\s*", "", s)
    return re.sub(r"\s+", " ", s).strip()


def obligation_sentences(text: str) -> list[str]:
    """Normalised sentences containing MUST / never / always / "do not".

    Frontmatter is ignored; markdown emphasis, bullet/heading markers and line
    wrapping are normalised away, so reflowing a rule does not count as a change.
    """
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)
    out = []
    for block in re.split(r"\n\s*\n|\n(?=\s*(?:[-*]|\d+\.)\s)", text):
        block = _norm(block.replace("\n", " "))
        for sent in re.split(r"(?<=[.!?:])\s+(?=[A-Z\"(])", block):
            if OBLIGATION.search(sent):
                out.append(_norm(sent))
    return out


def test_standing_context_within_budget():
    cs = _load_context_size()
    total = cs.total(cs.measure())
    assert total <= BUDGET_BYTES, (
        f"standing context is {total} bytes, over the {BUDGET_BYTES} budget; "
        "trim it (see docs/rules-history.md) or raise BUDGET_BYTES deliberately"
    )


def test_rules_keep_every_obligation_sentence():
    """Deterministic: compares against a committed snapshot, not live git state.

    tests/data/rule_obligations.json holds, per rule file, the obligation
    sentences found in `main` before the diet (`git show main:<file>`). Each must
    still appear, whitespace/markdown-normalised, in the same rule file. To change
    a rule's obligation on purpose, update the snapshot in the same PR.
    """
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    missing = []
    for name, sentences in snapshot.items():
        current = obligation_sentences((RULES / name).read_text(encoding="utf-8"))
        blob = " ".join(current)
        missing += [f"{name}: {s}" for s in sentences if s not in blob]
    assert not missing, "obligation sentences removed or reworded:\n" + "\n".join(missing)
