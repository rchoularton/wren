#!/usr/bin/env python3
"""
Convert a heavy document (PDF, docx, xlsx, pptx) to cached Markdown before a model reads it.

Reading a raw PDF or Word file costs far more tokens than reading its Markdown. This converts
once and caches the result under `.cache/md/`, keyed on source path + mtime + size, so a repeat
read costs nothing (token-budget rule 4: deterministic work before any model token).

Usage (path of the Markdown on stdout; status and errors on stderr):
    python3 .claude/lib/doc_to_md.py report.pdf            # print the cached .md path
    python3 .claude/lib/doc_to_md.py report.pdf --print    # print the Markdown itself
    python3 .claude/lib/doc_to_md.py data.xlsx --force     # ignore the cache

Exit codes: 0 ok, 1 conversion failed, 2 file not found or unsupported type,
3 no converter installed for that type (the message names what to install).

Cache root: $CLAUDE_PROJECT_DIR/.cache/md, else <project root>/.cache/md where the project root
is found from this file's location (.claude/lib/ -> two levels up).

Converters are optional and detected at runtime (stdlib only here):
    pdf   pdftotext (poppler)  ->  pdfplumber
    docx  pandoc               ->  python-docx (a Wren core requirement)
    xlsx  openpyxl
    pptx  python-pptx
"""
import argparse
import hashlib
import importlib
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

CONVERT_EXTS = (".pdf", ".docx", ".xlsx", ".pptx")

# ext -> [(label, kind, name, install hint)] in order of preference.
CONVERTERS = {
    ".pdf": [("pdftotext", "exe", "pdftotext", "poppler (brew install poppler / apt install poppler-utils)"),
             ("pdfplumber", "module", "pdfplumber", "pip install pdfplumber")],
    ".docx": [("pandoc", "exe", "pandoc", "pandoc (brew install pandoc)"),
              ("python-docx", "module", "docx", "pip install python-docx")],
    ".xlsx": [("openpyxl", "module", "openpyxl", "pip install openpyxl")],
    ".pptx": [("python-pptx", "module", "pptx", "pip install python-pptx")],
}


class ConverterMissing(Exception):
    pass


class Result(NamedTuple):
    path: Path
    cached: bool


def log(*a):
    print(*a, file=sys.stderr)


def have_exe(name: str) -> bool:
    return shutil.which(name) is not None


def have_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def available(ext: str) -> list:
    """Converters installed for `ext`, in order of preference."""
    check = {"exe": have_exe, "module": have_module}
    return [c for c in CONVERTERS[ext] if check[c[1]](c[2])]


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def cache_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    return (Path(env) if env else project_root()) / ".cache" / "md"


def cache_key(src: Path) -> str:
    st = src.stat()
    raw = f"{src.resolve()}\n{st.st_mtime_ns}\n{st.st_size}"
    return hashlib.sha256(raw.encode()).hexdigest()


# --------------------------------------------------------------------------- converters
def _run(cmd) -> str:
    out = subprocess.run(cmd, capture_output=True, timeout=180)
    if out.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {out.stderr.decode('utf-8', 'replace')[:400]}")
    return out.stdout.decode("utf-8", "replace")


def _md_table(rows) -> str:
    """rows: list of lists -> GFM table; the first row is the header."""
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [list(r) + [""] * (width - len(r)) for r in rows]

    def cell(x):
        return str("" if x is None else x).replace("|", "\\|").replace("\n", " ").strip()

    head = "| " + " | ".join(cell(c) for c in rows[0]) + " |"
    sep = "| " + " | ".join(["---"] * width) + " |"
    body = ["| " + " | ".join(cell(c) for c in r) + " |" for r in rows[1:]]
    return "\n".join([head, sep, *body])


def pdf_to_md(src: Path, via: str) -> str:
    if via == "pdftotext":
        text = _run(["pdftotext", "-layout", str(src), "-"])
        if text.strip():
            return text
        log("[doc_to_md] pdftotext found no text (scanned PDF?)")
        return text
    import pdfplumber
    parts = []
    with pdfplumber.open(str(src)) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            parts.append(f"<!-- page {i} -->\n{page.extract_text() or ''}")
    return "\n\n".join(parts)


