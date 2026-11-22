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


def run(script, *args, env=None):
    import os
    base = {k: v for k, v in os.environ.items() if not k.startswith(("WREN_", "CLAUDE_PROJECT_DIR"))}
    return subprocess.run([NODE, str(script), *map(str, args)], capture_output=True, text=True, timeout=60, env={**base, **(env or {})})


def build(d, *extra, date=DATE):
    return run(BUILD, "--date", date, "--dir", d, *extra, env={"CLAUDE_PROJECT_DIR": str(d)})


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


def test_merge_duplicate_accept_self_merge_and_dedupe(d):
    ok = {"type": "merge_duplicate", "title": "Merge", "details": {"keep": "AAAA1111", "merge_keys": ["BBBB2222", "CCCC3333"]}}
    same = {"type": "merge_duplicate", "title": "Merge again", "details": {"keep": "AAAA1111", "merge": ["CCCC3333"], "remove": "BBBB2222"}}
    selfm = {"type": "merge_duplicate", "title": "Self", "details": {"keep": "AAAA1111", "merge_keys": ["AAAA1111"]}}
    empty = {"type": "merge_duplicate", "title": "Empty", "details": {"keep": "AAAA1111"}}
    write(d, f"cataloguer_{DATE}.proposals.json", cat_file([ok, same, selfm, empty]))
    p = build(d)
    assert p.returncode == 0, p.stderr
    q = queue(d)
    assert len(q["actions"]) == 1 and q["actions"][0]["details"]["merge_keys"] == ["BBBB2222", "CCCC3333"]
    assert len(rejected(d)["rejected"]) == 2 and len(rejected(d)["duplicates_dropped"]) == 1
    assert run(QUEUE, "status", d / f"approval_queue_{DATE}.json").returncode == 0


@pytest.mark.parametrize("doi", ["10.12", "not-a-doi", "https://doi.org/abc"])
def test_invalid_doi_rejected(d, doi):
    bad_add = {"type": "add_item", "title": "x", "details": {"DOI": doi, "title": "T"}}
    bad_fix = {"type": "fix_metadata", "title": "x", "details": {"item_key": "K1", "field_fixes": [{"field": "DOI", "proposed": doi}]}}
    flat = {"type": "fix_metadata", "title": "x", "details": {"item_key": "K1", "field": "doi", "proposed": doi}}
    write(d, f"scout_{DATE}.proposals.json", scout_file([bad_add, bad_fix, flat, TAG]))
    assert build(d).returncode == 0
    assert len(queue(d)["actions"]) == 1
    assert len(rejected(d)["rejected"]) == 3


def test_doi_normalised_under_any_spelling(d):
    a = {"type": "add_item", "title": "x", "details": {"DOI": "HTTPS://DOI.ORG/10.1234/ABC", "title": "T"}}
    f = {"type": "fix_metadata", "title": "x", "details": {"item_key": "K1", "field_fixes": [{"field": "DOI", "proposed": "doi:10.1234/XYZ"}]}}
    write(d, f"scout_{DATE}.proposals.json", scout_file([a, f]))
    assert build(d).returncode == 0
    acts = queue(d)["actions"]
    assert acts[0]["details"]["doi"] == "10.1234/abc" and "DOI" not in acts[0]["details"]
    assert acts[1]["details"]["proposed_changes"]["DOI"] == "10.1234/xyz"


def test_dedupe_per_field_and_per_tag(d):
    f1 = {"type": "fix_metadata", "title": "a", "details": {"item_key": "K1", "proposed_changes": {"pages": "1-2"}}}
    f2 = {"type": "fix_metadata", "title": "b", "details": {"item_key": "K1", "proposed_changes": {"pages": "1-2", "abstract": "Real text"}}}
    f3 = {"type": "fix_metadata", "title": "c", "details": {"item_key": "K1", "proposed_changes": {"pages": "9"}}}
    t1 = {"type": "add_tag", "title": "t", "details": {"item_key": "K1", "tags": ["Alpha", " alpha ", "beta"]}}
    t2 = {"type": "add_tag", "title": "t2", "details": {"item_key": "K1", "tags": ["ALPHA", "gamma"]}}
    write(d, f"cataloguer_{DATE}.proposals.json", cat_file([f1, f2, f3, t1, t2]))
    assert build(d).returncode == 0
    acts = queue(d)["actions"]
    assert acts[1]["details"]["proposed_changes"] == {"abstract": "Real text"}
    assert acts[2]["details"]["tags"] == ["Alpha", "beta"]
    assert acts[3]["details"]["tags"] == ["gamma"]
    assert len(acts) == 4 and len(rejected(d)["duplicates_dropped"]) == 1


