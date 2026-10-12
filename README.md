# Samsung PRISM 26VI05 - VLM image-quality evaluation pipeline (English)

End-to-end pipeline: **dataset with pre-defined ground-truth scores -> pairwise JSONL -> zero-shot
benchmark -> QLoRA fine-tuning -> CoT inference -> validation gate -> Python score engine ->
agreement analytics -> diagnostic audit.**

## How to run
- **One command:** `./run_all.sh` runs every stage in order (each stage is resumable).
- **Google Colab:** upload this folder (zipped as `prism_vlm.zip`) to Drive, open `colab_run_pipeline.ipynb`,
  choose a GPU runtime, Run all.
- **Kaggle (free 2x T4):** see `kaggle/` - `datagen` regenerates the dataset on CPU, `pipeline` runs the GPU
  stages (baseline and QLoRA training in parallel, one GPU each) and stops cleanly before the 12 h limit;
  `pipeline-resume` continues from that output.

### Step by step
1. `pip install torch` (matching your CUDA), then `pip install -r requirements.txt`
   (`requirements-cpu.txt` is enough for stages 1-2 and the self-test).
2. `python scripts/01_generate_dataset.py` - 700 samples -> 2,800 images; every `target_vs_realised_MAE`
   in `data/metadata/generation_summary.json` should be < 0.05.
3. `python scripts/02_build_splits.py` - must print `leakage_check passed`.
4. `python scripts/make_pilot_showcase.py`, `python scripts/00_selftest.py` (prints `SELFTEST PASSED`),
   `python scripts/export_annotation_sheet.py`.
5. `python scripts/gpu_smoke_test.py` - must print `SMOKE TEST PASSED`; apply any RECOMMEND line to `configs/config.yaml`.
6. `python scripts/03_prompt_study_and_baseline.py` - prompt study (P1-P4, validation) + zero-shot baseline (test).
7. `python scripts/04_train_qlora.py` - QLoRA fine-tuning; best adapter chosen by validation MAE.
8. `python scripts/05_infer.py --adapter outputs/best_adapter --name finetuned_qlora --split test`
9. `python scripts/06_evaluate.py --models baseline_zero_shot finetuned_qlora --split test`
   (add `--human_csv data/human/pilot_annotations.csv` if that file exists).

Low-VRAM GPUs (T4, 15 GB): set `model.max_pixels: 501760`, `inference.batch_size: 2`, `train.epochs: 2`,
`inference.prompt_study_n: 30` in `configs/config.yaml`.

Hardware: NVIDIA GPU with >= 16 GB VRAM recommended (12 GB works with lower `max_pixels`).
Rough times: dataset 15-30 min (CPU), prompt study + baseline 1-3 h, training 2-6 h, final inference 1-2 h.

## The dataset (Mimat's approach: score first, then render)
Every sample = 1 Original + 3 releases. Before rendering, each release gets a **random target score for
all 12 metrics**; the renderer turns each target into a controlled physical change, **measures what it
actually produced**, and stores that measured value as ground truth. The release's focus category
(R1 technical, R2 visual, R3 human perception) degrades more; all other metrics get **minute changes**
(often exactly none), so the model must learn to see small differences.

| Metric | Controlled change (score 1.0 = identical, 0.0 = maximum) |
|---|---|
| OCR Accuracy | % of characters substituted (confusables like O/0, l/1), up to 25% |
| Alignment Preservation | text blocks moved up to 40 px x / 12 px y |
| Font Similarity | 0.6 x size change (up to 35%) + 0.4 x typeface change (similar = 0.5, other class = 1) |
| Object Preservation | logos/stamps/QR/photos shrink up to 40%, move up to 30 px, fade up to 70% |
| Background Fidelity | colour of the inpainted text regions, CIEDE2000 up to 25 (measured after rendering) |
| Texture Continuity | fraction of paper grain smoothed inside edited regions (measured) |
| Ghost Text Residue | faint offset copy of old glyphs, opacity up to 45% |
| Lighting Consistency | illumination gradient, up to 45% darker at one side |
| Reading Flow | line spacing change (up to +60% / -30%) + baseline jitter |
| Visual Anchor Integrity | titles/headings shrink up to 35% and move; rules thin and break |
| Semantic Emphasis | fraction of bold/coloured phrases that lose styling |
| Authenticity | JPEG quality 95 -> 20 plus noise in edited regions |

