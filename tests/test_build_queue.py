"""scripts/zotero/build-queue.mjs: proposals files -> approval queue. Node via subprocess, temp dirs only."""
from __future__ import annotations

import json
import shutil
import subprocess

import pytest
from conftest import REPO_ROOT

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node not installed")

BUILD = REPO_ROOT / "scripts" / "zotero" / "build-queue.mjs"
QUEUE = REPO_ROOT / "scripts" / "zotero" / "approval-queue.mjs"
DATE = "2026-01-15"


def run(script, *args):
    return subprocess.run([NODE, str(script), *map(str, args)], capture_output=True, text=True, timeout=60)


def build(d, *extra, date=DATE):
    return run(BUILD, "--date", date, "--dir", d, *extra)


def write(d, name, obj):
    (d / name).write_text(obj if isinstance(obj, str) else json.dumps(obj))


def cat_file(actions):
    return {"agent": "librarian-cataloguer", "generated": DATE, "actions": actions}


def scout_file(actions):
    return {"agent": "librarian-scout", "generated": DATE, "actions": actions}


TAG = {"type": "add_tag", "title": "Tag", "details": {"item_key": "ABCD2345", "tags": ["topic-x"]}}
FIX = {"type": "fix_metadata", "title": "Fix", "details": {"item_key": "ABCD2345", "proposed_changes": {"pages": "1-9"}}}
COLL = {"type": "add_to_collection", "title": "File", "details": {"item_key": "ABCD2345", "collection_key": "COLL0001"}}
ADD = {"type": "add_item", "title": "Add: A", "paper": "p1", "details": {"doi": "10.1234/abc", "title": "A", "relevance": "high"}}


@pytest.fixture
def d(tmp_path):
    return tmp_path


def queue(d):
    return json.loads((d / f"approval_queue_{DATE}.json").read_text())


def rejected(d):
    return json.loads((d / f"rejected_{DATE}.json").read_text())


def test_merge_two_files(d):
    write(d, f"cataloguer_{DATE}.proposals.json", cat_file([FIX, TAG, COLL]))
    write(d, f"scout_{DATE}.proposals.json", scout_file([ADD]))
    p = build(d)
    assert p.returncode == 0, p.stderr
    q = queue(d)
    assert [a["id"] for a in q["actions"]] == [1, 2, 3, 4]
    assert all(a["status"] == "pending" for a in q["actions"])
    assert [a["source_agent"] for a in q["actions"]] == ["librarian-cataloguer"] * 3 + ["librarian-scout"]
    assert q["date"] == DATE


@pytest.mark.parametrize("bad,reason", [
    ({"type": "flag_thing", "title": "x", "details": {}}, "unknown"),
    ({"type": "fix_metadata", "title": "x", "details": {"proposed_changes": {"pages": "1-2"}}}, "item_key"),
    ({"type": "fix_metadata", "title": "x", "details": {"item_key": "ABCD2345", "proposed_changes": {"abstract": "Fetch from Crossref"}}}, "placeholder"),
    ({"type": "add_item", "title": "x", "details": {"venue": "J"}}, "title or a DOI"),
])
def test_rejections(d, bad, reason):
    write(d, f"cataloguer_{DATE}.proposals.json", cat_file([TAG, bad]))
    p = build(d)
    assert p.returncode == 0, p.stderr
    assert len(queue(d)["actions"]) == 1
    r = rejected(d)["rejected"]
    assert len(r) == 1 and reason in r[0]["reason"]
    assert reason in p.stdout


def test_duplicates_across_files(d):
    a = dict(ADD, details={"doi": "10.1234/ABC", "title": "A"})
    b = dict(ADD, details={"doi": "https://doi.org/10.1234/abc", "title": "A again"})
    write(d, f"cataloguer_{DATE}.proposals.json", cat_file([TAG, FIX]))
    write(d, f"scout_{DATE}.proposals.json", scout_file([a, b, dict(TAG), dict(FIX)]))
    p = build(d)
    assert p.returncode == 0, p.stderr
    q = queue(d)
    assert len(q["actions"]) == 3  # TAG, FIX (first file), one add_item
    assert q["actions"][2]["details"]["doi"] == "10.1234/abc"
    assert len(rejected(d)["duplicates_dropped"]) == 3


def test_no_overwrite_without_force(d):
    write(d, f"cataloguer_{DATE}.proposals.json", cat_file([TAG]))
    assert build(d).returncode == 0
    p = build(d)
    assert p.returncode == 1 and "--force" in p.stderr
    assert build(d, "--force").returncode == 0


def test_force_refuses_after_decision(d):
    write(d, f"cataloguer_{DATE}.proposals.json", cat_file([TAG]))
    assert build(d).returncode == 0
    qf = d / f"approval_queue_{DATE}.json"
    q = json.loads(qf.read_text())
    q["actions"][0]["status"] = "rejected"
    qf.write_text(json.dumps(q))
    p = build(d, "--force")
    assert p.returncode == 1 and "no longer pending" in p.stderr
    assert json.loads(qf.read_text())["actions"][0]["status"] == "rejected"


def test_no_proposals_file(d):
    p = build(d)
    assert p.returncode == 1 and "No proposals file" in p.stderr


def test_missing_date_is_argument_error(d):
    assert run(BUILD, "--dir", d).returncode == 1


def test_queue_accepted_by_approval_queue_status(d):
    write(d, f"cataloguer_{DATE}.proposals.json", cat_file([FIX, TAG, COLL]))
    write(d, f"scout_{DATE}.proposals.json", scout_file([ADD]))
    assert build(d).returncode == 0
    p = run(QUEUE, "status", d / f"approval_queue_{DATE}.json")
    assert p.returncode == 0, p.stderr
    assert "4" in p.stdout


def test_malformed_json_reported_other_file_processed(d):
    write(d, f"cataloguer_{DATE}.proposals.json", "{not json")
    write(d, f"scout_{DATE}.proposals.json", scout_file([ADD]))
    p = build(d)
    assert p.returncode == 0, p.stderr
    assert f"cataloguer_{DATE}.proposals.json" in p.stdout
    assert len(queue(d)["actions"]) == 1
    assert rejected(d)["file_errors"]
