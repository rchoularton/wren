#!/usr/bin/env python3
"""Generate the two README diagrams as plain SVG (standard library only).

    python3 assets/diagrams/build_diagrams.py          write both SVG files
    python3 assets/diagrams/build_diagrams.py --check  exit 1 if a committed file is stale

npm does not render Mermaid, so the README uses these images instead. Edit the data
below when a skill or pipeline phase changes, then regenerate.
"""
from __future__ import annotations

import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------- data
# (label, skill or None)
ANALYSIS = [
    ("1 · Scope", None),
    ("2 · Data", None),
    ("3 · Explore", None),
    ("4 · Methods", None),
    ("5 · Build", None),
    ("6 · QC", "/qc-team"),
]
GATE = ("Phase 7 · Freeze", "/gold-standard")
WRITING = [
    ("8 · Draft", "/draft"),
    ("9 · Figures", "/figure"),
    ("10 · Review", None),
    ("11 · QC draft", None),
    ("12 · Submit", "/cover-letter"),
    ("13 · Revise", "/revision-response"),
    ("14 · Publish", None),
]
SKILL_GROUPS = [
    ("Orient", ["/research", "/paper", "/setup"]),
    ("Discover", ["/literature-scan", "/lit-digest", "/zotero-audit", "/pdf-fill", "/librarian-team"]),
    ("Write and submit", ["/draft", "/figure", "/ref-check", "/cover-letter", "/revision-response", "/peer-review"]),
    ("Rigor and memory", ["/gold-standard", "/qc-team", "/methods-audit", "/rigor-check",
                          "/research-memory", "/recall", "/retro"]),
]
SKILLS_TITLE = "Wren — {n} skills"

TEXT, MUTED, INDIGO = "#1f2328", "#57606a", "#3f51b5"
BOX_FILL, BORDER = "#f6f8fa", "#d0d7de"
GATE_FILL, GATE_STROKE = "#fde68a", "#b45309"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
SANS_EM, MONO_EM = 0.60, 0.62   # conservative width per character, in em
PAD = 12                        # minimum horizontal padding inside a box


# ---------------------------------------------------------------- helpers
def n(v: float) -> str:
    return f"{v:g}"


def text_width(s: str, size: float, mono: bool) -> float:
    return len(s) * size * (MONO_EM if mono else SANS_EM)


def text(x, y, s, size, fill=TEXT, mono=False, weight=None, anchor="middle") -> str:
    w = f' font-weight="{weight}"' if weight else ""
    fam = MONO if mono else SANS
    return (f'<text x="{n(x)}" y="{n(y)}" text-anchor="{anchor}" font-family="{fam}" '
            f'font-size="{n(size)}"{w} fill="{fill}">{escape(s)}</text>')


def rect(x, y, w, h, fill, stroke, sw=1, r=8) -> str:
    return (f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" rx="{r}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{n(sw)}"/>')


def arrow(points) -> list[str]:
    """Polyline through points with an arrowhead on the last segment."""
    (x0, y0), (x1, y1) = points[-2], points[-1]
    dx = (x1 > x0) - (x1 < x0)
    dy = (y1 > y0) - (y1 < y0)
    bx, by = x1 - dx * 8, y1 - dy * 8                      # base of the head
    px, py = -dy * 4.5, dx * 4.5                           # perpendicular half-width
    line = points[:-1] + [(bx, by)]
    d = " ".join(f"{n(a)},{n(b)}" for a, b in line)
    head = f"{n(x1)},{n(y1)} {n(bx + px)},{n(by + py)} {n(bx - px)},{n(by - py)}"
    return [f'<polyline points="{d}" fill="none" stroke="{MUTED}" stroke-width="1.8"/>',
            f'<polygon points="{head}" fill="{MUTED}"/>']


def wrap(width, height, title, desc, body) -> str:
    head = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img">',
        f"<title>{escape(title)}</title>",
        f"<desc>{escape(desc)}</desc>",
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" '
        f'fill="#ffffff" stroke="{BORDER}" stroke-width="1"/>',
    ]
    return "\n".join(head + body + ["</svg>"]) + "\n"


# ---------------------------------------------------------------- pipeline
def step_box(x, y, w, h, label, skill) -> list[str]:
    out = [rect(x, y, w, h, BOX_FILL, BORDER)]
    cx = x + w / 2
    if skill:
        out += [text(cx, y + 25, label, 14, weight="600"), text(cx, y + 45, skill, 13, MUTED, mono=True)]
    else:
        out.append(text(cx, y + h / 2 + 5, label, 14, weight="600"))
    return out


def row_layout(steps, size=14, mono_size=13, min_w=100, gap=30):
    widths = []
    for label, skill in steps:
        need = text_width(label, size, False)
        if skill:
            need = max(need, text_width(skill, mono_size, True))
        widths.append(max(min_w, round(need + 2 * PAD + 4)))
    return widths, gap


