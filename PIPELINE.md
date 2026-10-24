# PRISM 26VI05 - Implemented pipeline

```
[0] config ─► [1] synthesis ─► [2] splits ─► [3] pilot + self-test
                                   │
                                   ├─► [4] prompt study (val) ─► [5] zero-shot baseline (test)
                                   │
                                   └─► [6] QLoRA training ─► [7] fine-tuned inference (test)
                                                                     │
                       [5] + [7] ─► [8] validation gate ─► [9] score engine ─► [10] evaluation + audit
```

All settings: `configs/config.yaml`. Every stage is resumable (re-running skips finished work).

---

## [0] Configuration - `configs/config.yaml`, `prism/common.py`
- `project_seed: 2026` drives every random choice (documents, severities, splits, subsets).
- Paths are resolved relative to the project root; `abspath()` normalises Windows `\` so metadata
  generated on Windows works on Linux (Kaggle/Colab).

## [1] Score-first dataset synthesis - `scripts/01_generate_dataset.py`
Per sample `i` (700 samples, multiprocessing pool):

1. **Document** - `prism/templates.py`, `document.py`, `objects.py`
   - template = `templates[i % 23]`: invoice, receipt, certificate, application_form, business_letter,
     restaurant_menu, event_flyer, mobile_settings, bank_statement, payslip, boarding_pass, medical_prescription,
     resume, newsletter, nutrition_label, id_card, shipping_label, report_card, utility_bill, email_message,
     web_landing_page, chat_screenshot, presentation_slide.
   - `doc_seed = 2026 * 100003 + i` randomises text, prices, names, colours, 11 bundled font families,
     paper texture, logos, stamps, QR codes, signatures, photos.
   - Rendered Original -> `data/images/sample_XXXX/original.png`; OCR boxes recorded.
2. **Target severities** (score = 1 - severity) - `prism/perturb.py::sample_release_severities`
   - R1 focus = technical, R2 = visual, R3 = human_perception.
   - focus-category metrics: `Beta(2.0, 2.6)` (mean 0.43).
   - off-focus metrics: exactly 0 with p = 0.30, else `Beta(1.1, 14)` (mean 0.07, "minute" changes).
   - p = 0.20: one extra off-focus defect `U(0.25, 0.70)`; p = 0.08: whole release near-clean.
   - rounded to a 0.01 grid.
3. **Controlled rendering** - `prism/render.py::plan_release`, `render`. Severity 1.0 maps to (`prism/metrics.py::PHYS`):

   | Metric | Physical change at severity 1.0 |
   |---|---|
   | ocr_accuracy | 25% characters substituted with visual confusables (O/0, l/1, …) |
   | alignment_preservation | text blocks moved 40 px x / 12 px y |
   | font_similarity | 0.6 × size change (±35%) + 0.4 × typeface change (similar 0.5, other class 1.0) |
   | object_preservation | objects shrink 40%, shift 30 px, fade 70% |
   | background_fidelity | inpainted text regions shifted to CIEDE2000 ΔE 25 |
   | texture_continuity | paper grain smoothed in edited regions (blur searched to hit target) |
   | ghost_text_residue | offset copy of old glyphs at 45% opacity |
   | lighting_consistency | illumination gradient, 45% darker at one end |
   | reading_flow | line spacing +60% / −30%, baseline jitter 15% of line height |
   | visual_anchor_integrity | headings shrink 35% / move 25 px, rules thinned and broken |
   | semantic_emphasis | fraction of bold/coloured phrases lose styling |
   | authenticity | JPEG quality 95 -> 20 + Gaussian noise (σ ≤ 6) in edited patches |

4. **Measured ground truth** - after rendering, each realised change is measured (e.g. ΔE after gamut
   clipping, texture loss after blur, actual character error rate) and stored as `scores`.
   Target-vs-realised MAE ≤ 0.028 for every metric (`generation_summary.json`).
5. **Reasoning target** - `prism/reasoning.py` writes one `observation -> score` line per metric from the
   control parameters (e.g. `OCR: about 6.9% of characters differ ("Wireless"->"Wirebess") -> 0.72`).
6. **Ground-truth ranking** - `prism/scoring.py` applied to the measured scores -> `gt_ranking`, `gt_best_release`.

Outputs: `data/images/` (2,800 PNG), `data/metadata/samples.jsonl` (full record), `metadata.csv`,
`generation_summary.json`.

## [1b] Minute-change ladder - `prism/ladder.py` (run by `01_generate_dataset.py`, `--only ladder`)
Per ladder Original: `control_0` + **13 edit families x 4 levels = 52 releases**, each changing ONE thing
(one multi-line text block, one object or one heading). The first 6 families are the prism_iqa
"24 generation" (github.com/Sanjana432/prism_iqa `LADDERS`: 6 x 4 = 24 releases); the other 7 give 11 of
the 12 metrics their own single-factor ladder. `ladder.knobs` in the config selects the families.

Every score is computed automatically while the image is generated (no manual annotation), from what was
actually drawn, on the same scales (`metrics.PHYS`) as the R1/R2/R3 releases.
`score = round(1 - min(1, severity), 2)`.

| Edit family | Levels | Metric | Severity (written out in each release's `score_calculation`) |
|---|---|---|---|
| font_family (nominal) | same class / other class / monospace (or another cross-class face if it does not fit) / other class bold | font_similarity (+ semantic_emphasis for bold) | 0.4 x typeface term (0.5 same class, 1.0 other class) + 0.2 x bold |
| font_size | x1.01, 1.025, 1.05, 1.10 (line pitch kept) | font_similarity | 0.6 x abs(drawn size ratio - 1) / 0.35 |
| font_color | +2, 5, 10, 20 grey levels towards lower contrast | font_similarity | 0.6 x min(1, dE2000(ink) / 25) |
| inpaint_color_mismatch | 1, 3, 6, 12 grey levels on the re-filled patch | background_fidelity | dE2000(patch mean) / 25 |
| justification | block shifted 1, 2, 4, 8 px | alignment_preservation | px / hypot(40, 12) |
| line_spacing | +1, 2, 4, 8 px per line | reading_flow | (px / line pitch) / 0.6 |
| char_substitution | 1, 2, 3, 5 characters -> look-alikes (0/O, 1/l, rn/m ...) | ocr_accuracy | (substituted / characters in block) / 0.25 |
| ghost_residue | old glyphs at 2, 5, 10, 20 % opacity, 2 px offset | ghost_text_residue | opacity / 0.45 |
| texture_smoothing | 5, 10, 20, 35 % of the paper grain blurred away in the patch | texture_continuity | measured 1 - std(detail after) / std(detail before) |
| lighting_drop | soft shadow 2, 4, 8, 15 % darker at its centre, fading to 0 at the edges | lighting_consistency | drop / 0.45 |
| local_compression | block area re-saved as JPEG q92, 88, 82, 72 | authenticity | (95 - q) / 75 |
| object_shift | one logo / QR / stamp / photo moved 1, 2, 4, 8 px | object_preservation | px / 30 |
| heading_shift | one title / heading moved 1, 2, 4, 8 px | visual_anchor_integrity | px / 25 |

(semantic_emphasis has no ladder of its own; it moves with the bold font_family level.)

- Targets are chosen so that every edited version stays on the page, inside the panel it sits on
  (bubble / card / label) and clear of every other text block, object and rule; the object / heading must
  be able to move 8 px without touching anything. A document lacking a movable object or heading retries
  with new seeds; if still none, that family is skipped for that Original and recorded in `skipped_knobs`.
- The edited block is drawn **4x supersampled** (8x below 13 px) in the Original, the control and every
  release: Pillow rasterises at whole-pixel sizes, so a 1 % size change only survives supersampled.
- Per release: `render_audit` (changed pixels, pixels changed outside the edited region - always 0),
  `score_calculation` (formula with the measured numbers for all 12 metrics) and `pixel_measurements`
  (12 image-only measurements ported from prism_iqa `vision.compare`: changed-pixel fraction, ink IoU,
  font-height / line-pitch / left-edge deltas, foreground / background RGB distance, ...).
- **Check the scores yourself:** `python scripts/check_ladder_scores.py` re-computes every score from the
  stored measurements with its own copy of the formulas, checks locality, and cross-checks the images
  (controls pixel-identical, a 4 px shift shows up as a 4 px left-edge move, ...) ->
  `reports/ladder_score_check.csv` (one row per release x metric: formula, recomputed, stored).
- Reasoning lines name the region (e.g. `in the top-right block "Bill To Karthik ..."`).
- Outputs: `data/images/ladder_XXXX/`, `ladder.jsonl`, `ladder_metadata.csv`, `ladder_summary.json`,
  `metadata_ladder.json` (metadata_real.json schema with measured `metric_scores`, plus trailing
  `score_calculation` and `pixel_measurements`). Pairs: `data/pairs/ladder_{train,val,test}.jsonl`.
- Evaluation (`06_evaluate.py --split ladder_test`): detection rate per level (prediction below the model's
  own control prediction), just-noticeable level (>= 50 % detected), Spearman(level, prediction), false-alarm
  rate on the identical controls, **attribution precision** (share of the predicted drop that lands on the
  edited metric) and the full edit x metric leakage matrix, figure `ladder_sensitivity.png`.
  `ladder.include_in_train: true` adds ladder train pairs to training.

## [2] Leakage-free splits + pairwise records - `scripts/02_build_splits.py`
- Group by `sample_id`, stratify by template, shuffle with the seed: 70 / 15 / 15 ->
  492 / 104 / 104 samples = **1,476 / 312 / 312 pairs**.
- One record per (Original, Release): image paths, `prompt_id = P4`, `scores`, and
  `target = "<analysis>\n" + reasoning + "\n</analysis>\n" + JSON(12 scores)`.
- Assertion: every `sample_id` appears in exactly one split -> `split_manifest.json`.
- `splits.holdout_templates`: listed templates go entirely to test -> generalisation to document types
  never seen in training. Data-engine samples (`ladder_engine.jsonl`, stage 12) are added to train only.

## [3] Pilot + self-test (CPU)
- `make_pilot_showcase.py`: 12 metrics × 5 levels (scores 0.95…0.25), one metric changed at a time ->
  `pilot/sheets/`.
- `00_selftest.py`: renderer, gate, score engine and the full evaluation path with mock predictors
  (oracle + N(0, 0.05) must give MAE ≈ 0.04; malformed outputs must be caught).

## [4] Prompt study - `scripts/03_prompt_study_and_baseline.py`, `prism/prompts.py`
Base model untouched (4-bit), on a fixed seeded subset of **validation** (`prompt_study_n`, 30 on T4):
- **P1** minimal instruction + key list -> JSON.
- **P2** per-metric rubric + JSON spec.
- **P3** rubric + "output ONLY one JSON object".
- **P4** rubric + forced CoT: `<analysis>` with exactly one `- <observation> -> <score>` line per metric
  in fixed order, `</analysis>`, then JSON.
- Selection: `min(pooled MAE + 0.5 × (1 − valid_rate))` -> `reports/prompt_study.csv/json`,
  per-metric diagnostics `metric_diagnostics_zero_shot.csv`.

## [5] Zero-shot baseline
Selected prompt on the full **test** split -> `predictions/baseline_zero_shot_test.jsonl`.

## [6] QLoRA fine-tuning - `scripts/04_train_qlora.py`
- **Model**: `Qwen/Qwen2.5-VL-3B-Instruct`, bitsandbytes **4-bit NF4, double quant**, compute dtype
  bf16 if supported else fp16 (T4 -> fp16); `prepare_model_for_kbit_training`; SDPA attention.
- **Vision input**: dynamic resolution, `min_pixels 200,704` / `max_pixels 501,760` (T4) ->
  256-640 visual tokens per image (one token per 28×28 px). `max_seq_len 4096`, **never truncated**
  (over-length raises an error).
- **Collator**: chat template (system + "ORIGINAL:" img + "RELEASE:" img + P4 + target); labels = −100
  before the `<|im_start|>assistant\n` marker and on padding -> loss only on CoT + JSON.
- **LoRA**: `target_modules = all-linear`, r 16, α 32, dropout 0.05, bias none.
- **Optimisation**: TRL `SFTTrainer` (fallback: `transformers.Trainer`), batch 1 × grad-accum 16,
  LR 1e-4 cosine, warmup 5%, weight decay 0.01, max grad norm 1.0, `paged_adamw_8bit`,
  gradient checkpointing (non-reentrant), epochs 2 on T4 (3 default) = 93 steps/epoch.
- **Checkpoint selection** (`ValGenerationCallback`): every ½ epoch (46 steps) -> eval loss on 120 val
  pairs, then **generation** on a fixed 32-pair val subset -> gate -> MAE;
  `selection = MAE + 0.5 × invalid_rate`; best -> `outputs/best_adapter/` (+ `val_score.json`);
  history -> `outputs/val_generation_log.jsonl`.
- Resumes from `outputs/checkpoints/checkpoint-*` (keeps last 3). Final -> `final_adapter/`, `training_log.json`.

## [7] Fine-tuned inference - `scripts/05_infer.py`, `prism/vlm.py`
- Base 4-bit + `PeftModel(best_adapter)`, greedy decoding, left padding, batch 2 (T4),
  `max_new_tokens 768` for P4 (256 for others); CUDA OOM -> falls back to batch 1 for that batch.
- Appends each row to `predictions/finetuned_qlora_test.jsonl` (resumable).
- Writes `reports/release_report_finetuned_qlora.xlsx` (per sample: 12 scores, categories, overall, rank).

## [8] Validation gate - `prism/validation.py`
1. Take balanced `{…}` spans, last first.
2. Clean: single -> double quotes, drop trailing commas; `json.loads`.
3. Map key aliases (`ocr_accuracy`, `OCR Accuracy`, `ocraccuracy` …) to the 12 canonical keys.
4. Each value numeric and in [0, 1]; all 12 present -> accept; else error codes.
5. On failure: **one retry** with a strict JSON-only prompt (256 tokens); still failing -> invalid, logged.

## [9] Python score engine - `prism/scoring.py`
- category = mean of its 4 metrics; overall = weighted mean of categories (weights 1/1/1).
- ranking: sort by (−overall, −technical, release id); best = first.
- Identical code for ground truth and predictions.

## [10] Evaluation + diagnostic audit - `scripts/06_evaluate.py`, `prism/evaluation.py`, `prism/report.py`
- **Regression** (per metric / category / overall / template): MAE, RMSE, PLCC, SROCC, bias,
  accuracy within ±0.05 / ±0.10 / ±0.15.
- **Bands**: excellent ≥ 0.90, good 0.75-0.90, fair 0.50-0.75, poor < 0.50 -> accuracy + macro-F1.
- **Ranking**: best-release accuracy, exact R1/R2/R3 order, Kendall τ, pairwise preference accuracy.
- **Coverage**: valid-output rate after the gate.
- **Audit**: top errors (|error| > 0.30), failure patterns, error by severity.
- **No manual annotation**: all ground truth comes from the renderer's measurements.
- Outputs: `reports/evaluation_report.md`, `evaluation_metrics.xlsx`, figures, ranking CSVs.

---

## [11] Judge any image pair - `scripts/07_judge.py`, `prism/judge.py`
`python scripts/07_judge.py --original a.png --release b.png` (or `--pairs pairs.csv`): the fine-tuned model
scores the pair, then deterministic Python returns **ACCEPT / REJECT** (any metric < `evaluation.gate_threshold`),
the failing metrics with the model's own observation (what and where) and a **repair action** per metric
(`prism/judge.py FIXES`). Domain-agnostic: translated or AI-edited documents, re-typeset scans, UI screenshots
across builds/languages, tamper screening. 06_evaluate.py reports the same gate on the test split:
decision accuracy, reject precision/recall, false-reject rate and **diagnosis accuracy** (right metric blamed).

## [12] Self-improving data engine - `scripts/08_data_engine.py`
Reads the ladder analysis of a model, finds the edit families it still misses at level 1, generates new
ladder Originals containing only those families (`data/metadata/ladder_engine.jsonl`) and 02_build_splits.py
adds them to training. Retrain -> re-evaluate -> repeat: each round targets the model's current blind spots.

## Explanation check (in 06_evaluate.py)
For ladder releases the model's analysis line for the edited metric is compared with the ground-truth line:
**location accuracy** (same top/middle/bottom-left/right phrase) and **quantity accuracy** (same px / %
within 25 % or 1 unit). It measures whether the written reason is true, not only whether the score is close.

## Execution (Kaggle, free T4) - `kaggle/`
| Session | Runs | Inputs attached |
|---|---|---|
| `prism-vlm-datagen` (CPU) | stages 1-2 | code dataset |
| `prism-vlm-train` (GPU) | stage 6 | code + datagen output |
| `prism-vlm-baseline` (GPU) | stages 4-5 | code + datagen output |
| `prism-vlm-finish` (GPU) | stages 7-10 | code + datagen + baseline + train outputs |

- One GPU session at a time (free tier); each stage in its own session so memory is not shared.
- T4 overrides: `max_pixels 501760`, `inference.batch_size 2`, `train.epochs 2`, `prompt_study_n 30`.
- Each session stops itself at 10.5 h so its output is always saved; state lives in
  `/kaggle/working/state` and is merged into the next session.
