#!/usr/bin/env python3
"""Generate the Wren pixel-art logo.

Source of truth for the logo: the GRID below is the hand-designed 16x16 pixel map.
Running this script regenerates wren.svg (scalable) and PNG rasters next to it.

    python3 assets/logo/generate_logo.py

Requires Pillow (pip install pillow).
"""
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent

PALETTE = {
    '.': None,             # transparent
    'K': (42, 26, 16),     # outline dark brown
    'D': (95, 63, 34),     # dark brown  (back / wing / tail)
    'B': (160, 109, 59),   # body brown
    'L': (240, 215, 170),  # light buff belly
    'W': (251, 245, 233),  # brow highlight
    'E': (26, 18, 11),     # eye
    'Y': (235, 162, 60),   # beak
}

# 16 x 16. A wren facing right, tail cocked up-left.
GRID = [
    "................",
    "...KK...........",
    "..KDDK..........",
    "..KDDK...KKKKK..",
    "..KDDK..KBWWBK..",
    "..KDDK.KBBBBEBYY",
    "..KDDDKBBBBBBBY.",
    ".KDDBBBBBBBBBBK.",
    ".KDBDDBBBBBBBBK.",
    ".KDBDDBBBLLLLBK.",
    "..KDBBBBBLLLLBK.",
    "..KDBBBBLLLLLBK.",
    "...KBBBBLLLLBK..",
    "...KBBBBBBBBK...",
    "....KKK.KKK.....",
    ".....K...K......",
]

W = len(GRID[0])
H = len(GRID)
for i, row in enumerate(GRID):
    assert len(row) == W, f"row {i} len {len(row)} != {W}: {row!r}"


def _master():
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = img.load()
    for y, row in enumerate(GRID):
        for x, ch in enumerate(row):
            c = PALETTE[ch]
            if c:
                px[x, y] = (*c, 255)
    return img


def main():
    master = _master()

    # PNG rasters (nearest-neighbour keeps the pixels crisp)
    for size in (512, 128, 64, 32):
        name = "wren.png" if size == 512 else f"wren-{size}.png"
        master.resize((size, size), Image.NEAREST).save(HERE / name)

    # SVG (one rect per pixel; crisp at any scale)
    rects = []
    for y, row in enumerate(GRID):
        for x, ch in enumerate(row):
            c = PALETTE[ch]
            if c:
                rects.append(f'<rect x="{x}" y="{y}" width="1" height="1" fill="rgb{c}"/>')
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'shape-rendering="crispEdges" width="256" height="256">\n'
        + "\n".join(rects) + "\n</svg>\n"
    )
    (HERE / "wren.svg").write_text(svg)
    print("wrote wren.svg, wren.png (512), wren-128.png, wren-64.png, wren-32.png")


if __name__ == "__main__":
    main()
