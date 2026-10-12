"""Stage 1 - Generate the English dataset with PRE-DEFINED ground-truth scores.

For each sample: one Original + three releases (R1/R2/R3). Each release gets a random target
score for all 12 metrics, the renderer realises it, and the *measured* realisation is stored as
ground truth in the metadata (no human annotation needed for these labels).

Outputs
  data/images/<sample_id>/{original,R1,R2,R3}.png
  data/metadata/samples.jsonl     one record per sample (full metadata, OCR boxes, control params)
  data/metadata/metadata.csv      one row per Original-Release pair (easy to open in Excel)
  data/metadata/generation_summary.json   realisation fidelity (target vs realised)

Usage:  python scripts/01_generate_dataset.py [--n 700] [--workers 8]
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prism.common import P, load_config, write_jsonl  # noqa: E402
from prism.metrics import CATEGORIES, METRIC_KEYS  # noqa: E402
from prism.perturb import sample_release_severities  # noqa: E402
from prism.reasoning import build_reasoning, scores_from_severity  # noqa: E402
from prism.render import render  # noqa: E402
from prism.scoring import category_scores, rank_releases  # noqa: E402
from prism.templates import build_document  # noqa: E402

CFG = None


def _init(cfg):
    global CFG
    CFG = cfg


def make_sample(i: int) -> dict:
    cfg = CFG
    seed = cfg["project_seed"]
    templates = cfg["dataset"]["templates"]
    template = templates[i % len(templates)]
    sid = f"sample_{i:04d}"
    doc_seed = seed * 100003 + i
    doc = build_document(template, doc_seed)
    out_dir = P(cfg, "images_dir", sid)
    os.makedirs(out_dir, exist_ok=True)
    rel_dir = os.path.join(cfg["paths"]["images_dir"], sid)

    orig, oinfo = render(doc, None, seed=doc_seed)
    orig.save(os.path.join(out_dir, "original.png"))

    releases = []
    w = cfg["scoring"]["category_weights"]
    for ri, (rid, profile) in enumerate(cfg["dataset"]["release_profiles"].items()):
        rng = np.random.default_rng([seed, i, ri])
        target_sev = sample_release_severities(profile, rng, cfg)
        img, info = render(doc, target_sev, seed=doc_seed * 10 + ri + 1)
        img.save(os.path.join(out_dir, f"{rid}.png"))
        scores = scores_from_severity(info["realised_severity"])
        releases.append({
            "release_id": rid,
            "profile": profile,
            "release_image_path": f"{rel_dir}/{rid}.png",
            "target_scores": {k: round(1 - target_sev[k], 2) for k in METRIC_KEYS},
            "scores": scores,
            "category_scores": category_scores(scores, w),
            "ground_truth_source": "predefined",
            "control_parameters": info["details"],
            "reasoning": build_reasoning(info["realised_severity"], info["details"]),
            "ocr_data_release": info["ocr_boxes_release"],
        })
    ranking, _ = rank_releases({r["release_id"]: r["scores"] for r in releases}, w)
    return {
        "sample_id": sid,
        "template": template,
        "language": cfg["dataset"]["language"],
        "doc_seed": doc_seed,
        "image_size": [doc.width, doc.height],
        "original_image_path": f"{rel_dir}/original.png",
        "ocr_data": oinfo["ocr_boxes_original"],
        "n_objects": len(doc.objects),
        "releases": releases,
        "gt_ranking": ranking,
        "gt_best_release": ranking[0],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--n", type=int, default=None)
    ap.add_argument("--workers", type=int, default=None)
    a = ap.parse_args()
    cfg = load_config(a.config)
    n = a.n or cfg["dataset"]["n_samples"]
    workers = a.workers if a.workers is not None else cfg["dataset"]["workers"]
    workers = workers or os.cpu_count() or 1
    t0 = time.time()
    records = []
    with Pool(workers, initializer=_init, initargs=(cfg,)) as pool:
        for k, rec in enumerate(pool.imap(make_sample, range(n), chunksize=2)):
            records.append(rec)
            if (k + 1) % 25 == 0 or k + 1 == n:
                el = time.time() - t0
                print(f"[generate] {k + 1}/{n} samples  ({el:.0f}s, eta {el / (k + 1) * (n - k - 1):.0f}s)", flush=True)

    md = P(cfg, "metadata_dir")
    os.makedirs(md, exist_ok=True)
    write_jsonl(os.path.join(md, "samples.jsonl"), records)

    with open(os.path.join(md, "metadata.csv"), "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["sample_id", "release_id", "template", "profile", "original_image_path", "release_image_path"]
                    + METRIC_KEYS + CATEGORIES + ["overall", "is_gt_best"])
        for r in records:
            for rel in r["releases"]:
                cs = rel["category_scores"]
                wr.writerow([r["sample_id"], rel["release_id"], r["template"], rel["profile"], r["original_image_path"],
                             rel["release_image_path"]] + [rel["scores"][k] for k in METRIC_KEYS]
                            + [cs[c] for c in CATEGORIES] + [cs["overall"], rel["release_id"] == r["gt_best_release"]])

    # realisation fidelity and label distribution
    summ = {"n_samples": len(records), "n_pairs": 3 * len(records), "seconds": round(time.time() - t0, 1),
            "per_metric": {}, "best_release_distribution": {}}
    for k in METRIC_KEYS:
        tg = np.array([rel["target_scores"][k] for r in records for rel in r["releases"]])
        gt = np.array([rel["scores"][k] for r in records for rel in r["releases"]])
        summ["per_metric"][k] = {"target_vs_realised_MAE": round(float(np.mean(np.abs(tg - gt))), 4),
                                 "gt_mean": round(float(gt.mean()), 3), "gt_std": round(float(gt.std()), 3),
                                 "gt_min": round(float(gt.min()), 2), "share_gt_below_0.9": round(float(np.mean(gt < 0.9)), 3)}
    for r in records:
        summ["best_release_distribution"][r["gt_best_release"]] = summ["best_release_distribution"].get(r["gt_best_release"], 0) + 1
    with open(os.path.join(md, "generation_summary.json"), "w") as f:
        json.dump(summ, f, indent=2)
    print(json.dumps(summ, indent=2))


if __name__ == "__main__":
    main()
