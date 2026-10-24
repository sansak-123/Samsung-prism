"""Turn the model's 12 scores + analysis into an actionable verdict for ANY original/edited image pair.

Domain-agnostic: the same verdict works for translated images, generative / inpainting edits, OCR
re-typesetting, UI screenshots across builds or languages, scanned and re-printed forms, and tamper
screening. The VLM only scores; all decisions here are deterministic Python (like prism/scoring.py).
"""

from __future__ import annotations

from .metrics import METRIC_KEYS, METRIC_NAMES
from .scoring import category_scores

# what an automatic repair step (or a human editor) should do when a metric fails
FIXES = {
    "ocr_accuracy": "re-typeset the text from the verified transcription (wrong / look-alike characters)",
    "alignment_preservation": "restore the block's original x/y position and margins",
    "font_similarity": "re-render with the original typeface, weight, size and ink colour",
    "object_preservation": "re-composite the logo / QR / stamp / photo at its original position, size and opacity",
    "background_fidelity": "re-fill the edited patch with the surrounding background colour",
    "texture_continuity": "re-synthesise paper grain / pattern inside the edited patch",
    "ghost_text_residue": "erase the remaining traces of the old glyphs before re-rendering",
    "lighting_consistency": "match the patch brightness / shading to its surroundings",
    "reading_flow": "restore the original line spacing and baselines",
    "visual_anchor_integrity": "restore headings, rules and borders to their original size and position",
    "semantic_emphasis": "re-apply bold / colour emphasis to the emphasised phrases",
    "authenticity": "re-export the edited area losslessly (compression / noise artifacts)",
}


def analysis_lines(raw: str | None) -> dict:
    """metric -> the model's own observation line (the P4 output has one line per metric, in order)."""
    if not raw or "<analysis>" not in raw:
        return {}
    body = raw.split("<analysis>", 1)[1].split("</analysis>", 1)[0]
    lines = [l.strip().lstrip("- ").strip() for l in body.splitlines() if l.strip().startswith("-")]
    return dict(zip(METRIC_KEYS, lines)) if len(lines) == len(METRIC_KEYS) else {}


def verdict(scores: dict | None, raw: str | None = None, threshold: float = 0.95, category_weights=None) -> dict:
    if not scores:
        return {"decision": "UNSCORED", "reason": "model output failed the validation gate", "flags": []}
    cats = category_scores(scores, category_weights)
    why = analysis_lines(raw)
    flags = sorted(({"metric": k, "name": METRIC_NAMES[k], "score": scores[k], "observation": why.get(k),
                     "fix": FIXES[k]} for k in METRIC_KEYS if scores[k] < threshold), key=lambda f: f["score"])
    return {"decision": "REJECT" if flags else "ACCEPT", "threshold": threshold, "overall": cats["overall"],
            "categories": {c: v for c, v in cats.items() if c != "overall"}, "scores": scores, "flags": flags}