def test_authors_must_be_array(d):
    s = {"type": "add_item", "title": "x", "details": {"doi": "10.1234/a", "authors": "Doe, Jane"}}
    ok = {"type": "add_item", "title": "y", "details": {"doi": "10.1234/b", "authors": ["Doe, Jane", {"given": "J", "family": "Roe"}]}}
    write(d, f"scout_{DATE}.proposals.json", scout_file([s, ok]))
    assert build(d).returncode == 0
    assert len(queue(d)["actions"]) == 1 and "authors" in rejected(d)["rejected"][0]["reason"]


def test_empty_actions_exit_zero_no_queue(d):
    write(d, f"cataloguer_{DATE}.proposals.json", cat_file([]))
    p = build(d)
    assert p.returncode == 0 and "no actions proposed" in p.stdout
    assert not (d / f"approval_queue_{DATE}.json").exists()


# --- unattended guard and output-path confinement
def lib_dir(root):
    d = root / "outputs" / "librarian"
    d.mkdir(parents=True)
    return d


def test_unattended_force_is_refused(tmp_path):
    d = lib_dir(tmp_path)
    write(d, f"cataloguer_{DATE}.proposals.json", cat_file([TAG]))
    env = {"CLAUDE_PROJECT_DIR": str(tmp_path), "WREN_UNATTENDED": "1"}
    assert run(BUILD, "--date", DATE, "--dir", d, env=env).returncode == 0
    p = run(BUILD, "--date", DATE, "--dir", d, "--force", env=env)
    assert p.returncode == 1 and "refused: unattended run" in p.stderr


def test_unattended_dir_and_out_must_be_inside_outputs_librarian(tmp_path):
    d = lib_dir(tmp_path)
    write(d, f"cataloguer_{DATE}.proposals.json", cat_file([TAG]))
    other = tmp_path / "elsewhere"
    other.mkdir()
    write(other, f"cataloguer_{DATE}.proposals.json", cat_file([TAG]))
    env = {"CLAUDE_PROJECT_DIR": str(tmp_path), "WREN_UNATTENDED": "1"}
    assert run(BUILD, "--date", DATE, "--dir", other, env=env).returncode == 1
    p = run(BUILD, "--date", DATE, "--dir", d, "--out", tmp_path / "q.json", env=env)
    assert p.returncode == 1 and "outputs/librarian" in p.stderr and not (tmp_path / "q.json").exists()
    assert run(BUILD, "--date", DATE, "--dir", d, "--out", d / "approval_queue_x.json", env=env).returncode == 0


def test_attended_dir_and_out_must_still_be_inside_the_project(tmp_path):
    root = tmp_path / "proj"
    d = lib_dir(root)
    write(d, f"cataloguer_{DATE}.proposals.json", cat_file([TAG]))
    outside = tmp_path / "outside.json"
    env = {"CLAUDE_PROJECT_DIR": str(root)}
    p = run(BUILD, "--date", DATE, "--dir", d, "--out", outside, env=env)
    assert p.returncode == 1 and "project root" in p.stderr and not outside.exists()
    assert run(BUILD, "--date", DATE, "--dir", tmp_path, env=env).returncode == 1
    assert run(BUILD, "--date", DATE, "--dir", d, env=env).returncode == 0


# --- source_agent comes from the filename; a disagreeing agent field is a warning
def test_source_agent_from_filename_with_mismatch_warning(tmp_path):
    write(tmp_path, f"scout_{DATE}.proposals.json", {"agent": "librarian-cataloguer", "generated": DATE, "actions": [TAG]})
    write(tmp_path, f"mystery_{DATE}.proposals.json", {"agent": "librarian-scout", "generated": DATE, "actions": [FIX]})
    p = build(tmp_path)
    assert p.returncode == 0, p.stderr
    acts = queue(tmp_path)["actions"]
    assert {a["type"]: a["source_agent"] for a in acts} == {"add_tag": "librarian-scout", "fix_metadata": "unknown"}
    assert "WARNING" in p.stdout and "librarian-cataloguer" in p.stdout


def test_dangling_symlink_output_is_refused_unattended(tmp_path):
    lib = lib_dir(tmp_path)
    write(lib, f"cataloguer_{DATE}.proposals.json", cat_file([TAG]))
    (lib / f"approval_queue_{DATE}.json").symlink_to(tmp_path / "nowhere.json")
    p = run(BUILD, "--date", DATE, "--dir", lib, "--out", lib / f"approval_queue_{DATE}.json",
            env={"CLAUDE_PROJECT_DIR": str(tmp_path), "WREN_UNATTENDED": "1"})
    assert p.returncode == 1 and not (tmp_path / "nowhere.json").exists()
