"""Stage 8 - Self-improving data engine: generate more training data exactly where the model is still blind.

Reads the ladder sensitivity analysis of a model (reports/evaluation_results.json from 06_evaluate.py on
--split ladder_test or ladder_val), finds the edit families whose just-noticeable level is not L1 (or that
are never detected), and generates new ladder Originals that contain ONLY those edit families. They are
written to data/metadata/ladder_engine.jsonl and 02_build_splits.py adds them to the TRAINING split only
(they are new documents, so val/test stay untouched). Retrain, re-evaluate, repeat - every round focuses
the data on the model's current blind spots. All labels are measured by the renderer; nothing is manual.

Usage: python scripts/08_data_engine.py --model finetuned_qlora [--results reports/evaluation_results.json]
                                        [--n 42] [--round 1] [--workers 0]
"""

import argparse
import json
import os
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prism.common import P, load_config, write_jsonl  # noqa: E402
from prism.ladder import ORDINAL_KNOBS, make_ladder_sample  # noqa: E402

CFG = None


def _init(cfg):
    global CFG
    CFG = cfg


def _make(i):
    return make_ladder_sample(CFG, i)


def blind_spots(lad: dict, min_detection: float = 0.5) -> list:
    """Ordinal edit families whose level-1 edit is detected in fewer than `min_detection` of the Originals."""
    weak = []
    for knob in ORDINAL_KNOBS:
        j = lad.get("jnd", {})
        if knob in j and (j[knob] is None or j[knob]["level"] > 1):
            weak.append(knob)
    rows = [r for r in lad.get("rows", []) if r["artifact_type"] == "font_family"]
    if rows and min(r["detection_rate"] for r in rows) < min_detection:
        weak.append("font_family")
    return weak


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--model", required=True)
    ap.add_argument("--results", default=None)
    ap.add_argument("--n", type=int, default=42, help="new ladder Originals to generate this round")
    ap.add_argument("--round", type=int, default=1)
    ap.add_argument("--workers", type=int, default=0)
    a = ap.parse_args()
    cfg = load_config(a.config)
    path = a.results or os.path.join(P(cfg, "reports_dir"), "evaluation_results.json")
    res = json.load(open(path))
    if a.model not in res or "ladder" not in res[a.model]:
        sys.exit(f"{path} has no ladder analysis for {a.model} - run 06_evaluate.py --split ladder_val first")
    weak = blind_spots(res[a.model]["ladder"])
    print(f"[engine] blind spots of {a.model}: {weak or 'none - every edit family detected at level 1'}")
    if not weak:
        return
    cfg["ladder"]["knobs"] = weak
    start = 10000 * a.round
    with Pool(a.workers or os.cpu_count() or 1, initializer=_init, initargs=(cfg,)) as pool:
        recs = pool.map(_make, range(start, start + a.n))
    for r in recs:
        r["engine_round"] = a.round
        r["engine_targets"] = weak
    out = P(cfg, "metadata_dir", "ladder_engine.jsonl")
    old = []
    if os.path.exists(out):
        with open(out) as f:
            old = [json.loads(l) for l in f if l.strip() and json.loads(l).get("engine_round") != a.round]
    write_jsonl(out, old + recs)
    n_pairs = sum(len(r["releases"]) for r in recs)
    print(f"[engine] round {a.round}: {len(recs)} Originals, {n_pairs} pairs focused on {weak} -> {out}")
    print("[engine] next: python scripts/02_build_splits.py  (adds them to train)  ->  retrain  ->  re-evaluate")


if __name__ == "__main__":
    main()
