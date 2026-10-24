"""Builds the Chain-of-Thought training target: one short observation per metric, then the JSON.
The observation text is generated from the *measured* rendering parameters, so the reasoning
the model learns is always consistent with the score that follows it."""

from __future__ import annotations

import json

from .metrics import METRIC_KEYS

DIRS = {0: "right", 45: "bottom-right", 90: "bottom", 135: "bottom-left", 180: "left", 225: "top-left",
        270: "top", 315: "top-right"}


def scores_from_severity(realised: dict) -> dict:
    return {k: round(1.0 - realised[k], 2) for k in METRIC_KEYS}


def _none(sev):
    return sev < 0.015


def build_reasoning(realised: dict, d: dict) -> str:
    s = scores_from_severity(realised)
    L = []
    sv = realised

    if _none(sv["ocr_accuracy"]):
        L.append("OCR: all text matches the original")
    else:
        ex = "; ".join(f'"{a}"->"{b}"' for a, b in d["ocr_examples"][:2])
        L.append(f"OCR: about {d['ocr_cer'] * 100:.1f}% of characters differ (e.g. {ex})")

    L.append("Alignment: text blocks in original positions" if _none(sv["alignment_preservation"])
             else f"Alignment: text blocks displaced by ~{d['align_mean_shift_px']:.0f}px")

    if _none(sv["font_similarity"]):
        L.append("Font: same typeface and size")
    else:
        parts = []
        if d["font_family_term"] == 1.0:
            parts.append("typeface changed to a different style class")
        elif d["font_family_term"] == 0.5:
            parts.append("similar but different typeface")
        dm = (d["font_size_mult"] - 1) * 100
        if abs(dm) >= 0.5:
            parts.append(f"text {abs(dm):.0f}% {'larger' if dm > 0 else 'smaller'}")
        L.append("Font: " + ", ".join(parts or ["minor rendering difference"]))

    if d["n_objects"] == 0 or _none(sv["object_preservation"]):
        L.append("Objects: logos/graphics intact")
    else:
        L.append(f"Objects: graphics shrunk to {d['obj_scale'] * 100:.0f}%, moved ~{d['obj_shift_px']:.0f}px, "
                 f"opacity {d['obj_opacity'] * 100:.0f}%")

    L.append("Background: edited regions match the paper colour" if _none(sv["background_fidelity"])
             else f"Background: edited text regions show a colour shift (dE2000 ~{d['bg_delta_e2000']:.1f})")
    L.append("Texture: paper grain continuous" if _none(sv["texture_continuity"])
             else f"Texture: ~{d['tex_detail_loss'] * 100:.0f}% of paper grain smoothed inside edited regions")
    L.append("Ghost text: no residue" if _none(sv["ghost_text_residue"])
             else f"Ghost text: faint residue of old glyphs at ~{d['ghost_alpha'] * 100:.0f}% opacity")
    L.append("Lighting: uniform" if _none(sv["lighting_consistency"])
             else f"Lighting: up to {d['light_drop'] * 100:.0f}% darker toward the {DIRS.get(d['light_angle_deg'], 'edge')}")

    if _none(sv["reading_flow"]):
        L.append("Reading flow: spacing unchanged")
    else:
        dm = (d["line_spacing_mult"] - 1) * 100
        L.append(f"Reading flow: line spacing {'+' if dm >= 0 else '-'}{abs(dm):.0f}%, uneven baselines")

    L.append("Anchors: headings and rules intact" if _none(sv["visual_anchor_integrity"])
             else f"Anchors: headings {d['anchor_shrink'] * 100:.0f}% smaller and moved ~{d['anchor_shift_px']:.0f}px, rules broken/thinner")
    L.append("Emphasis: all bold/coloured phrases kept" if d["emph_lost"] == 0
             else f"Emphasis: {d['emph_lost']}/{d['emph_total']} emphasised phrases lost their styling")
    L.append("Authenticity: clean rendering" if _none(sv["authenticity"])
             else f"Authenticity: compression/noise artifacts (JPEG quality ~{d['jpeg_quality']})")

    if d.get("local"):
        _local_lines(L, sv, d["local"], d.get("emph_total", 0))
    lines = [f"- {txt} -> {s[k]:.2f}" for txt, k in zip(L, METRIC_KEYS)]
    return "\n".join(lines)


