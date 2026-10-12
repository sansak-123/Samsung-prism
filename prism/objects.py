"""Procedural graphic objects (logos, stamps, QR codes, signatures, photos, icons, UI widgets).
Each object is drawn as an RGBA tile, deterministic from its seed."""

from __future__ import annotations

import glob
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .document import get_font, FONT_DIR

PHOTO_DIR = os.path.join(os.path.dirname(FONT_DIR), "photos")
_PHOTOS = None


def _photos():
    global _PHOTOS
    if _PHOTOS is None:
        exts = ("*.jpg", "*.jpeg", "*.png", "*.webp")
        _PHOTOS = sorted(p for e in exts for p in glob.glob(os.path.join(PHOTO_DIR, e)))
    return _PHOTOS


def _rgba(color, a=255):
    return tuple(int(c) for c in color[:3]) + (a,)


def draw_object_tile(obj) -> Image.Image:
    w, h = max(2, int(obj.w)), max(2, int(obj.h))
    r = random.Random(obj.seed)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    k = obj.kind
    if k == "logo":
        shape = r.choice(["circle", "square", "hex"])
        c = _rgba(obj.color)
        if shape == "circle":
            d.ellipse((2, 2, w - 3, h - 3), fill=c)
        elif shape == "square":
            d.rounded_rectangle((2, 2, w - 3, h - 3), radius=w // 5, fill=c)
        else:
            pts = [(w / 2 + (w / 2 - 3) * math.cos(math.pi / 3 * i + math.pi / 6),
                    h / 2 + (h / 2 - 3) * math.sin(math.pi / 3 * i + math.pi / 6)) for i in range(6)]
            d.polygon(pts, fill=c)
        inv = (30, 30, 30, 255) if sum(obj.color[:3]) > 600 else (255, 255, 255, 255)
        f = get_font("DejaVuSans", True, h * 0.5)
        d.text((w / 2, h / 2), (obj.label or "A")[:1], font=f, fill=inv, anchor="mm")
        d.arc((w * 0.12, h * 0.12, w * 0.88, h * 0.88), r.randint(0, 90), r.randint(200, 330), fill=inv, width=2)
    elif k == "stamp":
        big = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        bd = ImageDraw.Draw(big)
        c = _rgba(obj.color, 200)
        bd.ellipse((3, 3, w - 4, h - 4), outline=c, width=4)
        bd.ellipse((12, 12, w - 13, h - 13), outline=c, width=2)
        bd.text((w / 2, h / 2), obj.label or "PAID", font=get_font("DejaVuSans", True, h * 0.13), fill=c, anchor="mm")
        img = big.rotate(r.uniform(-25, 25), resample=Image.BICUBIC)
    elif k == "qr":
        n = 21
        cell = min(w, h) / n
        g = np.random.default_rng(obj.seed).random((n, n)) > 0.5
        for (cy, cx) in ((0, 0), (0, n - 7), (n - 7, 0)):
            g[cy:cy + 7, cx:cx + 7] = False
            g[cy:cy + 7, cx] = g[cy:cy + 7, cx + 6] = True
            g[cy, cx:cx + 7] = g[cy + 6, cx:cx + 7] = True
            g[cy + 2:cy + 5, cx + 2:cx + 5] = True
        d.rectangle((0, 0, w - 1, h - 1), fill=(255, 255, 255, 255))
        for y in range(n):
            for x in range(n):
                if g[y, x]:
                    d.rectangle((x * cell, y * cell, (x + 1) * cell - 0.5, (y + 1) * cell - 0.5), fill=_rgba(obj.color))
    elif k == "signature":
        pts, x = [], 4.0
        while x < w - 4:
            pts.append((x, h / 2 + r.uniform(-h * 0.38, h * 0.38)))
            x += r.uniform(6, 14)
        sm = []
        for i in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            for t in np.linspace(0, 1, 6):
                sm.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * (3 * t * t - 2 * t * t * t)))
        d.line(sm, fill=_rgba(obj.color), width=2, joint="curve")
    elif k == "photo":
        photos = _photos()
        if photos:
            p = Image.open(photos[obj.seed % len(photos)]).convert("RGB")
            s = max(w / p.width, h / p.height)
            p = p.resize((int(p.width * s) + 1, int(p.height * s) + 1))
            left, top = (p.width - w) // 2, (p.height - h) // 2
            img = p.crop((left, top, left + w, top + h)).convert("RGBA")
        else:
            g = np.random.default_rng(obj.seed)
            top_c = np.array(obj.color[:3], float) * 0.6 + 100
            bot_c = np.array([g.integers(30, 120) for _ in range(3)], float)
            t = np.linspace(0, 1, h)[:, None, None]
            arr = top_c * (1 - t) + bot_c * t
            arr = np.repeat(arr, w, axis=1)
            base = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
            bd = ImageDraw.Draw(base)
            for _ in range(5):
                cx, cy, rad = g.integers(0, w), g.integers(0, h), g.integers(min(w, h) // 8, min(w, h) // 2 + 2)
                col = tuple(int(c) for c in g.integers(40, 230, 3)) + (int(g.integers(90, 200)),)
                bd.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), fill=col)
            ridge = [(0, h)] + [(x, h * 0.55 + g.uniform(-h * 0.2, h * 0.2)) for x in np.linspace(0, w, 7)] + [(w, h)]
            bd.polygon(ridge, fill=tuple(int(c) for c in bot_c * 0.6) + (255,))
            img = base.filter(ImageFilter.GaussianBlur(1.2))
            if obj.label:
                d2 = ImageDraw.Draw(img)
                d2.rectangle((0, 0, w - 1, h - 1), outline=(90, 90, 90, 255), width=2)
                d2.text((w / 2, h / 2), obj.label, font=get_font("DejaVuSans", True, 16), fill=(255, 255, 255, 255), anchor="mm")
    elif k == "icon":
        c = _rgba(obj.color)
        variant = r.randint(0, 3)
        if variant == 0:
            d.ellipse((w * .2, h * .1, w * .8, h * .7), outline=c, width=3)
            d.line((w * .5, h * .7, w * .5, h * .95), fill=c, width=3)
        elif variant == 1:
            d.rounded_rectangle((w * .1, h * .25, w * .9, h * .8), radius=4, outline=c, width=3)
            d.line((w * .1, h * .25, w * .5, h * .55, w * .9, h * .25), fill=c, width=3)
        elif variant == 2:
            d.rounded_rectangle((2, 2, w - 3, h - 3), radius=w // 4, fill=c)
            d.ellipse((w * .3, h * .3, w * .7, h * .7), fill=(255, 255, 255, 255))
        else:
            d.ellipse((w * .15, h * .15, w * .65, h * .65), outline=c, width=3)
            d.line((w * .58, h * .58, w * .9, h * .9), fill=c, width=4)
    elif k == "toggle":
        d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=_rgba(obj.color))
        d.ellipse((w - h + 3, 3, w - 4, h - 4), fill=(255, 255, 255, 255))
    elif k == "avatar":
        d.ellipse((0, 0, w - 1, h - 1), fill=_rgba(obj.color))
        d.text((w / 2, h / 2), (obj.label or "S")[:1], font=get_font("DejaVuSans", True, h * 0.45),
               fill=(255, 255, 255, 255), anchor="mm")
    elif k == "badge":
        c = _rgba(obj.color)
        n = 16
        pts = []
        for i in range(2 * n):
            rad = (w / 2 - 2) if i % 2 == 0 else (w / 2 - 9)
            a = math.pi * i / n
            pts.append((w / 2 + rad * math.cos(a), h / 2 + rad * math.sin(a)))
        d.polygon(pts, fill=c)
        d.ellipse((w * .2, h * .2, w * .8, h * .8), outline=(255, 255, 255, 255), width=2)
        d.text((w / 2, h / 2), "*", font=get_font("DejaVuSans", True, h * .4), fill=(255, 255, 255, 255), anchor="mm")
    return img