def build_pipeline() -> str:
    W, H = 1200, 400
    box_h, gap = 60, 30
    body: list[str] = []

    def row(steps, frame_y, title):
        widths, _ = row_layout(steps, gap=gap)
        total = sum(widths) + gap * (len(widths) - 1)
        fx = (W - total) / 2 - 20
        body.append(rect(fx, frame_y, total + 40, 130, "#ffffff", BORDER, 1, 12))
        body.append(text(fx + total + 22, frame_y + 28, title, 15, INDIGO, weight="700", anchor="end"))
        x, y = fx + 20, frame_y + 48
        boxes = []
        for (label, skill), w in zip(steps, widths):
            body.extend(step_box(x, y, w, box_h, label, skill))
            boxes.append((x, y, w))
            x += w + gap
        for (ax, ay, aw), (bx, by, bw) in zip(boxes, boxes[1:]):
            body.extend(arrow([(ax + aw, ay + box_h / 2), (bx, by + box_h / 2)]))
        return boxes

    top = row(ANALYSIS, 20, "Analysis")
    bottom = row(WRITING, 250, "Writing")

    gw, gh = 210, 64
    gx, gy = (W - gw) / 2, 176
    body.append(rect(gx, gy, gw, gh, GATE_FILL, GATE_STROKE, 2.5, 10))
    body.append(text(W / 2, gy + 27, GATE[0], 15, "#000000", weight="700"))
    body.append(text(W / 2, gy + 48, GATE[1], 13, "#000000", mono=True))

    mid = gy + gh / 2
    qx, qy, qw = top[-1]
    body.extend(arrow([(qx + qw / 2, qy + box_h), (qx + qw / 2, mid), (gx + gw, mid)]))
    dx, dy, dw = bottom[0]
    body.extend(arrow([(gx, mid), (dx + dw / 2, mid), (dx + dw / 2, dy)]))

    desc = ("A 14-phase pipeline. Analysis: 1 Scope, 2 Data, 3 Explore, 4 Methods, 5 Build, "
            "6 QC (/qc-team). Phase 7 Freeze (/gold-standard) is a gate: no writing until the analysis is frozen. "
            "Writing: 8 Draft (/draft), 9 Figures (/figure), 10 Review, 11 QC draft, "
            "12 Submit (/cover-letter), 13 Revise (/revision-response), 14 Publish.")
    return wrap(W, H, "Wren 14-phase paper pipeline", desc, body)


# ---------------------------------------------------------------- skills
def skill_count() -> int:
    return sum(len(s) for _, s in SKILL_GROUPS)


def build_skills() -> str:
    size, col_gap, margin = 15, 20, 24
    need = max(text_width(s, size, True) for _, ss in SKILL_GROUPS for s in ss) + 2 * PAD
    chip = max(text_width(g, 15, False) for g, _ in SKILL_GROUPS) + 2 * PAD + 8
    col_w = round(max(need, chip, 236))
    W = 2 * margin + 4 * col_w + 3 * col_gap
    row_h, pitch, top = 36, 44, 150
    H = top + max(len(s) for _, s in SKILL_GROUPS) * pitch + 20
    body = [text(W / 2, 56, SKILLS_TITLE.format(n=skill_count()), 26, weight="700")]
    for i, (group, skills) in enumerate(SKILL_GROUPS):
        x = margin + i * (col_w + col_gap)
        body.append(rect(x, 90, col_w, 40, INDIGO, INDIGO, 1, 8))
        body.append(text(x + col_w / 2, 115, group, 16, "#ffffff", weight="700"))
        for j, s in enumerate(skills):
            y = top + j * pitch
            body.append(rect(x, y, col_w, row_h, BOX_FILL, BORDER))
            body.append(text(x + col_w / 2, y + 23, s, size, mono=True))
    desc = ("Wren has %d skills in four groups. " % skill_count()
            + " ".join(f"{g}: {', '.join(ss)}." for g, ss in SKILL_GROUPS))
    return wrap(W, H, SKILLS_TITLE.format(n=skill_count()), desc, body)


# ---------------------------------------------------------------- main
OUTPUTS = {"paper-pipeline.svg": build_pipeline, "skills.svg": build_skills}


def main(argv) -> int:
    check = "--check" in argv
    stale = []
    for name, build in OUTPUTS.items():
        path, content = HERE / name, build()
        if check:
            if not path.is_file() or path.read_bytes() != content.encode("utf-8"):
                stale.append(name)
        else:
            path.write_bytes(content.encode("utf-8"))
    if stale:
        print(f"Stale diagram(s): {', '.join(stale)}. Run: python3 assets/diagrams/build_diagrams.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
