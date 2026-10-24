"""Image-only evidence of what changed between an Original crop and a release crop.

Port of `compare()` from github.com/Sanjana432/prism_iqa (prism/vision.py, "pixel-evidence-v1"), same 12
measurements. It looks at pixels only - never at the generator's parameters - so it is an independent
cross-check of the measured ground truth (see scripts/check_ladder_scores.py).

Ink detection assumes dark text on a lighter background (ink = pixels > 40 grey levels darker than the
85th-percentile background); on dark-mode crops the ink-based fields can be None or meaningless.
"""

from __future__ import annotations

import numpy as np


def _rows(mask):
    projection = mask.sum(axis=1)
    active = projection > max(2, float(projection.max()) * .08) if projection.size else projection
    edges = np.diff(np.r_[False, active, False].astype(int))
    starts, ends = np.where(edges == 1)[0], np.where(edges == -1)[0]
    bands = []  # rejoin dots/accents separated from the letter body by a few raster rows
    for s, e in zip(starts, ends):
        if bands and s - bands[-1][1] <= 3:
            bands[-1][1] = e
        else:
            bands.append([s, e])
    bands = [b for b in bands if b[1] - b[0] >= 3]
    return np.array([b[0] for b in bands], dtype=int), np.array([b[1] for b in bands], dtype=int)


def _median(v):
    return float(np.median(v)) if len(v) else None


def compare(reference: np.ndarray, candidate: np.ndarray, offset=(0, 0), tolerance: int = 0) -> dict:
    """reference / candidate: HxWx3 uint8 crops of identical size. offset = crop origin in the page
    (only used to report change_bbox in page coordinates)."""
    if reference.shape != candidate.shape:
        raise ValueError("crops must have identical size; resizing would erase minute changes")
    x, y = reference.astype(float), candidate.astype(float)
    gx, gy = x.mean(2), y.mean(2)
    mx, my = gx < np.percentile(gx, 85) - 40, gy < np.percentile(gy, 85) - 40
    delta = np.abs(x - y)
    changed = delta.max(2) > tolerance
    sy, ey = _rows(mx)
    st, et = _rows(my)
    hx, hy = _median(ey - sy), _median(et - st)
    px, py = _median(np.diff(sy)), _median(np.diff(st))
    bg = (~mx) & (~my)
    inkx = np.percentile(x[mx], 5, axis=0) if mx.any() else np.zeros(3)  # deep ink avoids anti-aliasing
    inky = np.percentile(y[my], 5, axis=0) if my.any() else np.zeros(3)
    leftx = [np.where(mx[s:e].any(0))[0][0] for s, e in zip(sy, ey) if mx[s:e].any()]
    lefty = [np.where(my[s:e].any(0))[0][0] for s, e in zip(st, et) if my[s:e].any()]
    left = _median(np.array(lefty) - np.array(leftx)) if len(leftx) == len(lefty) and leftx else None
    inter, union = (mx & my).sum(), (mx | my).sum()
    coords = np.argwhere(changed)
    extent = ([int(coords[:, 1].min()) + offset[0], int(coords[:, 0].min()) + offset[1],
               int(coords[:, 1].max() + 1) + offset[0], int(coords[:, 0].max() + 1) + offset[1]] if len(coords) else None)
    return {
        "changed_pixel_fraction": round(float(changed.mean()), 6),
        "mean_absolute_channel_error": round(float(delta.mean()), 4),
        "max_channel_delta": float(delta.max()),
        "ink_iou": round(float(inter / union), 4) if union else 1.0,
        "font_height_delta_px": (hy - hx) if hx and hy else None,
        "line_pitch_delta_px": (py - px) if px and py else None,
        "left_alignment_delta_px": left,
        "foreground_rgb_distance": round(float(np.linalg.norm(inky - inkx)), 3),
        "background_rgb_distance": (round(float(np.linalg.norm(np.median(y[bg], axis=0) - np.median(x[bg], axis=0))), 3)
                                    if bg.any() else None),
        "reference_line_count": int(len(sy)),
        "candidate_line_count": int(len(st)),
        "change_bbox": extent,
    }
