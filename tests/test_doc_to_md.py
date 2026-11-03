"""doc_to_md.py: conversion, cache hits and invalidation, and error paths."""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys

import pytest
from conftest import REPO_ROOT

docx = pytest.importorskip("docx")

SCRIPT = REPO_ROOT / ".claude" / "lib" / "doc_to_md.py"
spec = importlib.util.spec_from_file_location("doc_to_md", SCRIPT)
d2m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d2m)


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path / "proj"))
    # Force the python-docx path so tests need no pandoc.
    real = d2m.have_exe
    monkeypatch.setattr(d2m, "have_exe", lambda n: False if n == "pandoc" else real(n))


@pytest.fixture
def sample_docx(tmp_path):
    p = tmp_path / "in put" / "sample.docx"
    p.parent.mkdir()
    doc = docx.Document()
    doc.add_heading("Findings", level=1)
    doc.add_paragraph("Rainfall explains the unusual harvest.")
    doc.save(p)
    return p


def test_docx_converts_to_markdown(sample_docx):
    res = d2m.to_markdown(sample_docx)
    text = res.path.read_text(encoding="utf-8")
    assert "Rainfall explains the unusual harvest." in text
    assert "# Findings" in text and "## Findings" not in text
    assert res.path.parent == d2m.cache_root()
    assert (d2m.cache_root().parent.parent) == (sample_docx.parent.parent / "proj")


def test_second_call_hits_cache_without_converting(sample_docx, monkeypatch):
    first = d2m.to_markdown(sample_docx)
    assert first.cached is False and first.path.exists()

    def boom(*a, **k):
        raise AssertionError("converter invoked on a cache hit")

    monkeypatch.setattr(d2m, "convert", boom)
    second = d2m.to_markdown(sample_docx)
    assert second.cached is True and second.path == first.path


def test_touching_source_invalidates_cache(sample_docx):
    first = d2m.to_markdown(sample_docx)
    st = sample_docx.stat()
    os.utime(sample_docx, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
    second = d2m.to_markdown(sample_docx)
    assert second.cached is False
    assert second.path != first.path


def test_unsupported_extension_errors(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("hello")
    proc = subprocess.run([sys.executable, str(SCRIPT), str(f)],
                          capture_output=True, text=True)
    assert proc.returncode == 2
    assert "unsupported" in proc.stderr and ".pdf" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_pdf_without_converter_names_what_to_install(tmp_path, monkeypatch, capsys):
    f = tmp_path / "paper.pdf"
    f.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(d2m, "have_exe", lambda n: False)
    monkeypatch.setattr(d2m, "have_module", lambda n: False)
    rc = d2m.main([str(f)])
    err = capsys.readouterr().err
    assert rc == 3
    assert "pdftotext" in err and "pdfplumber" in err
    assert "Traceback" not in err


def test_converter_is_part_of_cache_key(sample_docx, monkeypatch):
    fallback = d2m.to_markdown(sample_docx)
    real = d2m.have_exe
    monkeypatch.setattr(d2m, "have_exe", lambda n: True if n == "pandoc" else real(n))
    monkeypatch.setattr(d2m, "convert", lambda *a, **k: "stub")
    res = d2m.to_markdown(sample_docx)
    assert res.cached is False and res.path != fallback.path
