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
_BG_CACHE = {}


def render_background(doc) -> np.ndarray:
    """Deterministic in the Background spec; memoised (one entry) because the ladder renders the same
    document 26 times. Returns a fresh copy so callers may modify it."""
    bgd = doc.background
    key = repr((doc.width, doc.height, bgd))
    if key not in _BG_CACHE:
        _BG_CACHE.clear()
        _BG_CACHE[key] = _render_background(doc)
    return _BG_CACHE[key].copy()


def _render_background(doc) -> np.ndarray:
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


def _run_font(family, style, size, role, lost, exact=False, force_bold=False):
    bold = force_bold or (style in ("bold", "accent") and not lost) or role in ("title", "heading")
    return get_font(family, bold, size, exact)


def _line_width(line, family, size, role, lost_keys, texts, exact=False, force_bold=False):
    sp = get_font(family, False, size, exact).getlength(" ")
    w = 0.0
    for k, r in enumerate(line):
        t = texts[k] if texts else r.text
        w += _run_font(family, r.style, size, role, k in lost_keys, exact, force_bold).getlength(t)
    return w + sp * max(0, len(line) - 1)


def shift_color(c, v):
    """Move a colour by v grey levels per channel towards mid-grey (dark ink gets lighter,
    light ink on dark UIs gets darker), i.e. towards lower contrast."""
    s = 1 if sum(c[:3]) / 3 < 128 else -1
    return tuple(int(np.clip(ch + s * v, 0, 255)) for ch in c[:3])


def layout(doc, P=None, local=None):
    """Return per-block list of lines: dict(x, y, h, runs=[(x, text, font, color)], text, w).
    local = one-block edit (ladder): {block, supersample, family, bold, size_mult, color_delta, dx, pitch_px}.
    The local block is laid out with fonts at `supersample` x size (positions stay in page pixels) because
    Pillow rasterises at whole-pixel sizes: a 1% size change only survives when drawn supersampled."""
    out = []
    for bi, b in enumerate(doc.blocks):
        span_of, _ = _span_ids(b)
        fam, size, spacing, dx, dy = b.family, b.size, 1.0, 0.0, 0.0
        L = local if local is not None and local["block"] == bi else None
        exact, force_bold, pitch_px, cdelta, ss = False, False, 0.0, 0, 1
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
        if local is not None and local.get("anchor") == bi:
            dx += local.get("anchor_dx", 0.0)  # visual-anchor edit: move one heading/title
        pitch_size = size
        if L is not None:
            fam = L.get("family") or fam
            force_bold = bool(L.get("bold"))
            ss = int(L.get("supersample", 1))
            size, exact = size * L.get("size_mult", 1.0), True
            dx += L.get("dx", 0.0)
            pitch_px = L.get("pitch_px", 0.0)
            cdelta = L.get("color_delta", 0)
        lines = []
        # a ladder font-size edit keeps the original line pitch (isolates size from spacing)
        lh = pitch_size * b.line_gap * spacing + pitch_px
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
                if L is not None and (j, k) in L.get("ocr_subs", {}):
                    chars = list(t)
                    for ci, new in L["ocr_subs"][(j, k)].items():
                        chars[ci] = new
                    t = "".join(chars)
                texts.append(t)
            lw = _line_width(line, fam, size * ss, b.role, lost, texts, exact, force_bold) / ss
            if b.align == "center":
                x0 = b.x + (b.w - lw) / 2
            elif b.align == "right":
                x0 = b.x + b.w - lw
            else:
                x0 = b.x
            jitter = (jit_rng.uniform(-1, 1) * P["flow"]["jitter"] * size * b.line_gap) if jit_rng else 0.0
            y0 = b.y + j * lh + dy + jitter
            x0 += dx
            sp = get_font(fam, False, size * ss, exact).getlength(" ") / ss
            runs, x = [], x0
            for k, r in enumerate(line):
                font = _run_font(fam, r.style, size * ss, b.role, k in lost, exact, force_bold)
                col = b.accent if (r.style == "accent" and k not in lost) else b.color
                if cdelta:
                    col = shift_color(col, cdelta)
                runs.append((x, texts[k], font, tuple(col)))
                x += font.getlength(texts[k]) / ss + sp
            lines.append({"x": x0, "y": y0, "w": lw, "h": size * 1.25, "runs": runs, "text": " ".join(texts), "ss": ss})
        out.append(lines)
    return out


def _draw_lines(draw, lines, alpha=255, offset=(0, 0)):
    for ln in lines:
        for (x, t, font, col) in ln["runs"]:
            draw.text((x + offset[0], ln["y"] + offset[1]), t, font=font, fill=tuple(col) + (alpha,))