def position_phrase(bbox, width, height) -> str:
    cx, cy = (bbox[0] + bbox[2]) / 2 / width, (bbox[1] + bbox[3]) / 2 / height
    v = "top" if cy < 1 / 3 else ("middle" if cy < 2 / 3 else "bottom")
    h = "left" if cx < 0.4 else ("right" if cx > 0.6 else "centre")
    return f"{v}-{h}" if h != "centre" else v


def _local_lines(L, sv, loc, emph_total):
    """Ladder releases: one block changed. Describe the measured change and WHERE it is, even when it
    is below the usual 'no change' threshold (the point of the ladder is minute changes)."""
    where = f'the {position_phrase(loc["region_bbox"], *loc["page_size"])} block "{loc["first_words"]}"'
    idx = {k: i for i, k in enumerate(METRIC_KEYS)}
    if sv["font_similarity"] > 0:
        parts = []
        if loc["family_term"]:
            parts.append("similar but different typeface" if loc["family_term"] == 0.5 else "typeface of a different style class")
        if loc["weight_changed"]:
            parts.append("set entirely in bold")
        dm = (loc["size_mult"] - 1) * 100
        if abs(dm) > 1e-6:
            parts.append(f"text {abs(dm):.1f}% {'larger' if dm > 0 else 'smaller'}")
        if loc["text_delta_e2000"] > 0:
            parts.append(f"ink colour slightly faded (dE2000 ~{loc['text_delta_e2000']:.1f})")
        L[idx["font_similarity"]] = f"Font: in {where}, " + ", ".join(parts)
    if sv["alignment_preservation"] > 0:
        L[idx["alignment_preservation"]] = f"Alignment: {where} shifted {loc['dx_px']:.0f}px to the right"
    if sv["reading_flow"] > 0:
        L[idx["reading_flow"]] = (f"Reading flow: line spacing in {where} increased by {loc['pitch_px']:.0f}px "
                                  f"(+{loc['pitch_rel'] * 100:.0f}%)")
    if sv["background_fidelity"] > 0:
        L[idx["background_fidelity"]] = (f"Background: re-filled patch behind {where} is slightly off-colour "
                                         f"(dE2000 ~{loc['bg_delta_e2000']:.1f})")
    if sv["semantic_emphasis"] > 0:
        L[idx["semantic_emphasis"]] = (f"Emphasis: {loc['emph_bold_spans_lost']}/{emph_total} bold phrases no longer "
                                       f"stand out because {where} is all bold")
    if sv["ocr_accuracy"] > 0 and loc.get("chars_substituted"):
        n = loc["chars_substituted"]
        L[idx["ocr_accuracy"]] = (f"OCR: {n} character{'s' if n > 1 else ''} in {where} replaced by look-alikes "
                                  f"({loc['block_cer'] * 100:.1f}% of the block)")
    if sv["ghost_text_residue"] > 0 and loc.get("ghost_alpha"):
        L[idx["ghost_text_residue"]] = f"Ghost text: faint copy of the old glyphs behind {where} at ~{loc['ghost_alpha'] * 100:.0f}% opacity"
    if sv["texture_continuity"] > 0 and loc.get("tex_loss"):
        L[idx["texture_continuity"]] = f"Texture: paper grain behind {where} smoothed (~{loc['tex_loss'] * 100:.0f}% of the detail lost)"
    if sv["lighting_consistency"] > 0 and loc.get("light_drop"):
        L[idx["lighting_consistency"]] = f"Lighting: soft shadow over {where}, up to {loc['light_drop'] * 100:.0f}% darker at its centre"
    if sv["authenticity"] > 0 and loc.get("jpeg_q", 95) < 95:
        L[idx["authenticity"]] = f"Authenticity: {where} re-saved with stronger compression (JPEG quality ~{loc['jpeg_q']})"
    if sv["object_preservation"] > 0 and loc.get("obj_dx_px"):
        L[idx["object_preservation"]] = f"Objects: the {loc['object_kind']} moved {loc['obj_dx_px']:.0f}px to the right"
    if sv["visual_anchor_integrity"] > 0 and loc.get("anchor_dx_px"):
        L[idx["visual_anchor_integrity"]] = f"Anchors: heading \"{loc['anchor_text']}\" moved {loc['anchor_dx_px']:.0f}px to the right"


def build_target(realised: dict, details: dict) -> str:
    scores = scores_from_severity(realised)
    return ("<analysis>\n" + build_reasoning(realised, details) + "\n</analysis>\n"
            + json.dumps({k: scores[k] for k in METRIC_KEYS}))
