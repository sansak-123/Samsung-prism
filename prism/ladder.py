"""Minute-change ladder: 1 unchanged control + N edit families x 4 levels per Original.

The first 6 edit families and their levels follow the "Minute Change Lab" generator
(github.com/Sanjana432/prism_iqa, prism/generation.py: LADDERS) - 6 x 4 = the "24 generation".
7 further minute families extend the ladder so that 11 of the 12 metrics get their own single-factor
ladder. Differences from that repo:
  * the edit is applied to ONE text block (or one object / one heading) of a full PRISM template;
  * every release gets MEASURED ground-truth scores for all 12 metrics, computed automatically by the
    renderer during generation (no manual annotation anywhere), on the same physical scales (metrics.PHYS)
    as the R1/R2/R3 releases; each score carries its written-out calculation (`score_calculation`);
  * everything outside the edited area is rendered exactly as the Original (audited per release), and
    image-only pixel measurements (`pixel_measurements`) give an independent cross-check.

Edit family -> metric it moves
  -- prism_iqa families (24 releases) --
  font_family (nominal)          -> font_similarity (+ semantic_emphasis for the bold variant)
  font_size  x1.01..x1.10        -> font_similarity
  font_color +2..+20 grey levels -> font_similarity (dE2000 of the ink colour)
  inpaint_color_mismatch 1..12   -> background_fidelity (dE2000 of the re-filled patch)
  justification 1..8 px          -> alignment_preservation
  line_spacing  +1..+8 px        -> reading_flow
  -- added minute families (28 releases) --
  char_substitution 1..5 chars   -> ocr_accuracy (look-alike characters, e.g. 0/O, 1/l)
  ghost_residue alpha 2..20 %    -> ghost_text_residue (faint copy of the old glyphs)
  texture_smoothing 5..35 %      -> texture_continuity (paper grain blurred in the re-filled patch)
  lighting_drop 2..15 %          -> lighting_consistency (brightness falls across the block)
  local_compression q92..q72     -> authenticity (block area re-saved as a lower-quality JPEG)
  object_shift 1..8 px           -> object_preservation (one logo / QR / stamp / photo moved)
  heading_shift 1..8 px          -> visual_anchor_integrity (one title / heading moved)
"""

from __future__ import annotations

import math
import os
import random
from datetime import datetime, timezone

import numpy as np

from .document import FAMILIES_BY_CLASS, FONT_FAMILIES, line_text
from .metrics import METRIC_KEYS, PHYS
from .pixel_evidence import compare
from .reasoning import build_reasoning, scores_from_severity
from .render import CONFUSABLE, layout, render
from .scoring import category_scores
from .templates import build_document

BASE_KNOBS = ["font_family", "font_size", "font_color", "inpaint_color_mismatch", "justification", "line_spacing"]
MINUTE_KNOBS = ["char_substitution", "ghost_residue", "texture_smoothing", "lighting_drop", "local_compression",
                "object_shift", "heading_shift"]
KNOBS = BASE_KNOBS + MINUTE_KNOBS
LADDERS = {
    "font_family": ["same_class", "cross_class", "third_class", "cross_class_bold"],  # nominal, not ranked
    "font_size": [1.01, 1.025, 1.05, 1.10],
    "font_color": [2, 5, 10, 20],
    "inpaint_color_mismatch": [1, 3, 6, 12],
    "justification": [1, 2, 4, 8],
    "line_spacing": [1, 2, 4, 8],
    "char_substitution": [1, 2, 3, 5],
    "ghost_residue": [0.02, 0.05, 0.10, 0.20],
    "texture_smoothing": [0.05, 0.10, 0.20, 0.35],
    "lighting_drop": [0.02, 0.04, 0.08, 0.15],
    "local_compression": [92, 88, 82, 72],
    "object_shift": [1, 2, 4, 8],
    "heading_shift": [1, 2, 4, 8],
}
KNOB_METRIC = {"font_family": "font_similarity", "font_size": "font_similarity", "font_color": "font_similarity",
               "inpaint_color_mismatch": "background_fidelity", "justification": "alignment_preservation",
               "line_spacing": "reading_flow", "char_substitution": "ocr_accuracy",
               "ghost_residue": "ghost_text_residue", "texture_smoothing": "texture_continuity",
               "lighting_drop": "lighting_consistency", "local_compression": "authenticity",
               "object_shift": "object_preservation", "heading_shift": "visual_anchor_integrity"}
