"""Agreement analytics + diagnostic audit.

Accuracy measures reported (per metric, per category, overall, per template):
  MAE, RMSE, PLCC (Pearson), SROCC (Spearman), bias (mean signed error),
  tolerance accuracy (|error| <= 0.05 / 0.10 / 0.15),
  quality-band accuracy + macro-F1 (excellent >= .90 / good .75-.90 / fair .50-.75 / poor < .50),
Ranking measures: best-release accuracy (RSA), exact-ranking accuracy, mean Kendall tau,
                  pairwise preference accuracy per metric.
Coverage: valid-output (parse) rate after the validation gate.
"""

from __future__ import annotations

import itertools
import math
from collections import defaultdict

import numpy as np
from scipy.stats import kendalltau, pearsonr, spearmanr

from .metrics import CATEGORIES, METRIC_KEYS, METRIC_CATEGORY, QUALITY_BANDS, band_of
from .scoring import category_scores, rank_releases

TOLS = (0.05, 0.10, 0.15)


def _safe_corr(fn, a, b):
    if len(a) < 3 or np.std(a) < 1e-9 or np.std(b) < 1e-9:
        return float("nan")
    return float(fn(a, b)[0])


def regression_metrics(gt, pred) -> dict:
    gt, pred = np.asarray(gt, float), np.asarray(pred, float)
    if len(gt) == 0:
        return {"n": 0}
    err = pred - gt
    out = {
        "n": int(len(gt)),
        "MAE": float(np.mean(np.abs(err))),
        "RMSE": float(math.sqrt(np.mean(err ** 2))),
        "PLCC": _safe_corr(pearsonr, gt, pred),
        "SROCC": _safe_corr(spearmanr, gt, pred),
        "bias": float(np.mean(err)),
    }
    for t in TOLS:
        out[f"acc@{t:.2f}"] = float(np.mean(np.abs(err) <= t + 1e-9))
    gb, pb = [band_of(x) for x in gt], [band_of(x) for x in pred]
    out["band_acc"] = float(np.mean([a == b for a, b in zip(gb, pb)]))
    f1s = []
    for name, _, _ in QUALITY_BANDS:
        tp = sum(a == name and b == name for a, b in zip(gb, pb))
        fp = sum(a != name and b == name for a, b in zip(gb, pb))
        fn = sum(a == name and b != name for a, b in zip(gb, pb))
        if tp + fp + fn:
            f1s.append(2 * tp / (2 * tp + fp + fn))
    out["band_macro_F1"] = float(np.mean(f1s)) if f1s else float("nan")
    return out


