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
import re
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


def evaluate(records: list, category_weights=None, top_error_threshold=0.30, gate_threshold=0.95) -> dict:
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

    # ---------------- ranking / best-release (core R1/R2/R3 samples only; ladder has its own analysis)
    by_s = defaultdict(dict)
    for r in valid:
        if r.get("kind", "triplet") != "ladder":
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
    if any(r.get("kind") == "ladder" for r in valid):
        res["ladder"] = ladder_sensitivity(valid, category_weights)
        res["explanations"] = explanation_check(valid)
    res["quality_gate"] = quality_gate(valid, gate_threshold)
    return res


KNOB_PRIMARY = {"font_family": "font_similarity", "font_size": "font_similarity", "font_color": "font_similarity",
                "inpaint_color_mismatch": "background_fidelity", "justification": "alignment_preservation",
                "line_spacing": "reading_flow", "char_substitution": "ocr_accuracy",
                "ghost_residue": "ghost_text_residue", "texture_smoothing": "texture_continuity",
                "lighting_drop": "lighting_consistency", "local_compression": "authenticity",
                "object_shift": "object_preservation", "heading_shift": "visual_anchor_integrity"}


def quality_gate(records: list, threshold: float = 0.95) -> dict:
    """Accept / reject decision a QA pipeline would make: reject a release when any metric < threshold.
    Reports decision accuracy, rejection precision / recall, and - for correctly rejected releases - whether
    the model blames the right metric (lowest predicted metric == lowest ground-truth metric), which is what
    an automatic repair step would act on."""
    tp = fp = fn = tn = 0
    diag = []
    for r in records:
        if not r.get("pred"):
            continue
        g_rej = min(r["gt"].values()) < threshold
        p_rej = min(r["pred"].values()) < threshold
        tp += g_rej and p_rej
        fp += (not g_rej) and p_rej
        fn += g_rej and not p_rej
        tn += (not g_rej) and not p_rej
        if g_rej and p_rej:
            diag.append(min(r["pred"], key=r["pred"].get) == min(r["gt"], key=r["gt"].get))
    n = tp + fp + fn + tn
    return {"threshold": threshold, "n": n, "decision_accuracy": (tp + tn) / n if n else float("nan"),
            "reject_precision": tp / (tp + fp) if tp + fp else float("nan"),
            "reject_recall": tp / (tp + fn) if tp + fn else float("nan"),
            "false_reject_rate": fp / (fp + tn) if fp + tn else float("nan"),
            "diagnosis_accuracy": float(np.mean(diag)) if diag else float("nan"),
            "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn}}


_POS = re.compile(r"\b(top|middle|bottom)(?:-(left|right))?\b")
_NUM = re.compile(r"(-?\d+(?:\.\d+)?)\s*(px|%)")


def _metric_line(text: str, metric: str):
    """The analysis line for a metric (lines are in METRIC_KEYS order, one per metric)."""
    if not text or "<analysis>" not in text:
        return None
    body = text.split("<analysis>", 1)[1].split("</analysis>", 1)[0]
    lines = [l.strip() for l in body.splitlines() if l.strip().startswith("-")]
    return lines[METRIC_KEYS.index(metric)] if len(lines) == len(METRIC_KEYS) else None


def explanation_check(records: list) -> dict:
    """Is the model's written reason TRUE? For ladder releases, compare the model's analysis line for the
    edited metric with the ground-truth line: same location phrase (top/middle/bottom-left/right) and
    the same measured quantity (px / %) within 25 % (or 1 unit)."""
    loc_hits, num_hits, n_lines = [], [], 0
    for r in records:
        if r.get("kind") != "ladder" or r.get("artifact_type") in (None, "control") or not r.get("raw"):
            continue
        m = r["primary_metric"]
        gl, pl = _metric_line(r.get("target", ""), m), _metric_line(r["raw"], m)
        if gl is None or pl is None:
            continue
        n_lines += 1
        g_pos, p_pos = _POS.search(gl), _POS.search(pl)
        if g_pos:
            loc_hits.append(bool(p_pos) and p_pos.group(0) == g_pos.group(0))
        g_num, p_num = _NUM.findall(gl.split("->")[0]), _NUM.findall(pl.split("->")[0])
        if g_num:
            gv, gu = float(g_num[0][0]), g_num[0][1]
            same = [float(v) for v, u in p_num if u == gu]
            num_hits.append(bool(same) and abs(same[0] - gv) <= max(1.0, 0.25 * abs(gv)))
    return {"n_explanations": n_lines,
            "location_accuracy": float(np.mean(loc_hits)) if loc_hits else float("nan"), "n_location": len(loc_hits),
            "quantity_accuracy": float(np.mean(num_hits)) if num_hits else float("nan"), "n_quantity": len(num_hits)}


def ladder_sensitivity(records: list, category_weights=None, false_alarm_below=0.98) -> dict:
    """Minute-change sensitivity on ladder samples (1 control + 6 knobs x 4 levels per Original).

    detection rate  - share of releases whose predicted primary-metric score is LOWER than the model's own
                      prediction for the unchanged control of the same Original (model-relative, so a model
                      that is biased low everywhere gets no credit);
    JND             - smallest level of an ordinal knob detected in >= 50% of Originals;
    monotonicity    - per Original, Spearman(level, predicted primary score); -1 = perfectly ordered;
    false alarms    - controls where any metric is predicted below `false_alarm_below` (images are identical)."""
    by_s = defaultdict(dict)
    for r in records:
        if r.get("kind") == "ladder":
            by_s[r["sample_id"]][r["release_id"]] = r
    per, controls = {}, []
    for rels in by_s.values():
        c = rels.get("control_0")
        if c:
            controls.append(c)
        for rid, r in rels.items():
            if rid == "control_0":
                continue
            m = r["primary_metric"]
            ref = c["pred"][m] if c else 1.0
            ref_overall = category_scores(c["pred"], category_weights)["overall"] if c else 1.0
            p = per.setdefault(rid, {"artifact_type": r["artifact_type"], "level": r["level"],
                                     "value": r.get("artifact_value"), "primary_metric": m, "gt": [], "pred": [],
                                     "det": [], "det_overall": []})
            p["gt"].append(r["gt"][m])
            p["pred"].append(r["pred"][m])
            p["det"].append(r["pred"][m] < ref - 1e-9)
            p["det_overall"].append(category_scores(r["pred"], category_weights)["overall"] < ref_overall - 1e-9)
    rows = []
    for rid, p in sorted(per.items(), key=lambda kv: (kv[1]["artifact_type"], kv[1]["level"])):
        gt, pr = np.array(p["gt"]), np.array(p["pred"])
        rows.append({"release_id": rid, "artifact_type": p["artifact_type"], "level": p["level"], "value": p["value"],
                     "primary_metric": p["primary_metric"], "n": len(gt), "gt_mean": float(gt.mean()),
                     "pred_mean": float(pr.mean()), "MAE": float(np.mean(np.abs(gt - pr))),
                     "detection_rate": float(np.mean(p["det"])), "overall_detection_rate": float(np.mean(p["det_overall"]))})
    jnd, mono = {}, {}
    for knob in sorted({r["artifact_type"] for r in rows}):
        lv = sorted((r for r in rows if r["artifact_type"] == knob), key=lambda r: r["level"])
        if knob == "font_family":  # nominal levels: no JND / ordering
            continue
        hit = [r for r in lv if r["detection_rate"] >= 0.5]
        jnd[knob] = {"level": hit[0]["level"], "value": hit[0]["value"]} if hit else None
        rhos = []
        for rels in by_s.values():
            pts = sorted((r["level"], r["pred"][r["primary_metric"]]) for r in rels.values() if r.get("artifact_type") == knob)
            if len(pts) >= 3 and np.std([q for _, q in pts]) > 1e-9:
                rhos.append(spearmanr([l for l, _ in pts], [q for _, q in pts])[0])
        mono[knob] = {"mean_spearman": float(np.mean(rhos)) if rhos else float("nan"), "n_with_variation": len(rhos),
                      "n_flat": len(by_s) - len(rhos)}
    fa = [any(c["pred"][k] < false_alarm_below for k in METRIC_KEYS) for c in controls]

    # cross-metric leakage: how much each single-factor edit moves EVERY metric (pred minus own control).
    # A precise judge moves only the edited metric; mass on other metrics = confusing one defect for another.
    leak = defaultdict(lambda: defaultdict(list))
    for rels in by_s.values():
        c = rels.get("control_0")
        if not c:
            continue
        for rid, r in rels.items():
            if rid != "control_0":
                for k in METRIC_KEYS:
                    leak[r["artifact_type"]][k].append(r["pred"][k] - c["pred"][k])
    leakage = {knob: {k: float(np.mean(v)) for k, v in ks.items()} for knob, ks in leak.items()}
    precision = {}
    for knob, d in leakage.items():
        prim = KNOB_PRIMARY.get(knob)
        drops = {k: max(0.0, -v) for k, v in d.items()}
        tot = sum(drops.values())
        precision[knob] = (drops.get(prim, 0.0) / tot) if tot > 1e-9 else float("nan")
    return {"n_originals": len(by_s), "rows": rows, "jnd": jnd, "monotonicity": mono,
            "leakage": leakage, "attribution_precision": precision,
            "control": {"n": len(controls), "false_alarm_rate": float(np.mean(fa)) if fa else float("nan"),
                        "mean_pred_overall": float(np.mean([category_scores(c["pred"], category_weights)["overall"]
                                                            for c in controls])) if controls else float("nan")}}
