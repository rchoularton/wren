"""Approval queue, Crossref-typed items and duplicate detection, driven through `node` with a fake fetch.

Nothing here reaches the network: every call goes through tests/node/fake-fetch.mjs, which logs it.
Each run asserts that no call was unmatched (an unmatched call would be a request nobody planned for).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from urllib.parse import quote

import pytest
from conftest import REPO_ROOT

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node not installed")

FAKE = REPO_ROOT / "tests" / "node" / "fake-fetch.mjs"
LDRIVER = REPO_ROOT / "tests" / "node" / "librarian-driver.mjs"
QUEUE = REPO_ROOT / "scripts" / "zotero" / "approval-queue.mjs"
DUPES = REPO_ROOT / "scripts" / "zotero" / "detect-duplicates.mjs"
EXAMPLE = REPO_ROOT / "scripts" / "zotero" / "examples" / "approval-queue.example.json"
TYPE_FIELDS = json.loads((REPO_ROOT / "tests" / "data" / "zotero-type-fields.json").read_text())
LIB = "https://api.zotero.org/users/42"


class Run:
    def __init__(self, tmp_path):
        self.root = tmp_path / "proj"
        self.root.mkdir()
        self.fixture = tmp_path / "fixture.json"
        self.log = tmp_path / "calls.jsonl"

    def go(self, script, args, routes=()):
        self.fixture.write_text(json.dumps({"routes": list(routes)}))
        self.log.write_text("")
        base = {k: v for k, v in os.environ.items()
                if not k.startswith(("ZOTERO_", "UNPAYWALL_", "CROSSREF_", "INSTITUTION_", "WREN_", "CLAUDE_PROJECT_DIR"))}
        env = {**base, "CLAUDE_PROJECT_DIR": str(self.root), "ZOTERO_API_KEY": "key", "ZOTERO_LIBRARY_ID": "42",
               "WREN_FAKE_FETCH": str(FAKE), "WREN_FAKE_FETCH_FIXTURE": str(self.fixture), "WREN_FAKE_FETCH_LOG": str(self.log)}
        proc = subprocess.run([NODE, str(script), *map(str, args)], capture_output=True, text=True, env=env, timeout=60)
        unmatched = [c for c in self.calls if not c["matched"]]
        assert not unmatched, f"unmatched (would-be network) calls: {unmatched}"
        return proc

    @property
    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines() if line]

    def writes(self):
        return [c for c in self.calls if c["method"] != "GET"]


@pytest.fixture
def run(tmp_path):
    return Run(tmp_path)


def write_queue(run, actions, name="queue.json"):
    p = run.root / name
    p.write_text(json.dumps({"date": "2026-01-15", "actions": actions}, indent=2))
    return p


def load(p):
    return json.loads(p.read_text())


def zitem(key, itemType="journalArticle", version=3, **data):
    return {"key": key, "version": version, "data": {"key": key, "version": version, "itemType": itemType, "tags": [], "collections": [], **data}}


def get_item(key, item=None, sequence=None):
    route = {"method": "GET", "url": f"{LIB}/items/{key}"}
    if sequence:
        route["sequence"] = [{"json": s} for s in sequence]
    else:
        route["response"] = {"json": item}
    return route


def patch_ok(key, status=204):
    return {"method": "PATCH", "url": f"{LIB}/items/{key}", "response": {"status": status, "text": "" if status == 204 else "conflict"}}


def type_fields(item_type, fields):
    return {"method": "GET", "url": f"itemTypeFields?itemType={item_type}", "response": {"json": [{"field": f} for f in fields]}}


def crossref(doi, response):
    return {"method": "GET", "url": f"api.crossref.org/works/{quote(doi, safe='')}", "response": response}


def post_items(key="NEWKEY01"):
    return {"method": "POST", "url": f"{LIB}/items", "response": {"status": 200, "json": {"successful": {"0": {"key": key}}, "failed": {}}}}


def add_item_action(doi="10.1234/example.1", **extra):
    return {"id": 1, "type": "add_item", "status": "pending", "title": "Add", "paper": "paper-a",
            "details": {"doi": doi, "title": "Proposer title", "authors": ["Doe, Jane"], "venue": "Proposer Journal", "date": "2026", "relevance": "high", **extra}}


# (a) status
def test_status_prints_counts_by_status_and_type(run):
    p = run.go(QUEUE, ["status", EXAMPLE])
    assert p.returncode == 0, p.stderr
    out = p.stdout
    assert "Total actions: 5" in out
    assert "pending: 4" in out and "approved: 1" in out
    for t in ("add_item", "fix_metadata", "add_tag", "add_to_collection", "merge_duplicate"):
        assert f"{t}: 1" in out
    assert run.calls == []


# (b) reject / skip persist
def test_reject_and_skip_persist_with_decided_at(run):
    q = write_queue(run, [{"id": 1, "type": "add_tag", "status": "pending", "details": {}},
                          {"id": 2, "type": "add_tag", "status": "pending", "details": {}}])
    assert run.go(QUEUE, ["reject", 1, q, "off", "topic"]).returncode == 0
    assert run.go(QUEUE, ["skip", 2, q]).returncode == 0
    a = {x["id"]: x for x in load(q)["actions"]}
    assert a[1]["status"] == "rejected" and a[1]["reason"] == "off topic" and a[1]["decided_at"]
    assert a[2]["status"] == "skipped" and a[2]["decided_at"] and "reason" not in a[2]
    assert "pending" not in run.go(QUEUE, ["status", q]).stdout.split("By type")[0]
    assert run.calls == []


# (c) add_item typed from Crossref
def test_add_item_journal_article_from_crossref(run):
    q = write_queue(run, [add_item_action("10.1234/journal.1")])
    work = {"message": {"type": "journal-article", "title": ["Crossref journal title"], "container-title": ["Journal of Tests"], "DOI": "10.1234/journal.1",
                        "volume": "7", "issued": {"date-parts": [[2025]]}, "author": [{"given": "A", "family": "Author"}]}}
    stored = zitem("NEWKEY01", "journalArticle", title="Crossref journal title", DOI="10.1234/journal.1",
                   tags=[{"tag": "librarian-team"}, {"tag": "source-paper-a"}, {"tag": "relevance-high"}])
    p = run.go(QUEUE, ["approve", 1, q], [crossref("10.1234/journal.1", {"json": work}), post_items(), get_item("NEWKEY01", stored)])
    assert p.returncode == 0, p.stderr
    sent = json.loads(run.writes()[0]["body"])[0]
    assert sent["itemType"] == "journalArticle" and sent["publicationTitle"] == "Journal of Tests"
    assert {t["tag"] for t in sent["tags"]} == {"librarian-team", "source-paper-a", "relevance-high"}
    assert len(run.writes()) == 1
    calls = run.calls
    post_i = next(i for i, c in enumerate(calls) if c["method"] == "POST")
    assert any(c["url"].endswith("/items/NEWKEY01") for c in calls[post_i + 1:]), "no re-read after the create"
    act = load(q)["actions"][0]
    assert act["status"] == "applied" and act["result"]["source"] == "crossref" and act["result"]["verified"] is True


def test_add_item_book_chapter_has_no_journal_only_field(run):
    q = write_queue(run, [add_item_action("10.1234/chapter.1")])
    work = {"message": {"type": "book-chapter", "title": ["A chapter"], "container-title": ["Series name", "The Book"], "publisher": "Pub", "DOI": "10.1234/chapter.1",
                        "page": "10-20", "author": [{"given": "A", "family": "Author"}]}}
    stored = zitem("NEWKEY01", "bookSection", title="A chapter", DOI="10.1234/chapter.1",
                   tags=[{"tag": "librarian-team"}, {"tag": "source-paper-a"}, {"tag": "relevance-high"}])
    p = run.go(QUEUE, ["approve", 1, q], [crossref("10.1234/chapter.1", {"json": work}), post_items(), get_item("NEWKEY01", stored)])
    assert p.returncode == 0, p.stderr
    sent = json.loads(run.writes()[0]["body"])[0]
    assert sent["itemType"] == "bookSection" and sent["bookTitle"] == "The Book"
    for journal_only in ("publicationTitle", "issue", "ISSN"):
        assert journal_only not in sent
    allowed = set(TYPE_FIELDS["fields"]["bookSection"]) | set(TYPE_FIELDS["itemKeys"])
    assert set(sent) <= allowed
    assert load(q)["actions"][0]["status"] == "applied"


# (d) Crossref unreachable -> proposer metadata
def test_add_item_falls_back_to_proposer_metadata_when_crossref_unreachable(run):
    q = write_queue(run, [add_item_action("10.1234/down.1")])
    stored = zitem("NEWKEY01", "journalArticle", title="Proposer title", DOI="10.1234/down.1",
                   tags=[{"tag": "librarian-team"}, {"tag": "source-paper-a"}, {"tag": "relevance-high"}])
    p = run.go(QUEUE, ["approve", 1, q], [crossref("10.1234/down.1", {"status": 503, "text": "down"}), post_items(), get_item("NEWKEY01", stored)])
    assert p.returncode == 0, p.stderr
    sent = json.loads(run.writes()[0]["body"])[0]
    assert sent["itemType"] == "journalArticle" and sent["title"] == "Proposer title" and sent["publicationTitle"] == "Proposer Journal"
    assert sent["creators"] == [{"creatorType": "author", "firstName": "Jane", "lastName": "Doe"}]
    act = load(q)["actions"][0]
    assert act["status"] == "applied" and act["result"]["source"] == "proposer"


# (e) fix_metadata: placeholders refused, invalid fields dropped
@pytest.mark.parametrize("value", ["", "unknown", "n/a", "TBD", "N/A", "Fetch from Crossref"])
def test_fix_metadata_refuses_placeholder_values(run, value):
    q = write_queue(run, [{"id": 1, "type": "fix_metadata", "status": "approved", "details": {"item_key": "ABCD2345", "proposed_changes": {"abstract": value}}}])
    p = run.go(QUEUE, ["approve", 1, q])
    assert p.returncode == 2
    act = load(q)["actions"][0]
    assert act["status"] == "failed" and "placeholder" in act["error"]
    assert run.calls == []  # refused before any request


def test_fix_metadata_drops_field_invalid_for_item_type_with_warning(run):
    q = write_queue(run, [{"id": 1, "type": "fix_metadata", "status": "approved", "details": {"item_key": "CHAP0001", "proposed_changes": {"abstract": "A real abstract.", "journal": "Not for chapters"}}}])
    before = zitem("CHAP0001", "bookSection", title="T")
    after = zitem("CHAP0001", "bookSection", version=4, title="T", abstractNote="A real abstract.")
    routes = [type_fields("bookSection", ["title", "abstractNote", "bookTitle"]), get_item("CHAP0001", sequence=[before, after]), patch_ok("CHAP0001")]
    p = run.go(QUEUE, ["approve", 1, q], routes)
    assert p.returncode == 0, p.stderr
    assert "warning" in p.stderr and "journal" in p.stderr
    patch = json.loads(run.writes()[0]["body"])
    assert patch == {"abstractNote": "A real abstract."}
    assert run.writes()[0]["headers"]["If-Unmodified-Since-Version"] == "3"
    act = load(q)["actions"][0]
    assert act["status"] == "applied" and act["result"]["warnings"]


# (f) re-read mismatch -> failed
def test_write_whose_reread_does_not_match_is_failed_not_applied(run):
    q = write_queue(run, [{"id": 1, "type": "add_tag", "status": "approved", "details": {"item_key": "ABCD2345", "tags": ["topic-x"]}}])
    unchanged = zitem("ABCD2345", title="T")
    p = run.go(QUEUE, ["approve", 1, q], [get_item("ABCD2345", unchanged), patch_ok("ABCD2345")])
    assert p.returncode == 2
    act = load(q)["actions"][0]
    assert act["status"] == "failed" and "re-read" in act["error"] and "topic-x" in act["error"]


# (g) 412 -> failed, exit 2
def test_version_conflict_marks_failed_and_exits_2(run):
    q = write_queue(run, [{"id": 1, "type": "add_tag", "status": "approved", "details": {"item_key": "ABCD2345", "tags": ["topic-x"]}}])
    p = run.go(QUEUE, ["approve", 1, q], [get_item("ABCD2345", zitem("ABCD2345")), patch_ok("ABCD2345", 412)])
    assert p.returncode == 2
    act = load(q)["actions"][0]
    assert act["status"] == "failed" and "412" in act["error"]


# (h) reconcile
def reconcile_queue(run):
    return write_queue(run, [
        {"id": 1, "type": "add_tag", "status": "pending", "title": "done already", "details": {"item_key": "DONE0001", "tags": ["topic-x"]}},
        {"id": 2, "type": "add_tag", "status": "pending", "title": "still to do", "details": {"item_key": "TODO0001", "tags": ["topic-x"]}},
        {"id": 3, "type": "flag_review", "status": "pending", "title": "no executor", "details": {}},
    ])


RECON_ROUTES = [get_item("DONE0001", zitem("DONE0001", tags=[{"tag": "topic-x"}])), get_item("TODO0001", zitem("TODO0001"))]


def test_reconcile_dry_run_changes_nothing_and_apply_marks_satisfied(run):
    q = reconcile_queue(run)
    before = q.read_bytes()
    p = run.go(QUEUE, ["reconcile", q], RECON_ROUTES)
    assert p.returncode == 0, p.stderr
    assert "already_done: 1" in p.stdout and "outstanding: 1" in p.stdout and "dry run" in p.stdout
    assert q.read_bytes() == before
    assert run.writes() == []

    p = run.go(QUEUE, ["reconcile", q, "--apply"], RECON_ROUTES)
    assert p.returncode == 0, p.stderr
    a = {x["id"]: x for x in load(q)["actions"]}
    assert a[1]["status"] == "already_done" and a[1]["reconciled_at"]
    assert a[2]["status"] == "pending"
    assert a[3]["status"] == "needs-manual"
    assert run.writes() == []


# (i) approve-all
def test_approve_all_runs_only_approved_actions(run):
    q = write_queue(run, [
        {"id": 1, "type": "add_tag", "status": "approved", "details": {"item_key": "APPR0001", "tags": ["t"]}},
        {"id": 2, "type": "add_tag", "status": "pending", "details": {"item_key": "PEND0001", "tags": ["t"]}},
    ])
    after = zitem("APPR0001", tags=[{"tag": "t"}], version=4)
    routes = [get_item("APPR0001", sequence=[zitem("APPR0001"), after]), patch_ok("APPR0001")]
    p = run.go(QUEUE, ["approve-all", q], routes)
    assert p.returncode == 0, p.stderr
    a = {x["id"]: x for x in load(q)["actions"]}
    assert a[1]["status"] == "applied" and a[2]["status"] == "pending" and "applied_at" not in a[2]
    assert not any("PEND0001" in c["url"] for c in run.calls)


# (j) atomic save
def test_queue_file_intact_when_rename_fails(run):
    q = write_queue(run, [{"id": 1, "type": "add_tag", "status": "pending", "details": {}}])
    original = q.read_text()
    p = run.go(LDRIVER, ["save-fail", q])
    assert p.returncode == 0, p.stderr
    res = json.loads(p.stdout)
    assert res["thrown"] == "simulated rename failure"
    assert res["content"] == original
    assert res["leftovers"] == []


# (k) detect-duplicates
def top_item(key, title, doi=""):
    return {"key": key, "version": 1, "data": {"key": key, "itemType": "journalArticle", "title": title, "DOI": doi, "creators": [], "tags": [], "collections": []}}


DUP_ITEMS = [
    top_item("AAAA0001", "Completely unrelated study of soil carbon", "10.1234/Same.DOI"),
    top_item("AAAA0002", "Another unrelated heading about glaciers", "https://doi.org/10.1234/same.doi"),
    top_item("AAAA0003", "Forecast-based financing and early action in practice"),
    top_item("AAAA0004", "Forecast based financing and early action in practice."),
    top_item("AAAA0005", "A wholly different title concerning ocean currents"),
]


def test_detect_duplicates_groups_by_doi_and_title_and_never_writes(run):
    out = run.root / "outputs" / "librarian" / "dupes.json"
    p = run.go(DUPES, ["--out", out], [{"method": "GET", "url": "/items/top", "response": {"json": DUP_ITEMS}}])
    assert p.returncode == 0, p.stderr
    rep = json.loads(out.read_text())
    by = {c["method"]: c for c in rep["clusters"]}
    assert {i["key"] for i in by["doi"]["items"]} == {"AAAA0001", "AAAA0002"} and by["doi"]["doi"] == "10.1234/same.doi"
    assert {i["key"] for i in by["title-fuzzy"]["items"]} == {"AAAA0003", "AAAA0004"}
    assert rep["items_scanned"] == 5 and rep["duplicate_clusters"] == 2
    assert run.calls and all(c["method"] == "GET" for c in run.calls)


def test_detect_duplicates_honours_limit(run):
    routes = [{"method": "GET", "urlRegex": "limit=2&", "response": {"json": DUP_ITEMS[:2]}}]
    p = run.go(DUPES, ["--limit", 2], routes)
    assert p.returncode == 0, p.stderr
    assert json.loads(p.stdout)["items_scanned"] == 2
    assert all(c["method"] == "GET" and "limit=2&" in c["url"] for c in run.calls)


# (l) Crossref type mapping
def test_crossref_mapping_covers_every_type_in_the_field_lists(run):
    p = run.go(LDRIVER, ["crossref-map"])
    assert p.returncode == 0, p.stderr
    res = json.loads(p.stdout)
    assert res["unmapped"] is None
    assert set(res["mapping"].values()) == set(TYPE_FIELDS["fields"]), "mapped Zotero types and ported field lists differ"
    for cr_type, item in res["items"].items():
        allowed = set(TYPE_FIELDS["fields"][item["itemType"]]) | set(TYPE_FIELDS["itemKeys"])
        assert set(item) <= allowed, f"{cr_type}: invalid fields {set(item) - allowed}"
    assert "publicationTitle" not in res["items"]["book-chapter"]
    assert res["items"]["report"]["institution"] == "Pub"
