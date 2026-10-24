"""Check every ladder score yourself - no generator code is re-used for the arithmetic.

For each release in data/metadata/ladder.jsonl this script
  1. recomputes all 12 severities from the stored measurements (control_parameters.local) with its own
     copy of the formulas below, and checks score == round(1 - min(1, severity), 2);
  2. cross-checks the claimed change against the image-only pixel measurements (pixel_measurements,
     computed from the PNGs): controls must be pixel-identical, every edit must change pixels, a 4/8 px
     justification must show up as a left-edge shift, extra line spacing as a larger line pitch, etc.;
  3. checks that nothing changed outside the edited region (render_audit).
Writes reports/ladder_score_check.csv (one row per release x metric with formula, recomputed and stored
values) and prints a summary. Exit code 1 if any arithmetic check fails.

Usage: python scripts/check_ladder_scores.py [--config configs/config.yaml] [--limit N]
"""

import argparse
import csv
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prism.common import P, load_config  # noqa: E402

# ---- the physical scales, written out again on purpose (see prism/metrics.py PHYS)
OCR_MAX_CER, ALIGN_MAX = 0.25, math.hypot(40.0, 12.0)
FONT_W_SIZE, FONT_MAX_SIZE, FONT_W_FAMILY, FONT_W_WEIGHT, FONT_W_COLOR, FONT_MAX_DE = 0.6, 0.35, 0.4, 0.2, 0.6, 25.0
BG_MAX_DE, GHOST_MAX, LIGHT_MAX, FLOW_MAX = 25.0, 0.45, 0.45, 0.60
JPEG_HI, JPEG_LO, OBJ_MAX_SHIFT, ANCHOR_MAX_SHIFT = 95, 20, 30.0, 25.0


def severities(loc: dict, emph_total: int) -> dict:
    font = (FONT_W_SIZE * abs(loc["size_mult"] - 1) / FONT_MAX_SIZE + FONT_W_FAMILY * loc["family_term"]
            + FONT_W_WEIGHT * float(loc["weight_changed"]) + FONT_W_COLOR * min(1.0, loc["text_delta_e2000"] / FONT_MAX_DE))
    return {
        "ocr_accuracy": loc["block_cer"] / OCR_MAX_CER,
        "alignment_preservation": loc["dx_px"] / ALIGN_MAX,
        "font_similarity": font,
        "object_preservation": loc["obj_dx_px"] / OBJ_MAX_SHIFT,
        "background_fidelity": loc["bg_delta_e2000"] / BG_MAX_DE,
        "texture_continuity": loc["tex_loss"],
        "ghost_text_residue": loc["ghost_alpha"] / GHOST_MAX,
        "lighting_consistency": loc["light_drop"] / LIGHT_MAX,
        "reading_flow": loc["pitch_rel"] / FLOW_MAX,
        "visual_anchor_integrity": loc["anchor_dx_px"] / ANCHOR_MAX_SHIFT,
        "semantic_emphasis": loc["emph_bold_spans_lost"] / emph_total if emph_total else 0.0,
        "authenticity": (JPEG_HI - loc["jpeg_q"]) / (JPEG_HI - JPEG_LO),
    }


def pixel_checks(rel: dict) -> list:
    """(name, passed) evidence checks that use only the image measurements."""
    px, k, v = rel["pixel_measurements"], rel["artifact_type"], rel["artifact_value"]
    out = []
    if k == "control":
        return [("control is pixel-identical", px["changed_pixel_fraction"] == 0)]
    out.append(("edit changes pixels", px["changed_pixel_fraction"] > 0))
    if k == "justification" and v >= 4 and px["left_alignment_delta_px"] is not None:
        out.append(("left edge moved by ~dx", abs(px["left_alignment_delta_px"] - v) <= 1.5))
    if k == "line_spacing" and v >= 4 and px["line_pitch_delta_px"] is not None:
        out.append(("line pitch grew by ~px", abs(px["line_pitch_delta_px"] - v) <= 1.5))
    # lighting_drop is left out: darkened paper crosses the evidence tool's ink threshold and merges lines
    if k in ("justification", "line_spacing", "inpaint_color_mismatch", "texture_smoothing",
             "local_compression", "ghost_residue", "font_color"):
        out.append(("line count unchanged", px["reference_line_count"] == px["candidate_line_count"]))
    if k == "font_size" and v >= 1.05 and px["font_height_delta_px"] is not None:
        out.append(("glyphs not smaller", px["font_height_delta_px"] >= -0.5))  # medians move in 0.5 px steps
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    cfg = load_config(a.config)
    path = P(cfg, "metadata_dir", "ladder.jsonl")
    if not os.path.exists(path):
        sys.exit(f"{path} not found - run scripts/01_generate_dataset.py first")
    rows, n_rel, arith_fail, outside_fail, pix, n_exact = [], 0, [], [], {}, 0
    with open(path) as f:
        for li, line in enumerate(f):
            if a.limit and li >= a.limit:
                break
            rec = json.loads(line)
            for rel in rec["releases"]:
                n_rel += 1
                loc = rel["control_parameters"]["local"]
                sev = severities(loc, rel["control_parameters"]["emph_total"])
                for m, s in sev.items():
                    # same rounding chain as generation: severity clipped to [0, 1], 4 dp, then score to 2 dp
                    expect = round(1 - round(min(1.0, max(0.0, s)), 4), 2)
                    stored = rel["scores"][m]
                    exact = expect == stored
                    ok = exact or abs(expect - stored) <= 0.0100001  # inputs are stored rounded (3-5 dp)
                    n_exact += exact
                    if not ok:
                        arith_fail.append((rel["release_image_path"], m, expect, stored))
                    rows.append({"sample_id": rec["sample_id"], "release_id": rel["release_id"], "metric": m,
                                 "formula": rel["score_calculation"][m]["formula"], "recomputed_severity": round(s, 4),
                                 "recomputed_score": expect, "stored_score": stored, "match": ok})
                if rel["render_audit"]["changed_pixels_outside_region"]:
                    outside_fail.append(rel["release_image_path"])
                for name, ok in pixel_checks(rel):
                    t = pix.setdefault(name, [0, 0])
                    t[0] += ok
                    t[1] += 1
    out = os.path.join(P(cfg, "reports_dir"), "ladder_score_check.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"releases checked: {n_rel}  |  metric scores recomputed: {len(rows)}  ->  {out}")
    print(f"arithmetic: {n_exact}/{len(rows)} scores reproduced exactly from their formulas, "
          f"{len(rows) - n_exact - len(arith_fail)} within 0.01 only because stored inputs are rounded, "
          f"{len(arith_fail)} mismatches")
    for x in arith_fail[:10]:
        print("   MISMATCH", x)
    print(f"locality: {n_rel - len(outside_fail)}/{n_rel} releases changed nothing outside the edited region")
    print("pixel evidence (image-only cross-checks):")
    for name, (ok, n) in pix.items():
        print(f"   {name:28s} {ok}/{n}")
    sys.exit(1 if arith_fail or outside_fail else 0)


if __name__ == "__main__":
    main()