def docx_to_md(src: Path, via: str) -> str:
    if via == "pandoc":
        return _run(["pandoc", "-f", "docx", "-t", "gfm", str(src)])
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    doc = Document(str(src))
    blocks = []
    for child in doc.element.body.iterchildren():
        if child.tag.endswith("}p"):
            para = Paragraph(child, doc)
            text = para.text.strip()
            if not text:
                continue
            style = para.style.name if para.style is not None else ""
            if style == "Title":
                text = f"# {text}"
            elif style.startswith("Heading ") and style[8:].isdigit():
                text = f"{'#' * min(int(style[8:]) + 1, 6)} {text}"
            elif style.startswith("List"):
                text = f"- {text}"
            blocks.append(text)
        elif child.tag.endswith("}tbl"):
            table = Table(child, doc)
            blocks.append(_md_table([[c.text for c in r.cells] for r in table.rows]))
    return "\n\n".join(blocks)


def xlsx_to_md(src: Path, max_rows: int) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(str(src), read_only=True, data_only=True)
    parts = []
    for ws in wb.worksheets:
        rows = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i >= max_rows:
                rows.append([f"... (more rows truncated after {max_rows})"])
                break
            if any(c is not None for c in row):
                rows.append(list(row))
        parts.append(f"## Sheet: {ws.title}\n\n{_md_table(rows) if rows else '_(empty)_'}")
    wb.close()
    return "\n\n".join(parts)


def pptx_to_md(src: Path) -> str:
    from pptx import Presentation
    parts = []
    for i, slide in enumerate(Presentation(str(src)).slides, 1):
        lines = [f"## Slide {i}"]
        for shape in slide.shapes:
            if shape.has_table:
                lines.append(_md_table([[c.text for c in r.cells] for r in shape.table.rows]))
            elif shape.has_text_frame:
                txt = "\n".join(p.text for p in shape.text_frame.paragraphs).strip()
                if txt:
                    lines.append(txt)
        parts.append("\n\n".join(lines))
    return "\n\n".join(parts)


def convert(src: Path, max_rows: int = 500) -> str:
    ext = src.suffix.lower()
    found = available(ext)
    if not found:
        wants = "; ".join(f"{label}: {hint}" for label, _, _, hint in CONVERTERS[ext])
        raise ConverterMissing(
            f"no converter installed for {ext} files. Install one of: {wants}")
    label = found[0][0]
    if ext == ".pdf":
        return pdf_to_md(src, label)
    if ext == ".docx":
        return docx_to_md(src, label)
    if ext == ".xlsx":
        return xlsx_to_md(src, max_rows)
    return pptx_to_md(src)


def to_markdown(src: Path, force: bool = False, no_cache: bool = False,
                max_rows: int = 500) -> Result:
    """Return the cached Markdown path for `src`, converting first on a miss."""
    key = cache_key(src)
    root = cache_root()
    dst = root / f"{key}{'.nocache' if no_cache else ''}.md"
    if not no_cache and not force and dst.exists():
        return Result(dst, True)
    md = f"<!-- normalized from {src.name} by doc_to_md.py -->\n\n" + convert(src, max_rows)
    root.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(".tmp")
    tmp.write_text(md, encoding="utf-8")
    tmp.replace(dst)
    return Result(dst, False)


# --------------------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Convert a PDF/docx/xlsx/pptx to cached Markdown.")
    ap.add_argument("file", help="source document")
    ap.add_argument("--print", dest="print_md", action="store_true",
                    help="print the Markdown instead of the cache path")
    ap.add_argument("--force", action="store_true", help="reconvert even on a cache hit")
    ap.add_argument("--no-cache", action="store_true", help="do not reuse an existing cache entry")
    ap.add_argument("--max-rows", type=int, default=500, help="xlsx: max rows per sheet")
    args = ap.parse_args(argv)

    src = Path(args.file)
    if not src.is_file():
        log(f"[doc_to_md] not found: {src}")
        return 2
    if src.suffix.lower() not in CONVERT_EXTS:
        log(f"[doc_to_md] unsupported type {src.suffix or '(no extension)'}; "
            f"supported: {', '.join(CONVERT_EXTS)}. Text, code and Markdown can be read directly.")
        return 2
    try:
        res = to_markdown(src, args.force, args.no_cache, args.max_rows)
    except ConverterMissing as e:
        log(f"[doc_to_md] {e}")
        return 3
    except Exception as e:  # noqa: BLE001
        log(f"[doc_to_md] conversion failed for {src}: {e}")
        return 1
    log(f"[doc_to_md] {'cache hit' if res.cached else 'converted'}: {res.path}")
    if args.print_md:
        sys.stdout.write(res.path.read_text(encoding="utf-8"))
    else:
        print(res.path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
