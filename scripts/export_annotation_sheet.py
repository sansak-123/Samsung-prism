"""Optional - export a human pilot-annotation sheet (default 20 pairs from the test split).

Three annotators fill one CSV each (or one CSV with an `annotator` column). Feed it to
`06_evaluate.py --human_csv` to get human sigma, the human-ceiling error per metric, and how well
the PRE-DEFINED scores agree with human perception (the check the mentors asked for).
"""

import argparse
import csv
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prism.common import P, load_config, read_jsonl  # noqa: E402
from prism.metrics import METRIC_KEYS  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--annotators", nargs="+", default=["A1", "A2", "A3"])
    a = ap.parse_args()
    cfg = load_config(a.config)
    test = read_jsonl(P(cfg, "pairs_dir", "test.jsonl"))
    random.Random(cfg["project_seed"]).shuffle(test)
    pick = test[: a.n]
    out = os.path.join(cfg["_root"], "data", "human", "pilot_annotations_TEMPLATE.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sample_id", "release_id", "annotator", "original_image_path", "release_image_path"] + METRIC_KEYS)
        for ann in a.annotators:
            for r in pick:
                w.writerow([r["sample_id"], r["release_id"], ann, r["original_image_path"], r["release_image_path"]]
                           + [""] * len(METRIC_KEYS))
    print(f"annotation sheet -> {out}  (fill scores 0-1, save as data/human/pilot_annotations.csv)")


if __name__ == "__main__":
    main()
