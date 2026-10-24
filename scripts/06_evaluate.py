"""Stage 6 - Agreement analytics + diagnostic audit + report.

Reads predictions/<model>_<split>.jsonl for each model and the ground truth in data/pairs/<split>.jsonl,
then writes reports/evaluation_report.md, reports/evaluation_metrics.xlsx, figures and ranking CSVs.

Usage: python scripts/06_evaluate.py --models baseline_zero_shot finetuned_qlora [--split test]
All ground truth is computed by the renderer during generation; there is no manual annotation input.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prism.common import P, load_config, read_jsonl  # noqa: E402
from prism.evaluation import evaluate  # noqa: E402
from prism.report import write_report  # noqa: E402


def load_rows(cfg, model, split, pred_dir=None):
    gt = {r["id"]: r for r in read_jsonl(P(cfg, "pairs_dir", f"{split}.jsonl"))}
    pred_path = os.path.join(pred_dir or P(cfg, "predictions_dir"), f"{model}_{split}.jsonl")
    preds = {r["id"]: r for r in read_jsonl(pred_path)}
    rows = []
    for pid, p in preds.items():
        g = gt[pid]
        rows.append({"id": pid, "sample_id": g["sample_id"], "release_id": g["release_id"], "template": g["template"],
                     "gt": g["scores"], "pred": p.get("pred"), "retried": p.get("retried", False),
                     "kind": g.get("kind", "ladder"), "target": g.get("target"), "raw": p.get("raw"),
                     **{k: g[k] for k in ("artifact_type", "level", "artifact_value", "primary_metric") if k in g}})
    return rows


def run_evaluation(cfg, models, split="test", pred_dir=None, out_dir=None, extra=None):
    w = cfg["scoring"]["category_weights"]
    thr = cfg["evaluation"]["top_error_threshold"]
    rows_by, results = {}, {}
    for m in models:
        rows_by[m] = load_rows(cfg, m, split, pred_dir)
        results[m] = evaluate(rows_by[m], w, thr, cfg["evaluation"].get("gate_threshold", 0.95))
        print(f"[evaluate] {m}: n={len(rows_by[m])} valid={results[m]['coverage']['valid_rate']:.3f} "
              f"MAE={results[m]['all_metrics_pooled'].get('MAE', float('nan')):.4f} "
              f"bestRelease={results[m]['ranking']['best_release_accuracy_RSA']:.3f}")
    out = out_dir or P(cfg, "reports_dir")
    path = write_report(results, rows_by, out, title=f"PRISM VLM evaluation - {split} split", extra=extra)
    print(f"[evaluate] report -> {path}")
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--models", nargs="+", default=["baseline_zero_shot", "finetuned_qlora"])
    ap.add_argument("--split", default="test")
    a = ap.parse_args()
    cfg = load_config(a.config)
    models = [m for m in a.models if os.path.exists(os.path.join(P(cfg, "predictions_dir"), f"{m}_{a.split}.jsonl"))]
    missing = set(a.models) - set(models)
    if missing:
        print(f"[evaluate] WARNING: no predictions for {sorted(missing)} - evaluating {models}")
    if not models:
        sys.exit("[evaluate] no prediction files found")
    run_evaluation(cfg, models, a.split,
                   extra={"Base model": cfg["model"]["base"], "Split": a.split,
                          "Ground truth": "pre-defined scores realised by the renderer (see data/metadata)"})


if __name__ == "__main__":
    main()