**8 finalised English templates:** invoice, receipt, certificate, application form, business letter,
restaurant menu, event flyer, mobile settings screen - all randomised (names, items, prices, colours,
fonts from 11 bundled open-licence families, paper texture, logos, stamps, QR codes, signatures, photos).
Drop your own photos into `assets/photos/` and the flyer/menu/form photo areas will use them.

### Included dataset
The generated dataset is committed in `data/`: 700 samples (`data/images/sample_XXXX/{original,R1,R2,R3}.png`,
2,800 images), full metadata and the train/val/test pairs, so stages 1-2 can be skipped. Regenerating with
`scripts/01_generate_dataset.py` reproduces it (seeded).

### Metadata
- `data/metadata/samples.jsonl` - one record per sample: template, seed, original path, `ocr_data`
  (line text + bounding boxes), and per release: image path, `target_scores`, ground-truth `scores`,
  `category_scores`, `control_parameters` (exact physical changes), `reasoning`, `ocr_data_release`,
  `ground_truth_source: "predefined"`, plus `gt_ranking` / `gt_best_release`.
- `data/metadata/metadata.csv` - one row per Original-Release pair (opens in Excel).
- `data/pairs/{train,val,test}.jsonl` - pairwise training records (Original + one release + CoT/JSON target),
  split 70/15/15 **by sample_id** (no leakage), stratified by template.
- `pilot/` - **5 images per artifact type** (each changes one metric only) with contact sheets in
  `pilot/sheets/` and `pilot_metadata.json` - this is the batch to show Ramesh and Mimat.

## Model pipeline (matches the Training & Evaluation slide)
1. Training inputs - pairwise JSONL, Qwen2.5-VL processor (image tokens never truncated), 4-bit NF4 base.
2. QLoRA adapters - all-linear, r 16 / alpha 32 / dropout 0.05.
3. Optimisation - TRL SFTTrainer, cosine LR, warmup 5%, grad-accum 16, validation checkpointing.
4. Validation gate - JSON schema + numeric range check, one retry, failures logged (`prism/validation.py`).
5. Inference scoring - forced CoT (`<analysis>` one line per metric) then the 12 scores (`prism/vlm.py`).
6. Python engine - category averages, overall, R1/R2/R3 ranking, best release (`prism/scoring.py`).
7. Agreement analytics - MAE, RMSE, PLCC, SROCC (`prism/evaluation.py`).
8. Diagnostic audit - top errors (|error| > 0.30), failure patterns, error by severity, optional human ceiling.

Checkpoint selection uses **validation-set generation MAE**, not training loss.

## Accuracy measures reported
Per metric, per category, overall and per template: MAE, RMSE, PLCC, SROCC, bias, accuracy within
+-0.05 / +-0.10 / +-0.15, quality-band accuracy and macro-F1 (excellent/good/fair/poor). Ranking:
best-release accuracy, exact R1/R2/R3 ranking accuracy, Kendall tau, pairwise preference accuracy.
Coverage: valid-output rate after the gate. Baseline vs fine-tuned side by side.

## Optional human check
`scripts/export_annotation_sheet.py` creates a 20-pair sheet for 3 annotators. Save the filled file as
`data/human/pilot_annotations.csv`; the evaluation then reports human sigma, the human-ceiling error per
metric, and how well the pre-defined scores match human judgement.

## Layout
```
configs/config.yaml        all settings
prism/                     library (templates, renderer, metrics, prompts, gate, scoring, evaluation, report, vlm)
scripts/00..06             stages; gpu_smoke_test.py; make_pilot_showcase.py; export_annotation_sheet.py
assets/fonts               bundled open-licence fonts (DejaVu, Liberation, Carlito, Caladea, Poppins, FreeFont)
```