ORDINAL_KNOBS = [k for k in KNOBS if k != "font_family"]
CANDIDATE_ROLES = ("body", "small")
SHIFT_MAX = max(LADDERS["object_shift"] + LADDERS["heading_shift"])
JPEG_BLOCK = 8  # changes may bleed to the surrounding 8x8 JPEG blocks (q95, no chroma subsampling)


def active_knobs(cfg: dict) -> list:
    knobs = cfg.get("ladder", {}).get("knobs") or KNOBS
    unknown = set(knobs) - set(KNOBS)
    if unknown:
        raise ValueError(f"unknown ladder knobs {sorted(unknown)}; choose from {KNOBS}")
    return [k for k in KNOBS if k in knobs]


def settings(knobs=None):
    return [("control", 0, None)] + [(k, n + 1, v) for k in (KNOBS if knobs is None else knobs) for n, v in enumerate(LADDERS[k])]


def family_options(base: str, rng: random.Random) -> dict:
    """Ordered candidate typefaces per nominal font-family level (first one that fits the layout is used).
    same_class: same style class; cross_class (+ its bold variant): the other text class (sans <-> serif);
    third_class: monospace (serif for mono text) preferred, falling back to another cross-class typeface
    when monospace would run off the page or into a neighbour. artifact_value always records the real font."""
    cls = FONT_FAMILIES[base][0]
    other = {"sans": "serif", "serif": "sans", "mono": "sans"}[cls]
    third = {"sans": "mono", "serif": "mono", "mono": "serif"}[cls]

    def shuf(xs):
        xs = list(xs)
        rng.shuffle(xs)
        return xs
    return {"same_class": shuf(f for f in FAMILIES_BY_CLASS[cls] if f != base),
            "cross_class": shuf(FAMILIES_BY_CLASS[other]),
            "third_class": shuf(FAMILIES_BY_CLASS[third]) + shuf(FAMILIES_BY_CLASS[other])}


def supersample_for(block) -> int:
    return 8 if block.size < 13 else 4


def substitution_plan(block, rng: random.Random) -> list:
    """Deterministic order of characters to replace with look-alikes (confusable characters first)."""
    pos = [(j, k, ci) for j, line in enumerate(block.lines) for k, r in enumerate(line)
           for ci, ch in enumerate(r.text) if ch.isalnum()]
    rng.shuffle(pos)
    pos.sort(key=lambda p: block.lines[p[0]][p[1]].text[p[2]] not in CONFUSABLE)
    plan = []
    for j, k, ci in pos[:max(LADDERS["char_substitution"])]:
        ch = block.lines[j][k].text[ci]
        new = CONFUSABLE.get(ch) or (("o" if ch != "o" else "a") if ch.islower() else ("0" if ch.isdigit() and ch != "0"
                                                                                   else ("8" if ch.isdigit() else "O")))
        plan.append((j, k, ci, new[0]))
    return plan


