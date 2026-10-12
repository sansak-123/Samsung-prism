"""Deterministic Python score engine: the VLM only predicts the 12 raw scores; all arithmetic,
ranking and best-release selection happen here (identically for predictions and ground truth)."""

from __future__ import annotations

from .metrics import CATEGORIES, CATEGORY_METRICS


def category_scores(scores: dict, category_weights: dict | None = None) -> dict:
    out = {c: sum(scores[k] for k in CATEGORY_METRICS[c]) / len(CATEGORY_METRICS[c]) for c in CATEGORIES}
    w = category_weights or {c: 1.0 for c in CATEGORIES}
    out["overall"] = sum(out[c] * w[c] for c in CATEGORIES) / sum(w[c] for c in CATEGORIES)
    return {k: round(v, 4) for k, v in out.items()}


def rank_releases(release_scores: dict, category_weights: dict | None = None):
    """release_scores: {"R1": {12 scores}, ...} -> (ranking list best-first, {release: category scores})."""
    cats = {r: category_scores(s, category_weights) for r, s in release_scores.items()}
    ranking = sorted(cats, key=lambda r: (-cats[r]["overall"], -cats[r]["technical"], r))
    return ranking, cats
