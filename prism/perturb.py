"""Pre-defined target scores per release (Mimat's approach).

Each sample has one Original and three releases. Every release receives a random target
score for ALL 12 metrics before rendering:
  * the release's focus category (R1 technical, R2 visual, R3 human perception by default)
    gets moderate-to-strong degradation;
  * every other metric gets a *minute* change (often exactly zero) so the model must learn to
    detect very small differences;
  * a small share of releases are near-clean, and some get one extra off-focus defect,
    so the "best release" varies from sample to sample.
"""

from __future__ import annotations

import numpy as np

from .metrics import METRIC_KEYS, METRIC_CATEGORY


def sample_release_severities(profile: str, rng: np.random.Generator, cfg: dict) -> dict:
    c = cfg["sampling"]
    clean = rng.random() < c["p_clean_release"]
    sev = {}
    for k in METRIC_KEYS:
        if not clean and METRIC_CATEGORY[k] == profile:
            s = rng.beta(c["focus_beta_a"], c["focus_beta_b"])
        elif rng.random() < c["p_untouched_metric"]:
            s = 0.0
        else:
            s = rng.beta(c["minute_beta_a"], c["minute_beta_b"])
        sev[k] = s
    if not clean and rng.random() < c["p_extra_defect"]:
        off = [k for k in METRIC_KEYS if METRIC_CATEGORY[k] != profile]
        k = off[rng.integers(len(off))]
        sev[k] = max(sev[k], rng.uniform(0.25, 0.7))
    # scores are defined on a 0.01 grid
    return {k: round(float(np.clip(v, 0, 1)), 2) for k, v in sev.items()}


def isolated_severities(metric: str, level: float) -> dict:
    """All metrics at zero except one - used for the pilot showcase (5 images per artifact type)."""
    return {k: (level if k == metric else 0.0) for k in METRIC_KEYS}
