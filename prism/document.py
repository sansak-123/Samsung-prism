"""Document model: a template is described as text blocks, rules, objects and a background.
The same Document is rendered twice: once as the Original, once with release parameters."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field, asdict
from functools import lru_cache

from PIL import ImageFont

FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts")

FONT_FAMILIES = {
    # name: (class, regular, bold)
    "DejaVuSans": ("sans", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
    "LiberationSans": ("sans", "LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf"),
    "Carlito": ("sans", "Carlito-Regular.ttf", "Carlito-Bold.ttf"),
    "Poppins": ("sans", "Poppins-Regular.ttf", "Poppins-Bold.ttf"),
    "FreeSans": ("sans", "FreeSans.ttf", "FreeSansBold.ttf"),
    "DejaVuSerif": ("serif", "DejaVuSerif.ttf", "DejaVuSerif-Bold.ttf"),
    "LiberationSerif": ("serif", "LiberationSerif-Regular.ttf", "LiberationSerif-Bold.ttf"),
    "Caladea": ("serif", "Caladea-Regular.ttf", "Caladea-Bold.ttf"),
    "FreeSerif": ("serif", "FreeSerif.ttf", "FreeSerifBold.ttf"),
    "LiberationMono": ("mono", "LiberationMono-Regular.ttf", "LiberationMono-Bold.ttf"),
    "DejaVuSansMono": ("mono", "DejaVuSansMono.ttf", "DejaVuSansMono-Bold.ttf"),
}
FAMILIES_BY_CLASS = {}
for _n, (_c, _r, _b) in FONT_FAMILIES.items():
    FAMILIES_BY_CLASS.setdefault(_c, []).append(_n)


@lru_cache(maxsize=4096)
def get_font(family: str, bold: bool, size: float) -> ImageFont.FreeTypeFont:
    _, reg, bld = FONT_FAMILIES[family]
    return ImageFont.truetype(os.path.join(FONT_DIR, bld if bold else reg), round(size * 4) / 4)


@dataclass
class Run:
    text: str
    style: str = "normal"  # normal | bold | accent (accent = coloured + bold)


@dataclass
class TextBlock:
    id: str
    role: str                    # title | heading | body | small
    lines: list                  # list[list[Run]]
    x: int
    y: int
    w: int
    size: float
    family: str
    align: str = "left"
    color: tuple = (30, 30, 30)
    accent: tuple = (180, 30, 40)
    line_gap: float = 1.35


@dataclass
class Rule:
    x1: int
    y1: int
    x2: int
    y2: int
    width: int = 2
    color: tuple = (120, 120, 120)


@dataclass
class Obj:
    kind: str                    # logo | icon | stamp | signature | qr | photo | toggle | avatar | badge
    x: int
    y: int
    w: int
    h: int
    color: tuple = (40, 90, 160)
    seed: int = 0
    label: str = ""


@dataclass
class Band:
    x: int
    y: int
    w: int
    h: int
    color: tuple
    radius: int = 0


@dataclass
class Background:
    base: tuple
    texture: float               # gaussian grain std (grey levels)
    seed: int
    bands: list = field(default_factory=list)
    gradient: tuple | None = None  # optional (top_color, bottom_color)


@dataclass
class Document:
    template: str
    width: int
    height: int
    background: Background
    blocks: list = field(default_factory=list)
    rules: list = field(default_factory=list)
    objects: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


# ---------------------------------------------------------------- markup / layout
_TOKEN = re.compile(r"(\*\*.+?\*\*|\[\[.+?\]\])")


def parse_markup(text: str) -> list:
    """'Pay **now** or [[today]]' -> word-level runs with styles."""
    words = []
    for part in _TOKEN.split(text):
        if not part:
            continue
        if part.startswith("**"):
            style, body = "bold", part[2:-2]
        elif part.startswith("[["):
            style, body = "accent", part[2:-2]
        else:
            style, body = "normal", part
        for wd in body.split(" "):
            if wd:
                words.append(Run(wd, style))
    return words


def run_font(block_family: str, style: str, size: float, role: str):
    bold = style in ("bold", "accent") or role in ("title", "heading")
    return get_font(block_family, bold, size)


def wrap_runs(words: list, family: str, size: float, width: int, role: str) -> list:
    lines, cur, cur_w = [], [], 0.0
    space = get_font(family, False, size).getlength(" ")
    for r in words:
        ww = run_font(family, r.style, size, role).getlength(r.text)
        add = ww if not cur else space + ww
        if cur and cur_w + add > width:
            lines.append(cur)
            cur, cur_w = [r], ww
        else:
            cur.append(r)
            cur_w += add
    if cur:
        lines.append(cur)
    return lines


def line_text(line: list) -> str:
    return " ".join(r.text for r in line)


def add_block(doc: Document, bid: str, text: str | list, x: int, y: int, w: int, role: str,
              size: float, family: str, align: str = "left", color=(30, 30, 30), accent=(180, 30, 40),
              line_gap: float = 1.35, pre: bool = False) -> int:
    """Add a wrapped block. `text` may be a string or list of strings (hard line breaks).
    pre=True keeps each string as one unwrapped run (tables / monospaced columns).
    Returns the y coordinate just below the block."""
    paras = text if isinstance(text, list) else [text]
    lines = []
    for p in paras:
        if pre:
            style = "bold" if p.startswith("**") and p.endswith("**") else "normal"
            lines.append([Run(p.strip("*"), style)])
        else:
            lines.extend(wrap_runs(parse_markup(p), family, size, w, role) or [[Run(" ")]])
    doc.blocks.append(TextBlock(bid, role, lines, x, y, w, size, family, align, color, accent, line_gap))
    return int(y + len(lines) * size * line_gap)
