"""Stage 2 - Leakage-free split (grouped by sample_id, stratified by template) + pairwise JSONL.

Every pairwise record = Original + ONE release, the P4 prompt id, and the CoT+JSON training target.
The dataset is the "24 generation" ladder (data/metadata/ladder.jsonl): the control and all 24 releases of
the same Original always land in the same split (asserted).

Outputs: data/pairs/{train,val,test}.jsonl, data/pairs/split_manifest.json
"""

import argparse
import json
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prism.common import P, load_config, read_jsonl, write_jsonl  # noqa: E402
from prism.metrics import METRIC_KEYS  # noqa: E402
from prism.prompts import TRAIN_PROMPT  # noqa: E402


def assign_splits(samples, fr, rng, holdout=()):
    """Grouped by sample_id, stratified by template. Templates in `holdout` go entirely to test, so the
    test split contains document types the model has never seen."""
    by_t = defaultdict(list)
    for s in samples:
        by_t[s["template"]].append(s["sample_id"])
    assign = {}
    for t, ids in sorted(by_t.items()):
        if t in holdout:
            assign.update({sid: "test" for sid in ids})
            continue
        ids = sorted(ids)
        rng.shuffle(ids)
        n = len(ids)
        n_va = max(1, round(n * fr["val"])) if n >= 3 else 0
        n_te = max(1, round(n * fr["test"])) if n >= 2 else 0
        n_tr = n - n_va - n_te
        for j, sid in enumerate(ids):
            assign[sid] = "train" if j < n_tr else ("val" if j < n_tr + n_va else "test")
    return assign


def to_pairs(samples, assign):
    pairs = {"train": [], "val": [], "test": []}
    for s in samples:
        sp = assign[s["sample_id"]]
        for rel in s["releases"]:
            target = ("<analysis>\n" + rel["reasoning"] + "\n</analysis>\n"
                      + json.dumps({k: rel["scores"][k] for k in METRIC_KEYS}))
            pairs[sp].append({
                "id": f"{s['sample_id']}_{rel['release_id']}",
                "sample_id": s["sample_id"],
                "release_id": rel["release_id"],
                "kind": s.get("kind", "ladder"),
                "template": s["template"],
                "original_image_path": s["original_image_path"],
                "release_image_path": rel["release_image_path"],
                "prompt_id": TRAIN_PROMPT,
                "target": target,
                "scores": rel["scores"],
                "artifact_type": rel["artifact_type"],
                "level": rel["level"],
                "artifact_value": rel["artifact_value"],
                "primary_metric": rel["primary_metric"],
            })
    return pairs


def _manifest(pairs):
    return {sp: {"n_samples": len({r["sample_id"] for r in rows}), "n_pairs": len(rows),
                 "templates": {t: len({r["sample_id"] for r in rows if r["template"] == t})
                               for t in sorted({r["template"] for r in rows})},
                 "sample_ids": sorted({r["sample_id"] for r in rows})} for sp, rows in pairs.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    a = ap.parse_args()
    cfg = load_config(a.config)
    fr = cfg["splits"]
    samples = read_jsonl(P(cfg, "metadata_dir", "ladder.jsonl"))
    holdout = set(fr.get("holdout_templates") or [])
    assign = assign_splits(samples, fr, random.Random(cfg["project_seed"]), holdout)
    pairs = to_pairs(samples, assign)
    random.Random(cfg["project_seed"] + 2).shuffle(pairs["train"])

    # data-engine rounds (08_data_engine.py): new documents aimed at the model's blind spots -> training only
    engine_path = P(cfg, "metadata_dir", "ladder_engine.jsonl")
    n_engine = 0
    if os.path.exists(engine_path):
        engine = read_jsonl(engine_path)
        epairs = to_pairs(engine, {s["sample_id"]: "train" for s in engine})["train"]
        pairs["train"] += epairs
        n_engine = len(epairs)
        random.Random(cfg["project_seed"] + 3).shuffle(pairs["train"])

    for sp, rows in pairs.items():
        write_jsonl(P(cfg, "pairs_dir", f"{sp}.jsonl"), rows)

    # leakage assertion (every release of an Original must stay in one split)
    seen = {}
    for sp, rows in pairs.items():
        for r in rows:
            assert seen.setdefault(r["sample_id"], sp) == sp, f"LEAKAGE: {r['sample_id']} in {seen[r['sample_id']]} and {sp}"
    manifest = _manifest(pairs)
    manifest["holdout_templates"] = sorted(holdout)
    manifest["data_engine_train_pairs"] = n_engine
    assert not any(r["template"] in holdout for r in pairs["train"] + pairs["val"]), "holdout template leaked into train/val"
    manifest["leakage_check"] = "passed: every sample_id appears in exactly one split"
    with open(P(cfg, "pairs_dir", "split_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print({sp: (manifest[sp]["n_samples"], manifest[sp]["n_pairs"]) for sp in pairs}, manifest["leakage_check"])


if __name__ == "__main__":
    main()
