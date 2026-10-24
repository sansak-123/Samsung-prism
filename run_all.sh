#!/usr/bin/env bash
# Full PRISM pipeline. Every stage is resumable; re-run after any interruption.
set -euo pipefail
cd "$(dirname "$0")"
PY=${PY:-python}

echo "=== [1/7] dataset generation (CPU) ==="
if [ ! -f data/metadata/ladder.jsonl ] || [ "$(wc -l < data/metadata/ladder.jsonl)" -lt "$($PY -c 'import yaml;print(yaml.safe_load(open("configs/config.yaml"))["ladder"]["n_originals"])')" ]; then
  $PY scripts/01_generate_dataset.py
fi
echo "=== [2/7] leakage-free splits + pairwise JSONL ==="
$PY scripts/02_build_splits.py
echo "=== [3/7] pilot showcase (5 images per artifact type) ==="
[ -d pilot/images ] || $PY scripts/make_pilot_showcase.py
echo "=== [4/7] CPU self-test ==="
$PY scripts/00_selftest.py

if ! $PY -c "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null; then
  echo "No CUDA GPU detected - stopping after the CPU stages. Run the rest on a GPU (see README / colab notebook)."
  exit 0
fi
echo "=== [5/7] prompt study (val) + zero-shot baseline (test) ==="
$PY scripts/03_prompt_study_and_baseline.py
echo "=== [6/7] QLoRA fine-tuning ==="
$PY scripts/04_train_qlora.py
echo "=== [7/7] fine-tuned inference + evaluation ==="
$PY scripts/05_infer.py --adapter outputs/best_adapter --name finetuned_qlora --split test
$PY scripts/06_evaluate.py --models baseline_zero_shot finetuned_qlora --split test
echo "DONE - open reports/evaluation_report.md"
