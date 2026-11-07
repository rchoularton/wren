"""Zotero client, /pdf-fill and reparent scripts, driven through `node` with a fake fetch.

Nothing here reaches the network: WREN_FAKE_FETCH points the scripts at
tests/node/fake-fetch.mjs, which answers from a JSON fixture and logs every call.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess

import pytest
from conftest import REPO_ROOT

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node not installed")

FAKE = REPO_ROOT / "tests" / "node" / "fake-fetch.mjs"
DRIVER = REPO_ROOT / "tests" / "node" / "driver.mjs"
PDF_FILL = REPO_ROOT / "scripts" / "zotero" / "pdf-fill.mjs"
REPARENT = REPO_ROOT / "scripts" / "zotero" / "reparent-orphan-attachments.mjs"
LIB = "https://api.zotero.org/users/42"
PDF2000 = b"%PDF-1.4\n" + b"A" * (2000 - 9)


@pytest.fixture
def proj(tmp_path):
    root = tmp_path / "my project"
    (root / "papers" / "paper-a").mkdir(parents=True)
    (root / "papers" / "paper-a" / "config.json").write_text(json.dumps({"zotero_collection": "COLL0001"}))
    return root


class Run:
    def __init__(self, tmp_path, proj):
        self.proj = proj
        self.fixture = tmp_path / "fixture.json"
        self.log = tmp_path / "calls.jsonl"

    def go(self, script, args, routes, email="me@example.org", extra_env=None, cmd=None):
        self.fixture.write_text(json.dumps({"routes": routes}))
        self.log.write_text("")
        base = {k: v for k, v in os.environ.items()
                if not k.startswith(("ZOTERO_", "UNPAYWALL_", "INSTITUTION_", "WREN_", "CLAUDE_PROJECT_DIR"))}
        env = {**base, "CLAUDE_PROJECT_DIR": str(self.proj), "ZOTERO_API_KEY": "key", "ZOTERO_LIBRARY_ID": "42",
               "WREN_FAKE_FETCH": str(FAKE), "WREN_FAKE_FETCH_FIXTURE": str(self.fixture),
               "WREN_FAKE_FETCH_LOG": str(self.log), **(extra_env or {})}
        if email:
            env["UNPAYWALL_EMAIL"] = email
        proc = subprocess.run([NODE, str(script), *args], capture_output=True, text=True, env=env, timeout=60)
        return proc

    @property
    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines() if line]


@pytest.fixture
def run(tmp_path, proj):
    return Run(tmp_path, proj)


def driver(run, *args, routes=(), env=None):
    p = run.go(DRIVER, list(args), list(routes), extra_env=env)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def item(key, title, doi=None, last="Smith", date="2020-05-01"):
    return {"key": key, "version": 1, "data": {"key": key, "itemType": "journalArticle", "title": title, "DOI": doi or "",
            "creators": [{"lastName": last, "firstName": "A"}], "date": date}}


def pdf_child(key):
    return {"key": key, "version": 2, "data": {"key": key, "itemType": "attachment", "contentType": "application/pdf",
            "md5": "abc", "filesize": 2000, "parentItem": "x"}}


def r(url=None, response=None, sequence=None, method="GET", regex=None, body=None):
    route = {"method": method}
    route["urlRegex" if regex else "url"] = regex or url
    if body:
        route["bodyIncludes"] = body
    if sequence:
        route["sequence"] = sequence
    else:
        route["response"] = response
    return route


def fill_routes():
    """Collection of three items: A has a PDF, B is on Unpaywall, C is nowhere."""
    return [
        r(f"{LIB}/collections/COLL0001/items/top", {"json": [item("AAAAAAAA", "Has pdf", "10.1/a"),
                                                              item("BBBBBBBB", "Open one", "10.1/b"),
                                                              item("CCCCCCCC", "Closed one", "10.1/c")]}),
        r(f"{LIB}/items/AAAAAAAA/children", {"json": [pdf_child("ATTA0001")]}),
        r(f"{LIB}/items/BBBBBBBB/children", sequence=[{"json": []}, {"json": [pdf_child("ATT00001")]}]),
        r(f"{LIB}/items/CCCCCCCC/children", {"json": []}),
        r("api.unpaywall.org/v2/10.1/b", {"json": {"best_oa_location": {"url_for_pdf": "https://oa.example/b.pdf"}}}),
        r("https://oa.example/b.pdf", {"bytes": 2000, "headers": {"content-type": "application/pdf"}}),
        r("api.unpaywall.org/v2/10.1/c", {"json": {"best_oa_location": None, "oa_locations": []}}),
        r("api.openalex.org/works/doi:10.1/b", {"json": {}}),
        r("api.openalex.org/works/doi:10.1/c", {"json": {}}),
        r("https://doi.org/10.1/b", {"text": "<html><head></head></html>"}),
        r("https://doi.org/10.1/c", {"text": "<html><head></head></html>"}),
        # Writes (only hit with --apply)
        r(regex=r"/users/42/items$", method="POST", response={"json": {"successful": {"0": {"key": "ATT00001"}}}}),
        r(f"{LIB}/items/ATT00001/file", method="POST", body="md5=",
          response={"json": {"url": "https://s3.example/up", "uploadKey": "UK1", "prefix": "PRE", "suffix": "SUF", "contentType": "multipart/x"}}),
        r("https://s3.example/up", method="POST", response={"status": 201, "text": ""}),
        r(f"{LIB}/items/ATT00001/file", method="POST", body="upload=UK1", response={"status": 204}),
    ]


def summary(proc):
    line = [ln for ln in proc.stdout.splitlines() if ln.startswith("SUMMARY ")][-1]
    return json.loads(line[len("SUMMARY "):])


# (a) -----------------------------------------------------------------------
def test_client_builds_user_and_group_urls_and_headers(run):
    res = driver(run, "urls")
    assert res["user"]["base"] == "https://api.zotero.org/users/42"
    assert res["group"]["base"] == "https://api.zotero.org/groups/77"
    assert res["user"]["call"]["url"] == "https://api.zotero.org/users/42/items?limit=1"
    assert res["user"]["call"]["headers"]["Zotero-API-Key"] == "k1"
    assert res["group"]["call"]["headers"]["Zotero-API-Key"] == "k2"
    assert res["user"]["call"]["headers"]["Zotero-API-Version"] == "3"


# (b) -----------------------------------------------------------------------
def test_attach_pdf_makes_four_calls_in_order(run, tmp_path):
    f = tmp_path / "paper.pdf"
    f.write_bytes(PDF2000)
    res = driver(run, "attach", str(f), routes=fill_routes())
    assert res == {"attachmentKey": "ATT00001", "deduped": False}
    c = run.calls
    assert all(x["matched"] for x in c)
    assert [(x["method"], x["url"]) for x in c] == [
        ("POST", f"{LIB}/items"),
        ("POST", f"{LIB}/items/ATT00001/file"),
        ("POST", "https://s3.example/up"),
        ("POST", f"{LIB}/items/ATT00001/file"),
    ]
    create = json.loads(c[0]["body"])[0]
    assert create["itemType"] == "attachment" and create["linkMode"] == "imported_file"
    assert create["parentItem"] == "PARENT01" and create["title"] == "My title"
    assert "Zotero-Write-Token" in c[0]["headers"]
    auth = c[1]["body"]
    assert f"md5={hashlib.md5(PDF2000).hexdigest()}" in auth and "filesize=2000" in auth and "filename=paper.pdf" in auth
    assert c[1]["headers"]["If-None-Match"] == "*"
    assert c[2]["body"] == f"<binary {len(PDF2000) + 6} bytes>"  # prefix + file + suffix
    assert c[3]["body"] == "upload=UK1"


def test_attach_pdf_honours_exists_short_circuit(run, tmp_path):
    f = tmp_path / "paper.pdf"
    f.write_bytes(PDF2000)
    routes = [r(regex=r"/users/42/items$", method="POST", response={"json": {"successful": {"0": {"key": "ATT00001"}}}}),
              r(f"{LIB}/items/ATT00001/file", method="POST", response={"json": {"exists": 1}})]
    res = driver(run, "attach", str(f), routes=routes)
    assert res == {"attachmentKey": "ATT00001", "deduped": True}
    assert len(run.calls) == 2 and all(x["matched"] for x in run.calls)


# (c) -----------------------------------------------------------------------
def test_412_raises_clear_version_conflict(run):
    res = driver(run, "patch", routes=[r(f"{LIB}/items/ITEM0001", method="PATCH", response={"status": 412, "text": "changed"})])
    assert res["error"]["code"] == "version_conflict" and res["error"]["status"] == 412
    assert "version conflict" in res["error"]["message"]
    assert run.calls[0]["headers"]["If-Unmodified-Since-Version"] == "5"


def test_429_backs_off_then_retries(run):
    routes = [r(f"{LIB}/items/ITEM0001", sequence=[{"status": 429, "headers": {"Retry-After": "7"}}, {"json": {"ok": 1}}])]
    res = driver(run, "retry429", routes=routes)
    assert res == {"status": 200, "sleeps": [7000]}


# (d) -----------------------------------------------------------------------
def test_pdf_fill_dry_run_reports_and_writes_nothing(run, proj):
    p = run.go(PDF_FILL, ["paper-a"], fill_routes())
    assert p.returncode == 0, p.stderr
    s = summary(p)
    assert (s["found"], s["manual"], s["attached"], s["failed"], s["already_had_pdf"]) == (1, 1, 0, 0, 1)
    assert "dry run" in p.stdout
    assert not (proj / "outputs").exists()
    assert all(c["matched"] for c in run.calls)
    assert [c for c in run.calls if c["method"] != "GET"] == []


# (e) -----------------------------------------------------------------------
def test_pdf_fill_apply_attaches_and_verifies_by_rereading(run, proj):
    p = run.go(PDF_FILL, ["paper-a", "--apply"], fill_routes())
    assert p.returncode == 0, p.stderr
    s = summary(p)
    assert (s["attached"], s["manual"], s["failed"]) == (1, 1, 0)
    c = run.calls
    assert all(x["matched"] for x in c)
    methods = [(x["method"], x["url"].replace(LIB, "")) for x in c if "zotero.org" in x["url"] or "s3.example" in x["url"]]
    posts = [m for m in methods if m[0] == "POST"]
    assert [u for _, u in posts] == ["https://api.zotero.org/users/42/items".replace(LIB, ""), "/items/ATT00001/file", "https://s3.example/up", "/items/ATT00001/file"]
    # the register POST is followed by a fresh GET of the item's children
    last_post = max(i for i, x in enumerate(c) if x["method"] == "POST")
    assert c[last_post + 1]["method"] == "GET" and c[last_post + 1]["url"].endswith("/items/BBBBBBBB/children")
    assert "verified" in p.stdout
    logs = list((proj / "outputs" / "pdf-fill").glob("paper-a-*.jsonl"))
    assert len(logs) == 1
    statuses = {json.loads(x)["key"]: json.loads(x)["status"] for x in logs[0].read_text().splitlines()}
    assert statuses == {"BBBBBBBB": "attached", "CCCCCCCC": "manual"}
    manual = (proj / "outputs" / "pdf-fill" / "paper-a-manual.md").read_text()
    assert "https://doi.org/10.1/c" in manual and "CCCCCCCC" in manual


def test_manual_list_uses_proxy_prefix_when_set(run, proj):
    p = run.go(PDF_FILL, ["paper-a", "--apply"], fill_routes(), extra_env={"INSTITUTION_PROXY_PREFIX": "https://proxy.example/login?url="})
    assert p.returncode == 0, p.stderr
    manual = (proj / "outputs" / "pdf-fill" / "paper-a-manual.md").read_text()
    assert "https://proxy.example/login?url=https://doi.org/10.1/c" in manual


# (f) -----------------------------------------------------------------------
def test_download_rejects_non_pdf_and_oversize(run):
    routes = [
        r("https://x.example/page", {"text": "<html>not a pdf</html>", "headers": {"content-type": "application/pdf"}}),
        r("https://x.example/big-stream", {"bytes": 50 * 1024 * 1024 + 1}),
        r("https://x.example/big-header", {"bytes": 100, "headers": {"content-length": str(60 * 1024 * 1024)}}),
        r("https://x.example/ok", {"bytes": 3000}),
    ]
    page = driver(run, "download", "https://x.example/page", routes=routes)
    assert page["ok"] is False and "not_pdf" in page["reason"]
    big = driver(run, "download", "https://x.example/big-stream", routes=routes)
    assert big["ok"] is False and "too_large" in big["reason"]
    hdr = driver(run, "download", "https://x.example/big-header", routes=routes)
    assert hdr["ok"] is False and "too_large" in hdr["reason"]
    ok = driver(run, "download", "https://x.example/ok", routes=routes)
    assert ok == {"ok": True, "length": 3000}


# (g) -----------------------------------------------------------------------
def test_reparent_dry_run_apply_and_idempotent_rerun(run, proj, tmp_path):
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps([{"attachmentKey": "ATT00001", "existingParentKey": "PARENT01"},
                                {"attachmentKey": "ATT00002", "existingParentKey": "PARENT02"}]))
    def att(k, parent=None):
        d = {"key": k, "version": 3, "data": {"key": k, "itemType": "attachment", "title": f"t-{k}"}}
        if parent:
            d["data"]["parentItem"] = parent
        return d
    routes = []
    for n in (1, 2):
        a, p_ = f"ATT0000{n}", f"PARENT0{n}"
        routes += [r(f"{LIB}/items/{a}", sequence=[{"json": att(a)}, {"json": att(a, p_)}]),
                   r(f"{LIB}/items/{p_}", {"json": item(p_, "Parent", "10.1/p")}),
                   r(f"{LIB}/items/{a}", method="PATCH", response={"status": 204})]
    log = proj / "outputs" / "pdf-fill" / "reparent.jsonl"

    dry = run.go(REPARENT, [str(plan)], routes)
    assert dry.returncode == 0, dry.stdout + dry.stderr
    assert "dry run: 2/2 ok" in dry.stdout
    assert [c for c in run.calls if c["method"] != "GET"] == [] and not log.exists()

    ap = run.go(REPARENT, [str(plan), "--apply"], routes)
    assert ap.returncode == 0, ap.stdout + ap.stderr
    patches = [c for c in run.calls if c["method"] == "PATCH"]
    assert len(patches) == 2 and all(c["headers"]["If-Unmodified-Since-Version"] == "3" for c in patches)
    assert json.loads(patches[0]["body"]) == {"parentItem": "PARENT01", "collections": []}
    rows = [json.loads(x) for x in log.read_text().splitlines()]
    assert [(x["attachmentKey"], x["ok"], x["verifiedParent"]) for x in rows] == [("ATT00001", True, "PARENT01"), ("ATT00002", True, "PARENT02")]
    assert all(c["matched"] for c in run.calls)

    again = run.go(REPARENT, [str(plan), "--apply"], routes)
    assert again.stdout.count("already applied") == 2
    assert run.calls == [] and len(log.read_text().splitlines()) == 2


# (h) -----------------------------------------------------------------------
def test_env_parser_handles_quotes_and_comments(run, tmp_path, proj):
    f = tmp_path / "sample.env"
    f.write_text('# comment\n\nA=plain\nB="quoted # not a comment"\nC=\'single quoted\'\nexport D=exported # trailing\nE=\nbad line\n')
    assert driver(run, "env", str(f)) == {"A": "plain", "B": "quoted # not a comment", "C": "single quoted", "D": "exported", "E": ""}
    (proj / ".env").write_text("ZOTERO_LIBRARY_ID=99\nPRESET=overridden\n")
    loaded = driver(run, "dotenv", str(proj))
    assert loaded["ZOTERO_LIBRARY_ID"] == "99" and loaded["PRESET"] == "keep"


# (i) -----------------------------------------------------------------------
def test_unpaywall_skipped_with_notice_when_email_unset(run):
    p = run.go(PDF_FILL, ["paper-a"], fill_routes(), email=None)
    assert p.returncode == 0, p.stderr
    assert "UNPAYWALL_EMAIL" in p.stdout and "skipping Unpaywall" in p.stdout
    assert p.stdout.count("skipping Unpaywall") == 1
    assert not any("unpaywall" in c["url"] for c in run.calls)
    assert all(c["matched"] for c in run.calls)
    s = summary(p)
    assert (s["found"], s["manual"]) == (0, 2)


def test_only_flag_limits_sources_and_keys_flag_skips_collection(run):
    routes = fill_routes() + [r(f"{LIB}/items?itemKey=CCCCCCCC", {"json": [item("CCCCCCCC", "Closed one", "10.1/c")]})]
    p = run.go(PDF_FILL, ["--keys", "CCCCCCCC", "--only", "openalex"], routes)
    assert p.returncode == 0, p.stderr
    urls = " ".join(c["url"] for c in run.calls)
    assert "openalex" in urls and "unpaywall" not in urls and "doi.org/10.1/c" not in urls and "collections" not in urls
