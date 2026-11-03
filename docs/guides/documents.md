# Reading documents cheaply

A PDF or Word file costs far more tokens to read raw than as Markdown. Wren converts it once, caches the result, and lets every later read hit the cache. This is the document form of token-budget rule 4 (`.claude/rules/token-budget.md`): do the deterministic work before any model token.

## Use it

```bash
python3 .claude/lib/doc_to_md.py paper.pdf            # prints the path of the cached .md
python3 .claude/lib/doc_to_md.py paper.docx --print   # prints the Markdown itself
npm run doc:md -- paper.pdf                           # same, via npm
```

Supported types: `.pdf`, `.docx`, `.xlsx`, `.pptx`. Text, code and Markdown need no conversion; read them directly. Node scripts can `import { normalizeToMd } from './.claude/lib/normalize-to-md.mjs'`.

`/literature-scan`, `/zotero-audit`, `/ref-check`, `/revision-response`, `/peer-review` and `/qc-team` tell the assistant to run this before reading a PDF or Word file.

## The cache

Results live in `.cache/md/` (git-ignored), under `$CLAUDE_PROJECT_DIR` when set, otherwise the project root. The key is the file's absolute path, modification time and size, so editing or replacing a file invalidates its entry automatically. Pass `--force` to reconvert anyway. Delete `.cache/md/` at any time; it is rebuilt on demand.

## Converters

Converters are optional and detected at runtime. If none is installed for a type, the command exits with code 3 and names what to install.

| Type | Preferred | Fallback |
|---|---|---|
| `.pdf` | `pdftotext` (poppler) | `pdfplumber` |
| `.docx` | `pandoc` | `python-docx` (already a Wren requirement) |
| `.xlsx` | `openpyxl` | none |
| `.pptx` | `python-pptx` | none |

The optional Python packages are listed, commented out, in `requirements.txt`. A scanned PDF has no text layer and converts to an empty result; it needs OCR first.

Exit codes: `0` ok, `1` conversion failed, `2` file missing or unsupported type, `3` no converter installed.
