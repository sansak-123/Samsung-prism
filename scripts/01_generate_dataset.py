"""Stage 1 - Generate the English dataset: the "24 generation" minute-change ladder (prism/ladder.py).

For each Original: 1 unchanged control + 6 edit families x 4 levels = 24 releases, each changing ONE text
block. Every release's 12 ground-truth scores are MEASURED by the renderer during generation and stored
in the metadata (no human annotation needed for these labels).

Outputs
  data/images/ladder_XXXX/{original,control_0,<knob>_<level>}.png
  data/metadata/ladder.jsonl           one record per Original (full metadata, OCR boxes, control params)
  data/metadata/ladder_metadata.csv    one row per Original-Release pair (easy to open in Excel)
  data/metadata/ladder_summary.json    per knob x level: mean measured score, render audit, monotonicity
  data/metadata/metadata_ladder.json   24 records per Original in the metadata_real.json schema (measured scores)

Usage:  python scripts/01_generate_dataset.py [--n 147] [--workers 8]
"""

import argparse
import csv
import json
import os
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prism.common import P, load_config, write_jsonl  # noqa: E402
from prism.ladder import ladder_summary, make_ladder_sample, to_metadata_real  # noqa: E402
from prism.metrics import CATEGORIES, METRIC_KEYS  # noqa: E402

CFG = None


def _init(cfg):
    global CFG
    CFG = cfg


def make_ladder(i: int) -> dict:
    return make_ladder_sample(CFG, i)


def generate_ladder(cfg, n, workers):
    t0 = time.time()
    records = []
    with Pool(workers, initializer=_init, initargs=(cfg,)) as pool:
        for k, rec in enumerate(pool.imap(make_ladder, range(n))):
            records.append(rec)
            if (k + 1) % 5 == 0 or k + 1 == n:
                el = time.time() - t0
                print(f"[ladder] {k + 1}/{n} originals x {len(rec['releases'])}  "
                      f"({el:.0f}s, eta {el / (k + 1) * (n - k - 1):.0f}s)", flush=True)
    md = P(cfg, "metadata_dir")
    os.makedirs(md, exist_ok=True)
    write_jsonl(os.path.join(md, "ladder.jsonl"), records)
    # same schema as metadata_real.json (prism_iqa): 24 records per Original, measured metric_scores
    with open(os.path.join(md, "metadata_ladder.json"), "w", encoding="utf-8") as f:
        json.dump(to_metadata_real(records), f, indent=2, ensure_ascii=False)
    with open(os.path.join(md, "ladder_metadata.csv"), "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["sample_id", "release_id", "template", "artifact_type", "level", "artifact_value", "primary_metric",
                     "target_block", "original_image_path", "release_image_path"] + METRIC_KEYS + CATEGORIES
                    + ["overall", "changed_pixels", "changed_pixels_outside_region"])
        for r in records:
            for rel in r["releases"]:
                cs = rel["category_scores"]
                wr.writerow([r["sample_id"], rel["release_id"], r["template"], rel["artifact_type"], rel["level"],
                             rel["artifact_value"], rel["primary_metric"], r["target_block"]["id"],
                             r["original_image_path"], rel["release_image_path"]]
                            + [rel["scores"][k] for k in METRIC_KEYS] + [cs[c] for c in CATEGORIES]
                            + [cs["overall"], rel["render_audit"]["changed_pixels"],
                               rel["render_audit"]["changed_pixels_outside_region"]])
    summ = ladder_summary(records)
    summ["seconds"] = round(time.time() - t0, 1)
    with open(os.path.join(md, "ladder_summary.json"), "w") as f:
        json.dump(summ, f, indent=2)
    print(json.dumps({k: summ[k] for k in ("n_samples", "n_pairs", "monotonic_share")}, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--n", type=int, default=None, help="ladder Originals (x25 pairs)")
    ap.add_argument("--workers", type=int, default=None)
    a = ap.parse_args()
    cfg = load_config(a.config)
    n = a.n or cfg["ladder"]["n_originals"]
    workers = a.workers if a.workers is not None else cfg["dataset"]["workers"]
    workers = workers or os.cpu_count() or 1
    generate_ladder(cfg, n, workers)


if __name__ == "__main__":
    main()