def to_local(bi: int, knob: str, value, ctx: dict) -> dict:
    """The control (and the ladder Original) also go through the supersampled path, so the only
    difference between a release and its Original is the knob itself. ctx: fams, ss, subs, object, anchor."""
    loc = {"block": bi, "supersample": ctx["ss"]}
    if knob == "control":
        return loc
    if knob == "font_family":
        loc["family"] = ctx["fams"][value]
        loc["bold"] = value == "cross_class_bold"
    elif knob == "font_size":
        loc["size_mult"] = float(value)
    elif knob == "font_color":
        loc["color_delta"] = int(value)
    elif knob == "inpaint_color_mismatch":
        loc["bg_delta"] = int(value)
    elif knob == "justification":
        loc["dx"] = float(value)
    elif knob == "line_spacing":
        loc["pitch_px"] = float(value)
    elif knob == "char_substitution":
        subs = {}
        for j, k, ci, new in ctx["subs"][:int(value)]:
            subs.setdefault((j, k), {})[ci] = new
        loc["ocr_subs"] = subs
    elif knob == "ghost_residue":
        loc["ghost_alpha"] = float(value)
    elif knob == "texture_smoothing":
        loc["tex_loss"] = float(value)
    elif knob == "lighting_drop":
        loc["light_drop"] = float(value)
    elif knob == "local_compression":
        loc["jpeg_q"] = int(value)
    elif knob == "object_shift":
        loc["object"], loc["obj_dx"] = ctx["object"], float(value)
    elif knob == "heading_shift":
        loc["anchor"], loc["anchor_dx"] = ctx["anchor"], float(value)
    return loc


# ------------------------------------------------------------------ target selection
def _bbox(lines, pad=3):
    return (min(l["x"] for l in lines) - pad, min(l["y"] for l in lines) - pad,
            max(l["x"] + l["w"] for l in lines) + pad, max(l["y"] + l["h"] for l in lines) + pad)


def _hit(a, b, m=2):
    return a[0] < b[2] + m and b[0] < a[2] + m and a[1] < b[3] + m and b[1] < a[3] + m


def _obstacles(doc, orig):
    obs = [("block", i, _bbox(l, 1)) for i, l in enumerate(orig) if l]
    obs += [("object", i, (o.x, o.y, o.x + o.w, o.y + o.h)) for i, o in enumerate(doc.objects)]
    obs += [("rule", i, (min(r.x1, r.x2) - r.width, min(r.y1, r.y2) - r.width,
                         max(r.x1, r.x2) + r.width, max(r.y1, r.y2) + r.width)) for i, r in enumerate(doc.rules)]
    return obs


def _panels(doc, box):
    """Background panels (chat bubbles, cards, label panels) that contain a box and must keep containing it."""
    return [(b.x, b.y, b.x + b.w, b.y + b.h) for b in doc.background.bands
            if b.x <= box[0] and b.y <= box[1] and b.x + b.w >= box[2] and b.y + b.h >= box[3]
            and (b.w < doc.width or b.h < doc.height)]


def _conflicts(doc, own, box, moved, obstacles):
    """New collisions of `moved` (the edited version of `box`): page edge, its panels, other elements."""
    ignore = {(k, j) for k, j, bb in obstacles if (k, j) == own or _hit(box, bb, 0)}
    c = int(moved[0] < 2 or moved[1] < 2 or moved[2] > doc.width - 2 or moved[3] > doc.height - 2)
    c += sum(1 for p in _panels(doc, box) if moved[0] < p[0] or moved[1] < p[1] or moved[2] > p[2] or moved[3] > p[3])
    return c + sum(1 for k, j, bb in obstacles if (k, j) not in ignore and _hit(moved, bb))


def _pick_shift_target(doc, kind, candidates, boxes, obstacles):
    """First object / heading that can move SHIFT_MAX px to the right without touching anything new."""
    for i in candidates:
        bx = boxes[i]
        moved = (bx[0], bx[1], bx[2] + SHIFT_MAX, bx[3])
        if _conflicts(doc, (kind, i), bx, moved, obstacles) == 0:
            return i
    return None


