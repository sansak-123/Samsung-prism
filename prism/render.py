"""Renderer: turns a Document + per-metric target severities into an image, and measures the
severity that was actually realised (stored as the ground-truth score = 1 - realised severity).

The Original is rendered through exactly the same path with all severities = 0, so a release
with all-zero severities is pixel-identical to its Original (verified in selftest)."""

from __future__ import annotations

import io
import math
import random
import warnings

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter
from skimage import color as skcolor

from .document import FONT_FAMILIES, FAMILIES_BY_CLASS, get_font, line_text
from .metrics import METRIC_KEYS, PHYS
from .objects import draw_object_tile

CONFUSABLE = {"O": "0", "0": "O", "o": "0", "l": "1", "1": "l", "I": "1", "i": "l", "e": "c", "c": "e",
              "S": "5", "5": "S", "a": "o", "B": "8", "8": "B", "g": "q", "q": "g", "n": "h", "h": "n",
              "u": "v", "v": "u", "m": "rn", "E": "F", "F": "E", "t": "f", "Z": "2", "2": "Z", "G": "6", "6": "G"}


# ------------------------------------------------------------------ background
def render_background(doc) -> np.ndarray:
    bgd = doc.background
    H, W = doc.height, doc.width
    img = Image.new("RGB", (W, H), tuple(bgd.base))
    if bgd.gradient:
        top, bot = np.array(bgd.gradient[0], float), np.array(bgd.gradient[1], float)
        t = np.linspace(0, 1, H)[:, None, None]
        grad = np.clip(top * (1 - t) + bot * t, 0, 255).astype(np.uint8)
        img = Image.fromarray(np.repeat(grad, W, axis=1))
    d = ImageDraw.Draw(img)
    for b in bgd.bands:
        if b.radius:
            d.rounded_rectangle((b.x, b.y, b.x + b.w, b.y + b.h), radius=b.radius, fill=tuple(b.color))
        else:
            d.rectangle((b.x, b.y, b.x + b.w, b.y + b.h), fill=tuple(b.color))
    arr = np.asarray(img).astype(np.float32)
    g = np.random.default_rng(bgd.seed)
    grain = gaussian_filter(g.normal(0, 1, (H, W)), 0.7)
    grain /= grain.std() + 1e-6
    mottle = gaussian_filter(g.normal(0, 1, (H, W)), 40)
    mottle /= mottle.std() + 1e-6
    fibre = gaussian_filter(g.normal(0, 1, (H, W)), (0.6, 6))
    fibre /= fibre.std() + 1e-6
    tex = bgd.texture * (grain + 0.35 * fibre) + bgd.texture * 0.8 * mottle
    tint = np.array([1.0, 0.97, 0.92], np.float32)
    arr += tex[..., None] * tint
    return np.clip(arr, 0, 255)


# ------------------------------------------------------------------ helpers
def _detail_std(p):
    p = p.mean(axis=2)
    return float((p - gaussian_filter(p, 2)).std())


def _texture_loss(patch, sigma):
    if sigma <= 1e-3:
        return 0.0, patch
    blurred = gaussian_filter(patch, (sigma, sigma, 0))
    s0 = _detail_std(patch)
    if s0 < 1e-6:
        return 0.0, blurred
    return float(np.clip(1 - _detail_std(blurred) / s0, 0, 1)), blurred


def _rgb2lab(arr255):
    return skcolor.rgb2lab(np.clip(arr255 / 255.0, 0, 1))


def _lab2rgb(lab):
    with warnings.catch_warnings():  # out-of-gamut clipping is expected; realised dE is measured afterwards
        warnings.simplefilter("ignore")
        return np.clip(skcolor.lab2rgb(lab) * 255.0, 0, 255)


def _de2000(lab1, lab2):
    return float(skcolor.deltaE_ciede2000(np.asarray(lab1, float)[None, None], np.asarray(lab2, float)[None, None])[0, 0])