def _draw_lines_supersampled(canvas, lines, ss):
    """Draw one block on an ss-times larger transparent layer and downsample it into the canvas."""
    pad = int(math.ceil(max(l["h"] for l in lines) * 0.6)) + 2
    x0 = max(0, int(math.floor(min(l["x"] for l in lines))) - pad)
    y0 = max(0, int(math.floor(min(l["y"] for l in lines))) - pad)
    x1 = min(canvas.width, int(math.ceil(max(l["x"] + l["w"] for l in lines))) + pad)
    y1 = min(canvas.height, int(math.ceil(max(l["y"] + l["h"] for l in lines))) + pad)
    layer = Image.new("RGBA", ((x1 - x0) * ss, (y1 - y0) * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for ln in lines:
        for (x, t, font, col) in ln["runs"]:
            d.text(((x - x0) * ss, (ln["y"] - y0) * ss), t, font=font, fill=tuple(col) + (255,))
    small = layer.convert("RGBa").resize((x1 - x0, y1 - y0), Image.LANCZOS).convert("RGBA")
    canvas.alpha_composite(small, (x0, y0))


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


def _lines_bbox(lines, pad=3):
    return [min(l["x"] for l in lines) - pad, min(l["y"] for l in lines) - pad,
            max(l["x"] + l["w"] for l in lines) + pad, max(l["y"] + l["h"] for l in lines) + pad]


def _measure_local(doc, L, bg_de, emph_total, orig_layout, rel_layout, tex=None):
    """Measure what a one-block ladder edit actually changed and convert it to severities on the
    same physical scales (PHYS) as the main releases. Convention: severity of the edited region."""
    bi = L["block"]
    b = doc.blocks[bi]
    # Pillow draws at floor(px + 0.5) whole pixels, so measure the size that was really drawn
    ss = int(L.get("supersample", 1))
    mult = L.get("size_mult", 1.0)
    drawn = lambda px: math.floor(round(px * 64) / 64 + 0.5)  # noqa: E731
    size_mult = drawn(b.size * mult * ss) / drawn(b.size * ss) if mult != 1.0 else 1.0
    fam = L.get("family") or b.family
    fam_term = 0.0 if fam == b.family else (0.5 if FONT_FAMILIES[fam][0] == FONT_FAMILIES[b.family][0] else 1.0)
    weight = 1.0 if L.get("bold") and b.role not in ("title", "heading") and any(
        r.style == "normal" for ln in b.lines for r in ln) else 0.0
    text_de = _de2000(_rgb2lab(np.array(b.color, float)), _rgb2lab(np.array(shift_color(b.color, L["color_delta"]), float))) \
        if L.get("color_delta") else 0.0
    dx = float(L.get("dx", 0.0))
    pitch = float(L.get("pitch_px", 0.0)) if len(b.lines) > 1 else 0.0
    pitch_rel = pitch / (b.size * b.line_gap)
    bold_spans = 0
    if L.get("bold"):
        ids, _ = _span_ids(b)
        styles = {}
        for (j, k), s in ids.items():
            styles[s] = b.lines[j][k].style
        bold_spans = sum(1 for s in styles.values() if s == "bold")
    font_sev = (PHYS["font_w_size"] * abs(size_mult - 1) / PHYS["font_max_size_delta"] + PHYS["font_w_family"] * fam_term
                + PHYS["font_w_weight"] * weight + PHYS["font_w_color"] * min(1.0, text_de / PHYS["font_color_max_de"]))
    severity = {
        "font_similarity": min(1.0, font_sev),
        "alignment_preservation": min(1.0, dx / math.hypot(PHYS["align_max_dx"], PHYS["align_max_dy"])),
        "reading_flow": min(1.0, pitch_rel / PHYS["flow_max_spacing"]),
        "background_fidelity": min(1.0, bg_de / PHYS["bg_max_delta_e"]),
        "semantic_emphasis": (bold_spans / emph_total) if emph_total else 0.0,
    }
    n_alnum = sum(ch.isalnum() for ln in b.lines for r in ln for ch in r.text)
    n_sub = sum(len(m) for m in L.get("ocr_subs", {}).values())
    block_cer = n_sub / n_alnum if n_alnum else 0.0
    tex = tex or {"loss": 0.0, "sigma": 0.0}
    jpeg_q = int(L.get("jpeg_q") or PHYS["auth_jpeg_q_max"])
    obj_dx, anchor_dx = float(L.get("obj_dx", 0.0)), float(L.get("anchor_dx", 0.0))
    severity.update({
        "ocr_accuracy": min(1.0, block_cer / PHYS["ocr_max_cer"]),
        "ghost_text_residue": min(1.0, float(L.get("ghost_alpha", 0.0)) / PHYS["ghost_max_alpha"]),
        "texture_continuity": float(tex["loss"]),
        "lighting_consistency": min(1.0, float(L.get("light_drop", 0.0)) / PHYS["light_max_drop"]),
        "authenticity": (PHYS["auth_jpeg_q_max"] - jpeg_q) / (PHYS["auth_jpeg_q_max"] - PHYS["auth_jpeg_q_min"]),
        "object_preservation": min(1.0, obj_dx / PHYS["obj_max_shift"]),
        "visual_anchor_integrity": min(1.0, anchor_dx / PHYS["anchor_max_shift"]),
    })
    ob, rb = _lines_bbox(orig_layout[bi]), _lines_bbox(rel_layout[bi])
    boxes = [ob, rb]
    if L.get("anchor") is not None:
        boxes += [_lines_bbox(orig_layout[L["anchor"]]), _lines_bbox(rel_layout[L["anchor"]])]
    if L.get("light_drop"):
        boxes.append([rb[0] - 12, rb[1] - 12, rb[2] + 12, rb[3] + 12])
    if L.get("object") is not None:
        o = doc.objects[L["object"]]
        boxes.append([o.x - 4, o.y - 4, o.x + o.w + obj_dx + 4, o.y + o.h + 4])
    region = [int(math.floor(min(x[0] for x in boxes))), int(math.floor(min(x[1] for x in boxes))),
              int(math.ceil(max(x[2] for x in boxes))), int(math.ceil(max(x[3] for x in boxes)))]
    words = " ".join(line_text(l) for l in b.lines).split()
    return {"severity": severity, "block_id": b.id, "block_role": b.role, "n_lines": len(b.lines),
            "first_words": " ".join(words[:4]) + (" ..." if len(words) > 4 else ""), "page_size": [doc.width, doc.height],
            "region_bbox": region, "size_mult": round(size_mult, 5), "family_from": b.family, "family_to": fam,
            "family_term": fam_term, "weight_changed": bool(weight), "text_delta_e2000": round(text_de, 3),
            "text_color_from": list(b.color[:3]),
            "text_color_to": list(shift_color(b.color, L["color_delta"])) if L.get("color_delta") else list(b.color[:3]),
            "dx_px": dx, "pitch_px": pitch, "pitch_rel": round(pitch_rel, 4), "bg_delta_e2000": round(bg_de, 3),
            "emph_bold_spans_lost": bold_spans, "chars_substituted": n_sub, "block_alnum_chars": n_alnum,
            "block_cer": round(block_cer, 5), "ghost_alpha": float(L.get("ghost_alpha", 0.0)),
            "tex_loss": round(float(tex["loss"]), 5), "tex_sigma": round(float(tex["sigma"]), 4),
            "light_drop": float(L.get("light_drop", 0.0)), "jpeg_q": jpeg_q, "obj_dx_px": obj_dx,
            "object_kind": doc.objects[L["object"]].kind if L.get("object") is not None else None,
            "anchor_dx_px": anchor_dx,
            "anchor_block": doc.blocks[L["anchor"]].id if L.get("anchor") is not None else None,
            "anchor_text": " ".join(line_text(l) for l in doc.blocks[L["anchor"]].lines)[:40] if L.get("anchor") is not None else None}


# ------------------------------------------------------------------ main render
def render(doc, sev: dict | None = None, seed: int = 0, local: dict | None = None):
    """Render the document. sev=None -> Original. Returns (PIL.Image, info).

    local: optional one-block edit used by the minute-change ladder (prism/ladder.py):
    {block: index, family, bold, size_mult, color_delta, dx, pitch_px, bg_delta}. Everything
    outside that block is rendered exactly as the Original; the change is measured and merged
    into the realised severities."""
    sev = {k: float(np.clip((sev or {}).get(k, 0.0), 0, 1)) for k in METRIC_KEYS}
    P = plan_release(doc, sev, seed)
    is_orig = all(v == 0 for v in sev.values()) and not local
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
        if local and local.get("object") is not None and doc.objects[local["object"]] is obj:
            cx += local.get("obj_dx", 0.0)
        canvas.alpha_composite(tile, (int(round(cx - tile.width / 2)), int(round(cy - tile.height / 2))))

    orig_layout = layout(doc, None)
    rel_layout = orig_layout if is_orig else layout(doc, P, local)

    # --- inpainting patches over every original text region (the "removed then re-rendered" area)
    arr = np.asarray(canvas).astype(np.float32)
    patches = []
    for bi, lines in enumerate(orig_layout):
        if not lines:
            continue
        x0 = int(max(0, min(l["x"] for l in lines) - 3))
        y0 = int(max(0, min(l["y"] for l in lines) - 3))
        x1 = int(min(W, max(l["x"] + l["w"] for l in lines) + 3))
        y1 = int(min(H, max(l["y"] + l["h"] for l in lines) + 3))
        if x1 - x0 > 4 and y1 - y0 > 4:
            patches.append((x0, y0, x1, y1, bi))

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
    local_bg_de, local_bg_offset, local_tex = 0.0, 0, {"loss": 0.0, "sigma": 0.0}
    for (x0, y0, x1, y1, bi) in patches:
        src = bg[y0:y1, x0:x1].copy()
        loss, p = _texture_loss(src, tex_sigma)
        if local and local.get("tex_loss") and bi == local["block"]:
            # texture smoothing: blur the paper grain of this one patch until the measured loss hits the target
            lo, hi = 0.0, PHYS["tex_max_sigma"]
            for _ in range(14):
                mid = (lo + hi) / 2
                if _texture_loss(src, mid)[0] < local["tex_loss"]:
                    lo = mid
                else:
                    hi = mid
            local_tex["sigma"] = (lo + hi) / 2
            local_tex["loss"], p = _texture_loss(src, local_tex["sigma"])
        p = _chroma_shift(p, P["bg_delta_e"], P["bg_theta"])
        if P["auth_noise"] > 0:
            p = p + nrng.normal(0, P["auth_noise"], p.shape)
        if local and local.get("bg_delta") and bi == local["block"]:
            # inpaint colour mismatch: the re-filled patch is a few grey levels off (towards mid-grey)
            local_bg_offset = (-1 if src.mean() >= 128 else 1) * int(local["bg_delta"])
            p = p + local_bg_offset
            local_bg_de = _de2000(_rgb2lab(src).reshape(-1, 3).mean(0),
                                  _rgb2lab(np.clip(p, 0, 255)).reshape(-1, 3).mean(0))
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

    if local and local.get("ghost_alpha"):
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        _draw_lines(ImageDraw.Draw(layer), orig_layout[local["block"]], int(round(255 * local["ghost_alpha"])),
                    local.get("ghost_offset", (2, 1)))
        canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(0.6)))

    # --- re-rendered text
    draw = ImageDraw.Draw(canvas)
    for lines in rel_layout:
        if lines and lines[0].get("ss", 1) > 1:
            _draw_lines_supersampled(canvas, lines, lines[0]["ss"])
        else:
            _draw_lines(draw, lines)

    out = np.asarray(canvas.convert("RGB")).astype(np.float32)

    # --- lighting gradient
    if P["light_drop"] > 0:
        a = math.radians(P["light_angle"])
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        proj = (xx - W / 2) * math.cos(a) + (yy - H / 2) * math.sin(a)
        t = (proj - proj.min()) / (proj.max() - proj.min() + 1e-6)
        out *= (1 - P["light_drop"] * t)[..., None]
    local_box = None
    if local:
        lb = _lines_bbox(rel_layout[local["block"]])
        local_box = [max(0, int(math.floor(lb[0]))), max(0, int(math.floor(lb[1]))),
                     min(W, int(math.ceil(lb[2]))), min(H, int(math.ceil(lb[3])))]
    if local and local.get("light_drop"):
        # uneven lighting on one block: a soft shadow, light_drop darker at its centre and fading to zero at
        # every edge (raised-cosine profile, so there is no visible patch boundary)
        x0, y0, x1, y1 = local_box
        pad = 12
        x0, y0, x1, y1 = max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad), min(H, y1 + pad)
        u = np.sin(np.pi * np.linspace(0, 1, x1 - x0, dtype=np.float32))
        v = np.sin(np.pi * np.linspace(0, 1, y1 - y0, dtype=np.float32))
        out[y0:y1, x0:x1] *= (1 - local["light_drop"] * (v[:, None] * u[None, :]))[..., None]
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

    # --- compression (authenticity); original also passes at q=95 for symmetry
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=P["jpeg_q"], subsampling=0 if P["jpeg_q"] >= 90 else 2)
    img = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
    if local and local.get("jpeg_q"):
        # re-saved patch: the block area (snapped to the 8x8 JPEG grid) is re-compressed at a lower quality
        x0, y0 = local_box[0] // 8 * 8, local_box[1] // 8 * 8
        x1, y1 = min(W, -(-local_box[2] // 8) * 8), min(H, -(-local_box[3] // 8) * 8)
        b2 = io.BytesIO()
        img.crop((x0, y0, x1, y1)).save(b2, "JPEG", quality=int(local["jpeg_q"]), subsampling=0)
        img.paste(Image.open(io.BytesIO(b2.getvalue())).convert("RGB"), (x0, y0))

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
    local_info = None
    if local:
        local_info = _measure_local(doc, local, local_bg_de, P["emph_total"], orig_layout, rel_layout, local_tex)
        local_info["bg_offset"] = local_bg_offset
        for k, v in local_info["severity"].items():
            realised[k] = max(realised[k], v)
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
    if local_info:
        details["local"] = {k: v for k, v in local_info.items() if k != "severity"}
    info = {"realised_severity": realised, "details": details,
            "ocr_boxes_original": boxes(orig_layout), "ocr_boxes_release": boxes(rel_layout)}
    return img, info