def choose_targets(doc, rng: random.Random, knobs):
    """Pick the multi-line body/small block whose edited versions stay on the page, inside their panel and
    clear of every text block, object and rule they did not already touch; font-family levels try their
    candidate typefaces in order. Also picks the object (object_shift) and heading (heading_shift).
    Returns (ctx, n_conflicts) or None if the document has no multi-line candidate block."""
    orig = layout(doc)
    obstacles = _obstacles(doc, orig)
    cands = [i for i, b in enumerate(doc.blocks) if b.role in CANDIDATE_ROLES and len(b.lines) >= 2 and orig[i]]
    cands.sort(key=lambda i: (-len(doc.blocks[i].lines), -doc.blocks[i].w, i))
    obj_order = sorted(range(len(doc.objects)), key=lambda i: (-doc.objects[i].w * doc.objects[i].h, i))
    obj_boxes = {i: (o.x, o.y, o.x + o.w, o.y + o.h) for i, o in enumerate(doc.objects)}
    head_order = [i for i, b in enumerate(doc.blocks) if b.role in ("title", "heading") and orig[i]]
    head_boxes = {i: _bbox(orig[i]) for i in head_order}
    best = None
    for bi in cands:
        ss = supersample_for(doc.blocks[bi])
        ob = _bbox(orig[bi])
        ctx = {"block": bi, "ss": ss, "fams": {}, "subs": substitution_plan(doc.blocks[bi], random.Random(rng.random())),
               "object": None, "anchor": None}

        def conf(loc):
            return _conflicts(doc, ("block", bi), ob, _bbox(layout(doc, None, loc)[bi]), obstacles)

        layout_knobs = [k for k in knobs if k in ("font_size", "justification", "line_spacing", "char_substitution")]
        conflicts = sum(conf(to_local(bi, k, v, ctx)) for k, _, v in settings(layout_knobs)[1:])
        if "font_family" in knobs:
            opts = family_options(doc.blocks[bi].family, random.Random(rng.random()))
            for label in ("same_class", "cross_class", "third_class"):
                tried = []
                for f in opts[label]:
                    if label == "third_class" and f == ctx["fams"]["cross_class"]:
                        continue
                    c = conf({"block": bi, "supersample": ss, "family": f})
                    if label == "cross_class":
                        c += conf({"block": bi, "supersample": ss, "family": f, "bold": True})
                    tried.append((c, f))
                    if c == 0:
                        break
                c, f = min(tried)
                ctx["fams"][label] = f
                conflicts += c
            ctx["fams"]["cross_class_bold"] = ctx["fams"]["cross_class"]
        if "object_shift" in knobs:
            ctx["object"] = _pick_shift_target(doc, "object", obj_order, obj_boxes, obstacles)
        if "heading_shift" in knobs:
            ctx["anchor"] = _pick_shift_target(doc, "block", head_order, head_boxes, obstacles)
        if conflicts == 0:
            return ctx, 0
        if best is None or conflicts < best[1]:
            best = (ctx, conflicts)
    return best


# ------------------------------------------------------------------ calculations (for checking by hand)
def score_calculation(loc: dict, realised: dict, scores: dict, emph_total: int) -> dict:
    """Per metric: the formula with the measured numbers filled in. score = round(1 - severity, 2)."""
    P = PHYS
    f = {
        "font_similarity": (f"0.6*|{loc['size_mult']} - 1|/0.35 + 0.4*{loc['family_term']} (typeface) + "
                            f"0.2*{int(loc['weight_changed'])} (bold) + 0.6*min(1, dE2000 {loc['text_delta_e2000']}/25)"),
        "alignment_preservation": f"{loc['dx_px']} px / hypot({P['align_max_dx']}, {P['align_max_dy']})",
        "reading_flow": f"({loc['pitch_px']} px extra / line pitch, = {loc['pitch_rel']}) / {P['flow_max_spacing']}",
        "background_fidelity": f"dE2000 {loc['bg_delta_e2000']} / {P['bg_max_delta_e']}",
        "semantic_emphasis": f"{loc['emph_bold_spans_lost']} bold phrases no longer distinct / {emph_total} emphasised phrases",
        "ocr_accuracy": (f"({loc['chars_substituted']} substituted / {loc['block_alnum_chars']} characters in block "
                         f"= CER {loc['block_cer']}) / {P['ocr_max_cer']}"),
        "ghost_text_residue": f"ghost opacity {loc['ghost_alpha']} / {P['ghost_max_alpha']}",
        "texture_continuity": (f"measured grain loss 1 - std(detail after)/std(detail before) = {loc['tex_loss']} "
                               f"(blur sigma {loc['tex_sigma']})"),
        "lighting_consistency": f"brightness drop {loc['light_drop']} / {P['light_max_drop']}",
        "authenticity": f"({P['auth_jpeg_q_max']} - JPEG q{loc['jpeg_q']}) / ({P['auth_jpeg_q_max']} - {P['auth_jpeg_q_min']})",
        "object_preservation": f"{loc['obj_dx_px']} px object shift / {P['obj_max_shift']}",
        "visual_anchor_integrity": f"{loc['anchor_dx_px']} px heading shift / {P['anchor_max_shift']}",
    }
    return {k: {"formula": f[k], "severity": round(realised[k], 4), "score": scores[k],
                "rule": "score = round(1 - min(1, severity), 2)"} for k in METRIC_KEYS}


