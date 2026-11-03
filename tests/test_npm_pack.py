"""Guard the published tarball: contributor-only files stay out, core files stay in."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(shutil.which("npm") is None, reason="npm not on PATH")
def test_pack_contents():
    out = subprocess.run(
        ["npm", "pack", "--dry-run", "--json"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    paths = {f["path"] for f in json.loads(out)[0]["files"]}

    bad = sorted(
        p for p in paths
        if p.startswith(("tests/", ".github/")) or p == "requirements-dev.txt"
    )
    assert not bad, f"excluded paths in tarball: {bad}"

    for required in (
        "bin/create-wren.mjs",
        ".claude/settings.json",
        "papers/example-paper/STATUS.md",
    ):
        assert required in paths, f"missing from tarball: {required}"