def _chroma_shift(patch, target_de, theta):
    """Shift the patch colour (mostly a*/b*, slightly darker so very light papers stay in gamut)
    so that CIEDE2000(mean before, mean after) ~= target_de, measured AFTER gamut clipping."""
    if target_de <= 1e-3:
        return patch
    lab = _rgb2lab(patch)
    mean = lab.reshape(-1, 3).mean(0)
    direction = np.array([-0.45, math.cos(theta), math.sin(theta)])
    direction /= np.linalg.norm(direction)

    def apply(mag):
        out = _lab2rgb(lab + mag * direction)
        return out, _de2000(mean, _rgb2lab(out).reshape(-1, 3).mean(0))

    lo, hi = 0.0, 90.0
    best = patch
    for _ in range(14):
        mid = (lo + hi) / 2
        best, de = apply(mid)
        if de < target_de:
            lo = mid
        else:
            hi = mid
    return best


def _span_ids(block):
    """Group consecutive non-normal runs into emphasis spans. Returns {(line, run): span_index}."""
    spans, cur, out = 0, None, {}
    for j, line in enumerate(block.lines):
        for k, r in enumerate(line):
            if r.style != "normal":
                if cur != r.style:
                    spans += 1
                    cur = r.style
                out[(j, k)] = spans - 1
            else:
                cur = None
        cur = None
    return out, spans


