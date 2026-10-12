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

    lines = [f"- {txt} -> {s[k]:.2f}" for txt, k in zip(L, METRIC_KEYS)]
    return "\n".join(lines)


def build_target(realised: dict, details: dict) -> str:
    scores = scores_from_severity(realised)
    return ("<analysis>\n" + build_reasoning(realised, details) + "\n</analysis>\n"
            + json.dumps({k: scores[k] for k in METRIC_KEYS}))