def evaluate(records: list, category_weights=None, top_error_threshold=0.30) -> dict:
    """records: [{sample_id, release_id, template, gt: {12}, pred: {12} | None, raw?}]"""
    n_all = len(records)
    valid = [r for r in records if r.get("pred")]
    res = {"coverage": {"n_total": n_all, "n_valid": len(valid),
                        "valid_rate": len(valid) / n_all if n_all else float("nan"),
                        "n_retried": sum(1 for r in records if r.get("retried")),
                        "n_invalid": n_all - len(valid)}}

    res["per_metric"] = {k: regression_metrics([r["gt"][k] for r in valid], [r["pred"][k] for r in valid])
                         for k in METRIC_KEYS}
    gcat = [category_scores(r["gt"], category_weights) for r in valid]
    pcat = [category_scores(r["pred"], category_weights) for r in valid]
    res["per_category"] = {c: regression_metrics([g[c] for g in gcat], [p[c] for p in pcat])
                           for c in CATEGORIES + ["overall"]}
    res["all_metrics_pooled"] = regression_metrics([r["gt"][k] for r in valid for k in METRIC_KEYS],
                                                    [r["pred"][k] for r in valid for k in METRIC_KEYS])
    by_t = defaultdict(list)
    for r, g, p in zip(valid, gcat, pcat):
        by_t[r["template"]].append((g["overall"], p["overall"]))
    res["per_template_overall"] = {t: regression_metrics([a for a, _ in v], [b for _, b in v]) for t, v in sorted(by_t.items())}

    # ---------------- ranking / best-release
    by_s = defaultdict(dict)
    for r in valid:
        by_s[r["sample_id"]][r["release_id"]] = r
    best_hits, exact_hits, taus, rows = [], [], [], []
    pair_hits = {k: [] for k in METRIC_KEYS + ["overall"]}
    for sid, rels in sorted(by_s.items()):
        if len(rels) < 2:
            continue
        g_rank, g_cat = rank_releases({k: v["gt"] for k, v in rels.items()}, category_weights)
        p_rank, p_cat = rank_releases({k: v["pred"] for k, v in rels.items()}, category_weights)
        best_hits.append(g_rank[0] == p_rank[0])
        exact_hits.append(g_rank == p_rank)
        if len(rels) >= 3:
            ids = sorted(rels)
            t = kendalltau([g_cat[i]["overall"] for i in ids], [p_cat[i]["overall"] for i in ids])[0]
            if not np.isnan(t):
                taus.append(t)
        for a, b in itertools.combinations(sorted(rels), 2):
            for k in METRIC_KEYS:
                dg = rels[a]["gt"][k] - rels[b]["gt"][k]
                if abs(dg) > 0.05:
                    pair_hits[k].append(np.sign(dg) == np.sign(rels[a]["pred"][k] - rels[b]["pred"][k]))
            dg = g_cat[a]["overall"] - g_cat[b]["overall"]
            if abs(dg) > 0.02:
                pair_hits["overall"].append(np.sign(dg) == np.sign(p_cat[a]["overall"] - p_cat[b]["overall"]))
        rows.append({"sample_id": sid, "gt_ranking": ">".join(g_rank), "pred_ranking": ">".join(p_rank),
                     "gt_best": g_rank[0], "pred_best": p_rank[0], "best_correct": g_rank[0] == p_rank[0],
                     **{f"gt_overall_{i}": g_cat[i]["overall"] for i in sorted(rels)},
                     **{f"pred_overall_{i}": p_cat[i]["overall"] for i in sorted(rels)}})
    res["ranking"] = {
        "n_samples": len(best_hits),
        "best_release_accuracy_RSA": float(np.mean(best_hits)) if best_hits else float("nan"),
        "exact_ranking_accuracy": float(np.mean(exact_hits)) if exact_hits else float("nan"),
        "mean_kendall_tau": float(np.mean(taus)) if taus else float("nan"),
        "pairwise_preference_accuracy": {k: (float(np.mean(v)) if v else float("nan")) for k, v in pair_hits.items()},
    }
    res["ranking_rows"] = rows

    # ---------------- diagnostic audit
    err_rows = []
    for r in valid:
        for k in METRIC_KEYS:
            e = r["pred"][k] - r["gt"][k]
            err_rows.append({"sample_id": r["sample_id"], "release_id": r["release_id"], "template": r["template"],
                             "metric": k, "category": METRIC_CATEGORY[k], "gt": r["gt"][k], "pred": r["pred"][k],
                             "error": round(e, 4), "abs_error": round(abs(e), 4)})
    top = sorted([e for e in err_rows if e["abs_error"] > top_error_threshold], key=lambda e: -e["abs_error"])
    res["top_errors"] = top
    buckets = {"untouched (gt>=0.98)": (0.98, 1.01), "minute (0.90-0.98)": (0.90, 0.98),
               "moderate (0.60-0.90)": (0.60, 0.90), "strong (<0.60)": (-0.01, 0.60)}
    sev_table = {}
    for k in METRIC_KEYS:
        sev_table[k] = {}
        for bname, (lo, hi) in buckets.items():
            es = [e["abs_error"] for e in err_rows if e["metric"] == k and lo <= e["gt"] < hi]
            sev_table[k][bname] = {"n": len(es), "MAE": float(np.mean(es)) if es else float("nan")}
    res["error_by_severity"] = sev_table
    pattern = defaultdict(lambda: {"n": 0, "over": 0, "under": 0})
    for e in top:
        p = pattern[(e["metric"], e["template"])]
        p["n"] += 1
        p["over" if e["error"] > 0 else "under"] += 1
    res["failure_patterns"] = sorted(
        [{"metric": m, "template": t, **v, "direction": "over-scores (misses defect)" if v["over"] >= v["under"]
          else "under-scores (hallucinates defect)"} for (m, t), v in pattern.items()], key=lambda x: -x["n"])
    res["error_rows"] = err_rows
    return res


def human_ceiling(human_rows: list, gt_lookup: dict) -> dict:
    """Optional: human pilot annotations of predefined-score images.
    human_rows: [{sample_id, release_id, annotator, <12 metric keys>}]
    Returns per-metric human sigma, leave-one-out human error vs consensus, and human-vs-predefined MAE."""
    items = defaultdict(list)
    for h in human_rows:
        items[(h["sample_id"], h["release_id"])].append(h)
    out = {}
    for k in METRIC_KEYS:
        sigmas, loo, vs_pre = [], [], []
        for key, anns in items.items():
            vals = [float(a[k]) for a in anns if a.get(k) not in (None, "")]
            if not vals:
                continue
            if len(vals) >= 2:
                sigmas.append(float(np.std(vals)))
                for i in range(len(vals)):
                    loo.append(abs(vals[i] - np.mean(vals[:i] + vals[i + 1:])))
            if key in gt_lookup:
                vs_pre.append(abs(np.mean(vals) - gt_lookup[key][k]))
        out[k] = {"mean_sigma": float(np.mean(sigmas)) if sigmas else float("nan"),
                  "human_ceiling_error": float(np.mean(loo)) if loo else float("nan"),
                  "human_vs_predefined_MAE": float(np.mean(vs_pre)) if vs_pre else float("nan"),
                  "n_items": len(items)}
    return out