# ------------------------------------------------------------------ one ladder sample
def make_ladder_sample(cfg: dict, i: int) -> dict:
    lc = cfg["ladder"]
    knobs = active_knobs(cfg)
    seed = cfg["project_seed"]
    templates = lc.get("templates") or cfg["dataset"]["templates"]
    sid = f"ladder_{i:04d}"
    choice, doc, doc_seed, template = None, None, None, None
    # a template first retries with new document seeds; a template that never has a usable multi-line
    # body block falls through to the next template
    for k in range(len(templates) * 6):
        template = templates[(i + k // 6) % len(templates)]
        doc_seed = seed * 100003 + 500000 + i * 997 + k
        doc = build_document(template, doc_seed)
        choice = choose_targets(doc, random.Random(doc_seed), knobs)
        ok = choice is not None and choice[1] <= lc.get("max_conflicts", 0)
        if ok and ("object_shift" in knobs and choice[0]["object"] is None
                   or "heading_shift" in knobs and choice[0]["anchor"] is None) and k % 6 != 5:
            ok = False  # prefer a document where every knob has a target; accept the 6th try regardless
        if ok:
            break
    if choice is None:
        raise RuntimeError(f"{sid}: no template produced a usable target block")
    ctx, conflicts = choice
    skipped = [k for k, t in (("object_shift", "object"), ("heading_shift", "anchor")) if k in knobs and ctx[t] is None]
    bi = ctx["block"]
    blk = doc.blocks[bi]

    out_dir = os.path.join(cfg["_root"], cfg["paths"]["images_dir"], sid)
    os.makedirs(out_dir, exist_ok=True)
    rel_dir = f"{cfg['paths']['images_dir']}/{sid}"
    ctrl = to_local(bi, "control", None, ctx)
    orig, oinfo = render(doc, None, seed=doc_seed, local=ctrl)
    regions = []
    for j, (b, lines) in enumerate(zip(doc.blocks, layout(doc, None, ctrl))):
        if lines:
            x0, y0, x1, y1 = _bbox(lines, 0)
            text = " ".join(l["text"] for l in lines)
            regions.append({"region_id": f"b{j:02d}", "bbox": [int(math.floor(x0)), int(math.floor(y0)),
                                                              int(math.ceil(x1)), int(math.ceil(y1))],
                            "role": b.role, "text_en": text, "text_translated": text})
    orig.save(os.path.join(out_dir, "original.png"))
    o_arr = np.asarray(orig).astype(np.int16)
    w = cfg["scoring"]["category_weights"]

    releases = []
    for knob, level, val in settings([k for k in knobs if k not in skipped]):
        rid = f"{knob}_{level}"
        loc = to_local(bi, knob, val, ctx)
        img, info = render(doc, None, seed=doc_seed, local=loc)
        img.save(os.path.join(out_dir, f"{rid}.png"))
        scores = scores_from_severity(info["realised_severity"])
        rel_arr = np.asarray(img).astype(np.int16)
        delta = np.abs(rel_arr - o_arr).max(axis=2)
        changed = delta > 0
        loc_info = info["details"]["local"]
        x0, y0, x1, y1 = loc_info["region_bbox"]
        x0, y0 = max(0, x0 // JPEG_BLOCK * JPEG_BLOCK - JPEG_BLOCK), max(0, y0 // JPEG_BLOCK * JPEG_BLOCK - JPEG_BLOCK)
        x1 = min(doc.width, x1 // JPEG_BLOCK * JPEG_BLOCK + 2 * JPEG_BLOCK)
        y1 = min(doc.height, y1 // JPEG_BLOCK * JPEG_BLOCK + 2 * JPEG_BLOCK)
        if knob != "control":
            inside = np.zeros_like(changed)
            inside[y0:y1, x0:x1] = True
            outside = int((changed & ~inside).sum())
        else:
            outside = int(changed.sum())
        ys, xs = np.nonzero(changed)
        audit = {"changed_pixels": int(changed.sum()), "max_channel_delta": int(delta.max()),
                 "changed_bbox": [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1] if len(xs) else None,
                 "changed_pixels_outside_region": outside, "no_visible_change": not bool(changed.any())}
        releases.append({
            "release_id": rid,
            "artifact_type": knob,
            "level": level,
            "artifact_value": val,
            "nominal_level": knob == "font_family",
            "primary_metric": KNOB_METRIC.get(knob),
            "release_image_path": f"{rel_dir}/{rid}.png",
            "scores": scores,
            "category_scores": category_scores(scores, w),
            "ground_truth_source": "measured",
            "score_calculation": score_calculation(loc_info, info["realised_severity"], scores,
                                                   info["details"]["emph_total"]),
            "pixel_measurements": compare(o_arr[y0:y1, x0:x1].astype(np.uint8), rel_arr[y0:y1, x0:x1].astype(np.uint8),
                                          offset=(x0, y0)),
            "control_parameters": info["details"],
            "reasoning": build_reasoning(info["realised_severity"], info["details"]),
            "ocr_data_release": info["ocr_boxes_release"],
            "render_audit": audit,
        })
    return {
        "sample_id": sid,
        "kind": "ladder",
        "template": template,
        "language": cfg["dataset"]["language"],
        "doc_seed": doc_seed,
        "image_size": [doc.width, doc.height],
        "original_image_path": f"{rel_dir}/original.png",
        "ocr_data": oinfo["ocr_boxes_original"],
        "ocr_regions": regions,
        "n_objects": len(doc.objects),
        "knobs": [k for k in knobs if k not in skipped],
        "skipped_knobs": skipped,
        "target_block": {"index": bi, "region_id": f"b{bi:02d}", "id": blk.id, "role": blk.role, "n_lines": len(blk.lines),
                         "family": blk.family, "size": blk.size, "supersample": ctx["ss"],
                         "text": " / ".join(line_text(l) for l in blk.lines), "families_used": ctx["fams"],
                         "layout_conflicts": conflicts,
                         "object": None if ctx["object"] is None else {"index": ctx["object"], "kind": doc.objects[ctx["object"]].kind},
                         "heading": None if ctx["anchor"] is None else {"index": ctx["anchor"], "region_id": f"b{ctx['anchor']:02d}",
                                                                        "id": doc.blocks[ctx["anchor"]].id}},
        "releases": releases,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def ladder_summary(records: list) -> dict:
    """Per knob x level: mean measured primary-metric score, audit counts, and monotonicity."""
    out = {"n_samples": len(records), "n_pairs": sum(len(r["releases"]) for r in records), "per_setting": {},
           "monotonic_share": {}, "templates": {}, "skipped_knobs": {}}
    for r in records:
        out["templates"][r["template"]] = out["templates"].get(r["template"], 0) + 1
        for k in r.get("skipped_knobs", []):
            out["skipped_knobs"][k] = out["skipped_knobs"].get(k, 0) + 1
    present = [k for k in KNOBS if any(k in r.get("knobs", BASE_KNOBS) for r in records)]
    for knob, level, val in settings(present):
        rid = f"{knob}_{level}"
        rels = [x for r in records for x in r["releases"] if x["release_id"] == rid]
        if not rels:
            continue
        m = KNOB_METRIC.get(knob)
        out["per_setting"][rid] = {
            "value": val, "primary_metric": m, "n": len(rels),
            "mean_primary_score": round(float(np.mean([x["scores"][m] for x in rels])), 4) if m else None,
            "mean_overall": round(float(np.mean([x["category_scores"]["overall"] for x in rels])), 4),
            "n_no_visible_change": sum(x["render_audit"]["no_visible_change"] for x in rels),
            "max_changed_pixels_outside_region": max(x["render_audit"]["changed_pixels_outside_region"] for x in rels),
        }
    for knob in [k for k in ORDINAL_KNOBS if k in present]:
        m = KNOB_METRIC[knob]
        ok = []
        for r in records:
            s = [x["scores"][m] for x in r["releases"] if x["artifact_type"] == knob]
            if s:
                ok.append(all(a >= b for a, b in zip(s, s[1:])))
        out["monotonic_share"][knob] = round(float(np.mean(ok)), 4) if ok else None
    return out


# ------------------------------------------------------------------ export in the metadata_real.json schema
# (prism_iqa "Minute Change Lab" format: one record per release image, 12 canonical metric keys)
REAL_METRIC_KEYS = {"reading_flow": "reading_flow_preservation", "semantic_emphasis": "semantic_emphasis_preservation",
                    "authenticity": "authenticity_score"}


def value_string(rel: dict) -> str:
    """artifact_value as the string the reference metadata uses (font name, size factor, RGB tuple, ...)."""
    k, v, loc = rel["artifact_type"], rel["artifact_value"], rel["control_parameters"]["local"]
    if k == "font_family":
        return loc["family_to"] + (" Bold" if v == "cross_class_bold" else "")
    if k == "font_size":
        return str(v)
    if k == "font_color":
        return str(tuple(loc["text_color_to"]))
    if k == "inpaint_color_mismatch":
        o = loc["bg_offset"]
        return str((o, o, o))
    if k == "justification":
        return f"right+{v}px"
    if k == "line_spacing":
        return f"+{v}px"
    if k == "char_substitution":
        return f"{v} chars"
    if k in ("ghost_residue", "texture_smoothing", "lighting_drop"):
        return f"{v * 100:g}%"
    if k == "local_compression":
        return f"q{v}"
    return f"right+{v}px ({loc['object_kind'] or loc['anchor_block']})"  # object_shift / heading_shift


def to_metadata_real(records: list, include_control: bool = False) -> list:
    """Ladder samples -> list of pair records with the keys (and key order) of metadata_real.json first.
    metric_scores holds the MEASURED ground truth instead of nulls; English-only, so the localized baseline
    is the Original itself and text_translated == text_en. Two trailing keys are added for checking:
    score_calculation (formula + numbers per metric) and pixel_measurements (image-only evidence)."""
    out = []
    for r in records:
        for rel in r["releases"]:
            if rel["artifact_type"] == "control" and not include_control:
                continue
            control = rel["artifact_type"] == "control"
            region = r["target_block"]["region_id"]
            if rel["artifact_type"] == "heading_shift":
                region = r["target_block"]["heading"]["region_id"]
            elif rel["artifact_type"] == "object_shift":
                region = f"object_{r['target_block']['object']['index']:02d}"
            out.append({
                "pair_id": f"{r['sample_id']}_{rel['artifact_type']}_{rel['level']:02d}",
                "source_sample_id": r["sample_id"],
                "artifact_type": rel["artifact_type"],
                "artifact_region": region,
                "artifact_value": None if control else value_string(rel),
                "target_lang": r["language"],
                "original_image_path": r["original_image_path"],
                "baseline_localized_path": r["original_image_path"],
                "translated_image_path": rel["release_image_path"],
                "ocr_data": r["ocr_regions"],
                "metric_scores": {REAL_METRIC_KEYS.get(k, k): rel["scores"][k] for k in METRIC_KEYS},
                "score_calculation": {REAL_METRIC_KEYS.get(k, k): v for k, v in rel["score_calculation"].items()},
                "pixel_measurements": rel["pixel_measurements"],
            })
    return out
