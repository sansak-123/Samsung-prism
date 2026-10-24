# Samsung PRISM 26VI05 - VLM image-quality evaluation pipeline (English)

End-to-end pipeline: **dataset with pre-defined ground-truth scores -> pairwise JSONL -> zero-shot
benchmark -> QLoRA fine-tuning -> CoT inference -> validation gate -> Python score engine ->
agreement analytics -> diagnostic audit.**

## How to run
- **With Claude Code (local GPU):** open this folder in Claude Code and say
  *"Follow CLAUDE.md and run the whole pipeline."* It handles setup, fixes and the final report.
- **Manually:** see the numbered steps in `CLAUDE.md`, or `./run_all.sh`.
- **Google Colab:** upload this zip to Drive, open `colab_run_pipeline.ipynb`, choose a GPU runtime, Run all.

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

**23 English templates:** invoice, receipt, certificate, application form, business letter,
restaurant menu, event flyer, mobile settings screen, bank statement, payslip, boarding pass, medical
prescription, resume, newsletter, nutrition label, ID card, shipping label, report card, utility bill,
email, web landing page, chat screenshot, presentation slide (incl. dark-mode and landscape variants) - all randomised (names, items, prices, colours,
fonts from 11 bundled open-licence families, paper texture, logos, stamps, QR codes, signatures, photos).
Drop your own photos into `assets/photos/` and the flyer/menu/form photo areas will use them.

### Metadata
- `data/metadata/samples.jsonl` - one record per sample: template, seed, original path, `ocr_data`
  (line text + bounding boxes), and per release: image path, `target_scores`, ground-truth `scores`,
  `category_scores`, `control_parameters` (exact physical changes), `reasoning`, `ocr_data_release`,
  `ground_truth_source: "predefined"`, plus `gt_ranking` / `gt_best_release`.
- `data/metadata/metadata.csv` - one row per Original-Release pair (opens in Excel).
- `data/pairs/{train,val,test}.jsonl` - pairwise training records (Original + one release + CoT/JSON target),
  split 70/15/15 **by sample_id** (no leakage), stratified by template.
- **Minute-change ladder** (`prism/ladder.py`): per ladder Original 1 unchanged control + 52 releases =
  13 single-factor edit families x 4 minute levels. The first 6 families are the prism_iqa "24 generation"
  (font family, font size x1.01-1.10, font colour +2-20, inpaint colour 1-12, justification 1-8 px, line
  spacing +1-8 px); 7 more (look-alike characters, ghost text, grain smoothing, soft shadow, local JPEG,
  object shift, heading shift) give 11 of the 12 metrics their own ladder. Scores are measured during
  generation, each with its written-out formula; `scripts/check_ladder_scores.py` re-computes all of them.
  Output also in the `metadata_real.json` schema (`data/metadata/metadata_ladder.json`).
- `pilot/` - **5 images per artifact type** (each changes one metric only) with contact sheets in
  `pilot/sheets/` and `pilot_metadata.json` - a visual sanity check of each artifact type.

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

## What makes PRISM different
1. **It measures the smallest change a VLM can see.** Each of 13 defect types comes in 4 minute levels, so
   the evaluation reports a just-noticeable level per defect, instead of hiding blindness inside an average
   (a model blind to every change below 0.05 still gets a pooled MAE of ~0.009).
2. **Ground truth with zero manual annotation that anyone can audit.** Every score is computed from what was
   drawn (dE2000, pixels, % of characters) and ships with its formula; one script re-computes all of them and
   cross-checks the pixels.
3. **It knows WHAT is wrong and WHERE, and whether its explanation is true.** Training targets name the
   region; the evaluation scores location and quantity in the model's own explanation.
4. **It does not confuse defects.** Single-factor edits give an edit x metric leakage matrix and an
   attribution-precision score - impossible with mixed-defect datasets.
5. **It acts, not just grades.** `07_judge.py` returns ACCEPT/REJECT, the failing metric, the region and the
   repair action for any original/edited pair; the evaluation reports gate accuracy and diagnosis accuracy.
6. **It improves itself.** `08_data_engine.py` generates new training data only for the defects the model
   still misses, round after round.
7. **It generalises and scales.** 23 document/UI types with an unseen-template test option; the same code
   runs a 3B model on a free T4 (fp16) or a 7B/32B model on bigger GPUs (config presets).
8. **Sanity built in.** Unchanged controls measure false alarms; ordering across levels measures consistency.

## No manual annotation
Every ground-truth score is computed automatically by the renderer during generation (stage 1) and
used directly for training and evaluation. There is no annotation sheet, rater step or human-label input.

## Layout
```
configs/config.yaml        all settings
prism/                     library (templates, renderer, metrics, prompts, gate, scoring, evaluation, report, vlm)
scripts/00..08             stages (07 judge any pair, 08 data engine); gpu_smoke_test.py;
                           make_pilot_showcase.py; check_ladder_scores.py
assets/fonts               bundled open-licence fonts (DejaVu, Liberation, Carlito, Caladea, Poppins, FreeFont)
```
