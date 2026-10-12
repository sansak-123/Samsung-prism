"""Pilot showcase for the mentors' review: 5 images per artifact type (12 metrics x 5 levels = 60 pairs).

Each pair changes ONE metric only, at a pre-defined score, so the reviewers can check that
"score 0.85 looks like 0.85". Templates rotate across the levels.

Outputs: pilot/images/<metric>/..., pilot/sheets/<metric>.png (contact sheet),
         pilot/pilot_metadata.json, pilot/pilot_metadata.csv
"""

import argparse
import csv
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prism.common import P, load_config  # noqa: E402
from prism.document import get_font  # noqa: E402
from prism.metrics import METRIC_KEYS, METRIC_NAMES, METRIC_CATEGORY  # noqa: E402
from prism.perturb import isolated_severities  # noqa: E402
from prism.reasoning import build_reasoning, scores_from_severity  # noqa: E402
from prism.render import render  # noqa: E402
from prism.templates import build_document  # noqa: E402

TW, TH = 300, 400


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    a = ap.parse_args()
    cfg = load_config(a.config)
    root = P(cfg, "pilot_dir")
    os.makedirs(os.path.join(root, "sheets"), exist_ok=True)
    templates = cfg["dataset"]["templates"]
    levels = cfg["pilot"]["levels"]
    meta = []
    for mi, metric in enumerate(METRIC_KEYS):
        mdir = os.path.join(root, "images", metric)
        os.makedirs(mdir, exist_ok=True)
        tiles = []
        for li, lvl in enumerate(levels):
            template = templates[(mi + li) % len(templates)]
            seed = 900000 + mi * 100 + li
            doc = build_document(template, seed)
            orig, _ = render(doc, None, seed=seed)
            rel, info = render(doc, isolated_severities(metric, lvl), seed=seed + 1)
            op, rp = os.path.join(mdir, f"L{li + 1}_original.png"), os.path.join(mdir, f"L{li + 1}_release.png")
            orig.save(op)
            rel.save(rp)
            scores = scores_from_severity(info["realised_severity"])
            meta.append({"pilot_id": f"{metric}_L{li + 1}", "artifact_type": metric, "metric_category": METRIC_CATEGORY[metric],
                         "template": template, "original_image_path": os.path.relpath(op, cfg["_root"]),
                         "release_image_path": os.path.relpath(rp, cfg["_root"]),
                         "target_score": round(1 - lvl, 2), "ground_truth_score": scores[metric],
                         "all_scores": scores, "control_parameters": info["details"],
                         "reasoning": build_reasoning(info["realised_severity"], info["details"]),
                         "ground_truth_source": "predefined", "ocr_data": info["ocr_boxes_original"]})
            tiles.append((orig, rel, scores[metric], template))
        # contact sheet: top row originals, bottom row releases with the score
        sheet = Image.new("RGB", (TW * len(tiles), TH * 2 + 70), "white")
        d = ImageDraw.Draw(sheet)
        d.text((10, 8), f"{METRIC_NAMES[metric]} ({METRIC_CATEGORY[metric]}) - top: Original, bottom: Release",
               fill=(0, 0, 0), font=get_font("DejaVuSans", True, 20))
        for j, (o, r, sc, t) in enumerate(tiles):
            sheet.paste(o.resize((TW, TH)), (j * TW, 40))
            sheet.paste(r.resize((TW, TH)), (j * TW, 40 + TH))
            d.text((j * TW + 8, 44 + 2 * TH), f"score = {sc:.2f}  [{t}]", fill=(180, 20, 20),
                   font=get_font("DejaVuSans", True, 16))
        sheet.save(os.path.join(root, "sheets", f"{mi + 1:02d}_{metric}.png"))
        print(f"[pilot] {metric}: " + ", ".join(f"{t[2]:.2f}" for t in tiles), flush=True)

    with open(os.path.join(root, "pilot_metadata.json"), "w") as f:
        json.dump(meta, f, indent=2)
    with open(os.path.join(root, "pilot_metadata.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pilot_id", "artifact_type", "metric_category", "template", "target_score", "ground_truth_score",
                    "original_image_path", "release_image_path"])
        for m in meta:
            w.writerow([m["pilot_id"], m["artifact_type"], m["metric_category"], m["template"], m["target_score"],
                        m["ground_truth_score"], m["original_image_path"], m["release_image_path"]])
    print(f"[pilot] {len(meta)} pairs -> {root}")


if __name__ == "__main__":
    main()