# ------------------------------------------------------------------ planning
def plan_release(doc, sev: dict, seed: int) -> dict:
    """Convert target severities into concrete physical parameters (deterministic)."""
    pr = random.Random(seed)
    P = {"sev_target": dict(sev)}

    # OCR substitutions
    positions = []
    for bi, b in enumerate(doc.blocks):
        for j, line in enumerate(b.lines):
            for k, r in enumerate(line):
                for ci, ch in enumerate(r.text):
                    if ch.isalnum():
                        positions.append((bi, j, k, ci))
    n_total = len(positions)
    n_sub = int(round(sev["ocr_accuracy"] * PHYS["ocr_max_cer"] * n_total))
    chosen = pr.sample(positions, min(n_sub, n_total)) if n_total else []
    subs = {}
    for (bi, j, k, ci) in chosen:
        ch = doc.blocks[bi].lines[j][k].text[ci]
        if ch in CONFUSABLE and pr.random() < 0.75:
            new = CONFUSABLE[ch]
        else:
            pool = "abcdefghijklmnopqrstuvwxyz" if ch.islower() else ("0123456789" if ch.isdigit() else "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            new = pr.choice([c for c in pool if c != ch])
        subs.setdefault((bi, j, k), {})[ci] = new
    P["ocr_subs"] = subs
    P["ocr_cer"] = (len(chosen) / n_total) if n_total else 0.0

    # alignment
    s = sev["alignment_preservation"]
    P["align"] = [(pr.choice([-1, 1]) * s * PHYS["align_max_dx"], pr.choice([-1, 1]) * s * PHYS["align_max_dy"])
                  for _ in doc.blocks]

    # font: severity = 0.6*size_term + 0.4*family_term
    s = sev["font_similarity"]
    wsz, wf = PHYS["font_w_size"], PHYS["font_w_family"]
    feasible = [f for f in (0.0, 0.5, 1.0) if wf * f <= s + 1e-9 and s - wf * f <= wsz + 1e-9]
    fam_term = pr.choice(feasible) if feasible else 0.0
    size_term = float(np.clip((s - wf * fam_term) / wsz, 0, 1))
    fam_map = {}
    for b in doc.blocks:
        if b.family in fam_map:
            continue
        cls = FONT_FAMILIES[b.family][0]
        if fam_term == 0.5:
            fam_map[b.family] = pr.choice([f for f in FAMILIES_BY_CLASS[cls] if f != b.family])
        elif fam_term == 1.0:
            other = pr.choice([c for c in FAMILIES_BY_CLASS if c != cls])
            fam_map[b.family] = pr.choice(FAMILIES_BY_CLASS[other])
        else:
            fam_map[b.family] = b.family
    inc = size_term * PHYS["font_max_size_delta"]
    direction = pr.choice([-1, 1])
    if direction > 0 and inc > 0 and not _fits(doc, 1 + inc):
        direction = -1
    P["font"] = {"family_term": fam_term, "size_term": size_term, "family_map": fam_map,
                 "size_mult": 1 + direction * inc}

    # objects
    s = sev["object_preservation"]
    P["objects"] = [{"scale": 1 - s * PHYS["obj_max_scale_loss"], "angle": pr.uniform(0, 2 * math.pi),
                     "shift": s * PHYS["obj_max_shift"], "opacity": 1 - s * PHYS["obj_max_fade"]} for _ in doc.objects]

    P["bg_delta_e"] = sev["background_fidelity"] * PHYS["bg_max_delta_e"]
    P["bg_theta"] = pr.uniform(0, 2 * math.pi)
    P["tex_loss_target"] = sev["texture_continuity"]
    P["ghost_alpha"] = sev["ghost_text_residue"] * PHYS["ghost_max_alpha"]
    P["ghost_offset"] = (pr.choice([-3, -2, 2, 3]), pr.choice([-2, -1, 1, 2]))
    P["light_drop"] = sev["lighting_consistency"] * PHYS["light_max_drop"]
    P["light_angle"] = pr.choice([0, 45, 90, 135, 180, 225, 270, 315])

    s = sev["reading_flow"]
    sign = pr.choice([-1, 1])
    P["flow"] = {"sign": sign, "spacing_mult": 1 + s * PHYS["flow_max_spacing"] if sign > 0 else 1 - s * PHYS["flow_max_spacing"] * 0.5,
                 "jitter": s * PHYS["flow_max_jitter"], "seed": pr.randint(0, 10**9)}

    s = sev["visual_anchor_integrity"]
    P["anchor"] = {"shrink": s * PHYS["anchor_max_shrink"], "shift": s * PHYS["anchor_max_shift"],
                   "angles": [pr.uniform(0, 2 * math.pi) for _ in doc.blocks], "rule_sev": s, "seed": pr.randint(0, 10**9)}

    # emphasis
    span_keys = []
    for bi, b in enumerate(doc.blocks):
        ids, n = _span_ids(b)
        span_keys += [(bi, i) for i in range(n)]
    n_lose = int(round(sev["semantic_emphasis"] * len(span_keys)))
    P["emph_lost"] = set(pr.sample(span_keys, n_lose)) if span_keys else set()
    P["emph_total"] = len(span_keys)

    s = sev["authenticity"]
    P["jpeg_q"] = int(round(PHYS["auth_jpeg_q_max"] - s * (PHYS["auth_jpeg_q_max"] - PHYS["auth_jpeg_q_min"])))
    P["auth_noise"] = s * PHYS["auth_max_noise"]
    P["seed"] = seed
    return P


def _fits(doc, mult):
    for b in doc.blocks:
        for line in b.lines:
            lw = _line_width(line, b.family, b.size, b.role, set(), None) * mult * 1.08
            if b.align == "left" and b.x + lw > doc.width - 8:
                return False
            if b.align == "right" and b.x + b.w - lw < 8:
                return False
            if b.align == "center" and lw > doc.width - 16:
                return False
    return True


def _run_font(family, style, size, role, lost):
    bold = (style in ("bold", "accent") and not lost) or role in ("title", "heading")
    return get_font(family, bold, size)


def _line_width(line, family, size, role, lost_keys, texts):
    sp = get_font(family, False, size).getlength(" ")
    w = 0.0
    for k, r in enumerate(line):
        t = texts[k] if texts else r.text
        w += _run_font(family, r.style, size, role, k in lost_keys).getlength(t)
    return w + sp * max(0, len(line) - 1)


def layout(doc, P=None):
    """Return per-block list of lines: dict(x, y, h, runs=[(x, text, font, color)], text, w)."""
    out = []
    for bi, b in enumerate(doc.blocks):
        span_of, _ = _span_ids(b)
        fam, size, spacing, dx, dy = b.family, b.size, 1.0, 0.0, 0.0
        jit_rng = None
        if P is not None:
            f = P["font"]
            fam = f["family_map"].get(b.family, b.family)
            size = b.size * f["size_mult"]
            dx, dy = P["align"][bi]
            spacing = P["flow"]["spacing_mult"]
            jit_rng = random.Random(P["flow"]["seed"] + bi)
            if b.role in ("title", "heading"):
                a = P["anchor"]
                size *= 1 - a["shrink"]
                dx += a["shift"] * math.cos(a["angles"][bi])
                dy += a["shift"] * math.sin(a["angles"][bi])
        lines = []
        lh = size * b.line_gap * spacing
        for j, line in enumerate(b.lines):
            lost = {k for k in range(len(line)) if P is not None and (bi, span_of.get((j, k), -1)) in P["emph_lost"]}
            texts = []
            for k, r in enumerate(line):
                t = r.text
                if P is not None and (bi, j, k) in P["ocr_subs"]:
                    chars = list(t)
                    for ci, new in P["ocr_subs"][(bi, j, k)].items():
                        chars[ci] = new
                    t = "".join(chars)
                texts.append(t)
            lw = _line_width(line, fam, size, b.role, lost, texts)
            if b.align == "center":
                x0 = b.x + (b.w - lw) / 2
            elif b.align == "right":
                x0 = b.x + b.w - lw
            else:
                x0 = b.x
            jitter = (jit_rng.uniform(-1, 1) * P["flow"]["jitter"] * size * b.line_gap) if jit_rng else 0.0
            y0 = b.y + j * lh + dy + jitter
            x0 += dx
            sp = get_font(fam, False, size).getlength(" ")
            runs, x = [], x0
            for k, r in enumerate(line):
                font = _run_font(fam, r.style, size, b.role, k in lost)
                col = b.accent if (r.style == "accent" and k not in lost) else b.color
                runs.append((x, texts[k], font, tuple(col)))
                x += font.getlength(texts[k]) + sp
            lines.append({"x": x0, "y": y0, "w": lw, "h": size * 1.25, "runs": runs, "text": " ".join(texts)})
        out.append(lines)
    return out


def _draw_lines(draw, lines, alpha=255, offset=(0, 0)):
    for ln in lines:
        for (x, t, font, col) in ln["runs"]:
            draw.text((x + offset[0], ln["y"] + offset[1]), t, font=font, fill=tuple(col) + (alpha,))


def _draw_rule(draw, ru, sev, rng):
    width = max(1, int(round(ru.width * (1 - 0.6 * sev))))
    length = math.hypot(ru.x2 - ru.x1, ru.y2 - ru.y1)
    if sev <= 0 or length < 4:
        draw.line((ru.x1, ru.y1, ru.x2, ru.y2), fill=tuple(ru.color) + (255,), width=width)
        return
    gap_total = sev * 0.7
    n_gaps = 3
    starts = sorted(rng.uniform(0, 1 - gap_total / n_gaps) for _ in range(n_gaps))
    segs, t = [], 0.0
    for s in starts:
        if s > t:
            segs.append((t, s))
        t = max(t, s + gap_total / n_gaps)
    if t < 1:
        segs.append((t, 1))
    for a, b in segs:
        draw.line((ru.x1 + (ru.x2 - ru.x1) * a, ru.y1 + (ru.y2 - ru.y1) * a,
                   ru.x1 + (ru.x2 - ru.x1) * b, ru.y1 + (ru.y2 - ru.y1) * b), fill=tuple(ru.color) + (255,), width=width)


# ------------------------------------------------------------------ main render
def render(doc, sev: dict | None = None, seed: int = 0):
    """Render the document. sev=None -> Original. Returns (PIL.Image, info)."""
    sev = {k: float(np.clip((sev or {}).get(k, 0.0), 0, 1)) for k in METRIC_KEYS}
    P = plan_release(doc, sev, seed)
    is_orig = all(v == 0 for v in sev.values())
    H, W = doc.height, doc.width
    bg = render_background(doc)
    canvas = Image.fromarray(bg.astype(np.uint8)).convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    rrng = random.Random(P["anchor"]["seed"])
    for ru in doc.rules:
        _draw_rule(draw, ru, P["anchor"]["rule_sev"], rrng)

    for obj, op in zip(doc.objects, P["objects"]):
        tile = draw_object_tile(obj)
        if op["scale"] < 0.999:
            tile = tile.resize((max(2, int(tile.width * op["scale"])), max(2, int(tile.height * op["scale"]))), Image.LANCZOS)
        if op["opacity"] < 0.999:
            a = np.asarray(tile).copy()
            a[..., 3] = (a[..., 3] * op["opacity"]).astype(np.uint8)
            tile = Image.fromarray(a)
        cx = obj.x + obj.w / 2 + op["shift"] * math.cos(op["angle"])
        cy = obj.y + obj.h / 2 + op["shift"] * math.sin(op["angle"])
        canvas.alpha_composite(tile, (int(round(cx - tile.width / 2)), int(round(cy - tile.height / 2))))

    orig_layout = layout(doc, None)
    rel_layout = orig_layout if is_orig else layout(doc, P)

    # --- inpainting patches over every original text region (the "removed then re-rendered" area)
    arr = np.asarray(canvas).astype(np.float32)
    patches = []
    for lines in orig_layout:
        if not lines:
            continue
        x0 = int(max(0, min(l["x"] for l in lines) - 3))
        y0 = int(max(0, min(l["y"] for l in lines) - 3))
        x1 = int(min(W, max(l["x"] + l["w"] for l in lines) + 3))
        y1 = int(min(H, max(l["y"] + l["h"] for l in lines) + 3))
        if x1 - x0 > 4 and y1 - y0 > 4:
            patches.append((x0, y0, x1, y1))

    tex_sigma, tex_realised, de_realised, area_tot = 0.0, 0.0, 0.0, 0.0
    if P["tex_loss_target"] > 0 and patches:
        big = max(patches, key=lambda p: (p[2] - p[0]) * (p[3] - p[1]))
        bp = bg[big[1]:big[3], big[0]:big[2]]
        lo, hi = 0.0, PHYS["tex_max_sigma"]
        for _ in range(12):
            mid = (lo + hi) / 2
            if _texture_loss(bp, mid)[0] < P["tex_loss_target"]:
                lo = mid
            else:
                hi = mid
        tex_sigma = (lo + hi) / 2
    nrng = np.random.default_rng(seed + 7)
    for (x0, y0, x1, y1) in patches:
        src = bg[y0:y1, x0:x1].copy()
        loss, p = _texture_loss(src, tex_sigma)
        p = _chroma_shift(p, P["bg_delta_e"], P["bg_theta"])
        if P["auth_noise"] > 0:
            p = p + nrng.normal(0, P["auth_noise"], p.shape)
        p = np.clip(p, 0, 255)
        area = (x1 - x0) * (y1 - y0)
        tex_realised += loss * area
        de_realised += (_de2000(_rgb2lab(src).reshape(-1, 3).mean(0), _rgb2lab(p).reshape(-1, 3).mean(0))
                        if P["bg_delta_e"] > 0 else 0.0) * area
        area_tot += area
        arr[y0:y1, x0:x1, :3] = p
    canvas = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")

    # --- ghost residue of the original glyphs
    if P["ghost_alpha"] > 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for lines in orig_layout:
            _draw_lines(ImageDraw.Draw(layer), lines, int(255 * P["ghost_alpha"]), P["ghost_offset"])
        canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(0.6)))

    # --- re-rendered text
    draw = ImageDraw.Draw(canvas)
    for lines in rel_layout:
        _draw_lines(draw, lines)

    out = np.asarray(canvas.convert("RGB")).astype(np.float32)

    # --- lighting gradient
    if P["light_drop"] > 0:
        a = math.radians(P["light_angle"])
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        proj = (xx - W / 2) * math.cos(a) + (yy - H / 2) * math.sin(a)
        t = (proj - proj.min()) / (proj.max() - proj.min() + 1e-6)
        out *= (1 - P["light_drop"] * t)[..., None]
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

    # --- compression (authenticity); original also passes at q=95 for symmetry
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=P["jpeg_q"], subsampling=0 if P["jpeg_q"] >= 90 else 2)
    img = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")

    # --- realised severities (ground truth)
    f = P["font"]
    realised = {
        "ocr_accuracy": min(1.0, P["ocr_cer"] / PHYS["ocr_max_cer"]),
        "alignment_preservation": sev["alignment_preservation"],
        "font_similarity": min(1.0, PHYS["font_w_size"] * abs(f["size_mult"] - 1) / PHYS["font_max_size_delta"]
                               + PHYS["font_w_family"] * f["family_term"]),
        "object_preservation": sev["object_preservation"] if doc.objects else 0.0,
        "background_fidelity": min(1.0, (de_realised / area_tot if area_tot else 0) / PHYS["bg_max_delta_e"]),
        "texture_continuity": (tex_realised / area_tot) if area_tot else 0.0,
        "ghost_text_residue": sev["ghost_text_residue"],
        "lighting_consistency": sev["lighting_consistency"],
        "reading_flow": sev["reading_flow"],
        "visual_anchor_integrity": sev["visual_anchor_integrity"],
        "semantic_emphasis": (len(P["emph_lost"]) / P["emph_total"]) if P["emph_total"] else 0.0,
        "authenticity": (PHYS["auth_jpeg_q_max"] - P["jpeg_q"]) / (PHYS["auth_jpeg_q_max"] - PHYS["auth_jpeg_q_min"]),
    }
    realised = {k: round(float(np.clip(v, 0, 1)), 4) for k, v in realised.items()}

    # examples for the reasoning text
    ocr_examples = []
    for (bi, j, k), m in list(P["ocr_subs"].items())[:3]:
        orig_t = doc.blocks[bi].lines[j][k].text
        chars = list(orig_t)
        for ci, new in m.items():
            chars[ci] = new
        # show only the affected word (runs of tables can be whole lines)
        ci = min(m)
        a = orig_t.rfind(" ", 0, ci) + 1
        b = orig_t.find(" ", ci)
        b = len(orig_t) if b < 0 else b
        new_t = "".join(chars)
        nb = new_t.find(" ", ci)
        ocr_examples.append([orig_t[a:b], new_t[a:(len(new_t) if nb < 0 else nb)]])

    def boxes(lay):
        bx = []
        for bi, lines in enumerate(lay):
            for ln in lines:
                bx.append({"block": doc.blocks[bi].id, "role": doc.blocks[bi].role, "text": ln["text"],
                           "bbox": [round(ln["x"], 1), round(ln["y"], 1), round(ln["x"] + ln["w"], 1), round(ln["y"] + ln["h"], 1)]})
        return bx

    details = {
        "ocr_cer": round(P["ocr_cer"], 4), "ocr_examples": ocr_examples,
        "align_mean_shift_px": round(float(np.mean([math.hypot(*d) for d in P["align"]])) if P["align"] else 0.0, 2),
        "font_family_term": f["family_term"], "font_size_mult": round(f["size_mult"], 4),
        "font_family_map": {k: v for k, v in f["family_map"].items() if k != v},
        "obj_scale": round(1 - sev["object_preservation"] * PHYS["obj_max_scale_loss"], 3),
        "obj_shift_px": round(sev["object_preservation"] * PHYS["obj_max_shift"], 1),
        "obj_opacity": round(1 - sev["object_preservation"] * PHYS["obj_max_fade"], 3),
        "n_objects": len(doc.objects),
        "bg_delta_e2000": round(de_realised / area_tot, 2) if area_tot else 0.0,
        "tex_blur_sigma": round(tex_sigma, 3), "tex_detail_loss": round(tex_realised / area_tot, 4) if area_tot else 0.0,
        "ghost_alpha": round(P["ghost_alpha"], 3), "ghost_offset_px": list(P["ghost_offset"]),
        "light_drop": round(P["light_drop"], 3), "light_angle_deg": P["light_angle"],
        "line_spacing_mult": round(P["flow"]["spacing_mult"], 3), "baseline_jitter": round(P["flow"]["jitter"], 3),
        "anchor_shrink": round(P["anchor"]["shrink"], 3), "anchor_shift_px": round(P["anchor"]["shift"], 1),
        "emph_lost": len(P["emph_lost"]), "emph_total": P["emph_total"],
        "jpeg_quality": P["jpeg_q"], "patch_noise_std": round(P["auth_noise"], 2),
    }
    info = {"realised_severity": realised, "details": details,
            "ocr_boxes_original": boxes(orig_layout), "ocr_boxes_release": boxes(rel_layout)}
    return img, info
