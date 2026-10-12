"""Stage 6 - Agreement analytics + diagnostic audit + report.

Reads predictions/<model>_<split>.jsonl for each model and the ground truth in data/pairs/<split>.jsonl,
then writes reports/evaluation_report.md, reports/evaluation_metrics.xlsx, figures and ranking CSVs.

Usage: python scripts/06_evaluate.py --models baseline_zero_shot finetuned_qlora [--split test]
       [--human_csv data/human/pilot_annotations.csv]
"""

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prism.common import P, load_config, read_jsonl  # noqa: E402
from prism.evaluation import evaluate, human_ceiling  # noqa: E402
from prism.report import write_report  # noqa: E402


def load_rows(cfg, model, split, pred_dir=None):
    gt = {r["id"]: r for r in read_jsonl(P(cfg, "pairs_dir", f"{split}.jsonl"))}
    pred_path = os.path.join(pred_dir or P(cfg, "predictions_dir"), f"{model}_{split}.jsonl")
    preds = {r["id"]: r for r in read_jsonl(pred_path)}
    rows = []
    for pid, p in preds.items():
        g = gt[pid]
        rows.append({"id": pid, "sample_id": g["sample_id"], "release_id": g["release_id"], "template": g["template"],
                     "gt": g["scores"], "pred": p.get("pred"), "retried": p.get("retried", False)})
    return rows


def run_evaluation(cfg, models, split="test", pred_dir=None, out_dir=None, human_csv=None, extra=None):
    w = cfg["scoring"]["category_weights"]
    thr = cfg["evaluation"]["top_error_threshold"]
    rows_by, results = {}, {}
    for m in models:
        rows_by[m] = load_rows(cfg, m, split, pred_dir)
        results[m] = evaluate(rows_by[m], w, thr)
        print(f"[evaluate] {m}: n={len(rows_by[m])} valid={results[m]['coverage']['valid_rate']:.3f} "
              f"MAE={results[m]['all_metrics_pooled'].get('MAE', float('nan')):.4f} "
              f"bestRelease={results[m]['ranking']['best_release_accuracy_RSA']:.3f}")
    human = None
    if human_csv and os.path.exists(human_csv):
        gt_lookup = {}
        for sp in ("train", "val", "test"):
            fp = P(cfg, "pairs_dir", f"{sp}.jsonl")
            if os.path.exists(fp):
                for r in read_jsonl(fp):
                    gt_lookup[(r["sample_id"], r["release_id"])] = r["scores"]
        with open(human_csv) as f:
            human = human_ceiling(list(csv.DictReader(f)), gt_lookup)
    out = out_dir or P(cfg, "reports_dir")
    path = write_report(results, rows_by, out, title=f"PRISM VLM evaluation - {split} split", extra=extra, human=human)
    print(f"[evaluate] report -> {path}")
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--models", nargs="+", default=["baseline_zero_shot", "finetuned_qlora"])
    ap.add_argument("--split", default="test")
    ap.add_argument("--human_csv", default=None)
    a = ap.parse_args()
    cfg = load_config(a.config)
    models = [m for m in a.models if os.path.exists(os.path.join(P(cfg, "predictions_dir"), f"{m}_{a.split}.jsonl"))]
    missing = set(a.models) - set(models)
    if missing:
        print(f"[evaluate] WARNING: no predictions for {sorted(missing)} - evaluating {models}")
    if not models:
        sys.exit("[evaluate] no prediction files found")
    run_evaluation(cfg, models, a.split, human_csv=a.human_csv,
                   extra={"Base model": cfg["model"]["base"], "Split": a.split,
                          "Ground truth": "pre-defined scores realised by the renderer (see data/metadata)"})


if __name__ == "__main__":
    main()
