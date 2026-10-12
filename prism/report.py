"""Writes the evaluation outputs: Excel workbook, Markdown report, figures, release-ranking CSVs."""

from __future__ import annotations

import json
import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .metrics import CATEGORIES, CATEGORY_NAMES, METRIC_KEYS, METRIC_NAMES, QUALITY_BANDS, band_of  # noqa: E402

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]   # validated categorical order (fixed, never cycled)
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
KEY = ["MAE", "RMSE", "PLCC", "SROCC", "acc@0.05", "acc@0.10", "acc@0.15", "band_acc", "band_macro_F1", "bias", "n"]


def _fmt(v, d=3):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "n/a"
    return f"{v:.{d}f}" if isinstance(v, float) else str(v)


def _style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _plot_mae(results, path):
    names = list(results)
    labels = [METRIC_NAMES[k] for k in METRIC_KEYS] + [CATEGORY_NAMES[c] for c in CATEGORIES] + ["Overall"]
    fig, ax = plt.subplots(figsize=(9, 7), facecolor=SURFACE)
    _style(ax)
    h = 0.8 / len(names)
    y = np.arange(len(labels))
    for i, n in enumerate(names):
        r = results[n]
        vals = [r["per_metric"][k]["MAE"] for k in METRIC_KEYS] + [r["per_category"][c]["MAE"] for c in CATEGORIES + ["overall"]]
        ax.barh(y + i * h - 0.4 + h / 2, vals, height=h * 0.85, color=SERIES[i % len(SERIES)], label=n)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, color=INK)
    ax.invert_yaxis()
    ax.set_xlabel("Mean absolute error (lower is better)", color=INK2)
    ax.set_title("MAE vs pre-defined ground truth, test split", color=INK, loc="left", fontsize=12)
    ax.legend(frameon=False, labelcolor=INK)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _plot_scatter(rows, name, path):
    fig, axes = plt.subplots(3, 4, figsize=(12, 9), facecolor=SURFACE)
    for ax, k in zip(axes.ravel(), METRIC_KEYS):
        _style(ax)
        ax.grid(color=GRID, linewidth=0.6)
        g = [r["gt"][k] for r in rows if r.get("pred")]
        p = [r["pred"][k] for r in rows if r.get("pred")]
        ax.plot([0, 1], [0, 1], color=INK2, linewidth=1, linestyle="--")
        ax.scatter(g, p, s=10, color=SERIES[0], alpha=0.55, linewidths=0)
        ax.set_xlim(-0.02, 1.02)
        ax.set_ylim(-0.02, 1.02)
        ax.set_title(METRIC_NAMES[k], fontsize=10, color=INK, loc="left")
    fig.supxlabel("Ground truth (pre-defined)", color=INK2)
    fig.supylabel(f"Predicted ({name})", color=INK2)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def _plot_band_confusion(rows, name, path):
    bands = [b[0] for b in QUALITY_BANDS]
    m = np.zeros((4, 4))
    for r in rows:
        if r.get("pred"):
            for k in METRIC_KEYS:
                m[bands.index(band_of(r["gt"][k])), bands.index(band_of(r["pred"][k]))] += 1
    norm = m / np.maximum(m.sum(1, keepdims=True), 1)
    fig, ax = plt.subplots(figsize=(5.5, 4.6), facecolor=SURFACE)
    ax.imshow(norm, cmap="Blues", vmin=0, vmax=1)
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f"{norm[i, j]:.0%}\n({int(m[i, j])})", ha="center", va="center", fontsize=8,
                    color="white" if norm[i, j] > 0.55 else INK)
    ax.set_xticks(range(4))
    ax.set_xticklabels(bands)
    ax.set_yticks(range(4))
    ax.set_yticklabels(bands)
    ax.set_xlabel("Predicted band", color=INK2)
    ax.set_ylabel("Ground-truth band", color=INK2)
    ax.set_title(f"Quality-band confusion ({name}), all metrics", color=INK, fontsize=11, loc="left")
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def write_report(results: dict, rows_by_model: dict, out_dir: str, title: str = "PRISM VLM evaluation",
                 extra: dict | None = None, human: dict | None = None):
    os.makedirs(out_dir, exist_ok=True)
    fig_dir = os.path.join(out_dir, "figures")
    os.makedirs(fig_dir, exist_ok=True)
    names = list(results)

    # ---------------- Excel
    summary, per_metric, per_cat, per_tpl, rank, pref, sev = [], [], [], [], [], [], []
    for n, r in results.items():
        o, pooled, rk = r["per_category"]["overall"], r["all_metrics_pooled"], r["ranking"]
        summary.append({"model": n, "valid_output_rate": r["coverage"]["valid_rate"], "n_pairs": r["coverage"]["n_total"],
                        "MAE_all_metrics": pooled["MAE"], "RMSE_all_metrics": pooled["RMSE"],
                        "PLCC_all_metrics": pooled["PLCC"], "SROCC_all_metrics": pooled["SROCC"],
                        "acc@0.10_all_metrics": pooled["acc@0.10"], "band_acc_all_metrics": pooled["band_acc"],
                        "MAE_overall_score": o["MAE"], "PLCC_overall_score": o["PLCC"], "SROCC_overall_score": o["SROCC"],
                        "best_release_accuracy": rk["best_release_accuracy_RSA"],
                        "exact_ranking_accuracy": rk["exact_ranking_accuracy"], "mean_kendall_tau": rk["mean_kendall_tau"]})
        for k in METRIC_KEYS:
            per_metric.append({"model": n, "metric": METRIC_NAMES[k], **{c: r["per_metric"][k].get(c) for c in KEY}})
            pref.append({"model": n, "metric": METRIC_NAMES[k], "pairwise_preference_accuracy": rk["pairwise_preference_accuracy"][k]})
            for b, v in r["error_by_severity"][k].items():
                sev.append({"model": n, "metric": METRIC_NAMES[k], "gt_bucket": b, "n": v["n"], "MAE": v["MAE"]})
        pref.append({"model": n, "metric": "Overall", "pairwise_preference_accuracy": rk["pairwise_preference_accuracy"]["overall"]})
        for c in CATEGORIES + ["overall"]:
            per_cat.append({"model": n, "category": CATEGORY_NAMES.get(c, "Overall"), **{x: r["per_category"][c].get(x) for x in KEY}})
        for t, v in r["per_template_overall"].items():
            per_tpl.append({"model": n, "template": t, **{x: v.get(x) for x in KEY}})
        rank.append({"model": n, **{k: v for k, v in rk.items() if k != "pairwise_preference_accuracy"}})
    xlsx = os.path.join(out_dir, "evaluation_metrics.xlsx")
    with pd.ExcelWriter(xlsx) as xw:
        pd.DataFrame(summary).to_excel(xw, sheet_name="summary", index=False)
        pd.DataFrame(per_metric).to_excel(xw, sheet_name="per_metric", index=False)
        pd.DataFrame(per_cat).to_excel(xw, sheet_name="per_category", index=False)
        pd.DataFrame(per_tpl).to_excel(xw, sheet_name="per_template", index=False)
        pd.DataFrame(rank).to_excel(xw, sheet_name="ranking", index=False)
        pd.DataFrame(pref).to_excel(xw, sheet_name="pairwise_preference", index=False)
        pd.DataFrame(sev).to_excel(xw, sheet_name="error_by_severity", index=False)
        for n, r in results.items():
            short = n[:18]
            pd.DataFrame(r["failure_patterns"]).to_excel(xw, sheet_name=f"patterns_{short}"[:31], index=False)
            pd.DataFrame(r["top_errors"][:500]).to_excel(xw, sheet_name=f"top_err_{short}"[:31], index=False)
            pd.DataFrame(r["ranking_rows"]).to_excel(xw, sheet_name=f"rank_{short}"[:31], index=False)
        if human:
            pd.DataFrame([{"metric": METRIC_NAMES[k], **v} for k, v in human.items()]).to_excel(xw, sheet_name="human_ceiling", index=False)
    for n, r in results.items():
        pd.DataFrame(r["ranking_rows"]).to_csv(os.path.join(out_dir, f"release_rankings_{n}.csv"), index=False)

    # ---------------- figures
    _plot_mae(results, os.path.join(fig_dir, "mae_per_metric.png"))
    for n in names:
        _plot_scatter(rows_by_model[n], n, os.path.join(fig_dir, f"scatter_{n}.png"))
        _plot_band_confusion(rows_by_model[n], n, os.path.join(fig_dir, f"band_confusion_{n}.png"))

    # ---------------- Markdown
    L = [f"# {title}", ""]
    if extra:
        for k, v in extra.items():
            L.append(f"- **{k}:** {v}")
        L.append("")
    L += ["## Headline accuracy (test split)", "",
          "| Measure | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    rowsdef = [
        ("Valid-output rate (validation gate)", lambda r: r["coverage"]["valid_rate"]),
        ("MAE, all 12 metrics pooled", lambda r: r["all_metrics_pooled"]["MAE"]),
        ("RMSE, all 12 metrics pooled", lambda r: r["all_metrics_pooled"]["RMSE"]),
        ("PLCC, all 12 metrics pooled", lambda r: r["all_metrics_pooled"]["PLCC"]),
        ("SROCC, all 12 metrics pooled", lambda r: r["all_metrics_pooled"]["SROCC"]),
        ("Within +-0.05", lambda r: r["all_metrics_pooled"]["acc@0.05"]),
        ("Within +-0.10", lambda r: r["all_metrics_pooled"]["acc@0.10"]),
        ("Within +-0.15", lambda r: r["all_metrics_pooled"]["acc@0.15"]),
        ("Quality-band accuracy", lambda r: r["all_metrics_pooled"]["band_acc"]),
        ("Quality-band macro-F1", lambda r: r["all_metrics_pooled"]["band_macro_F1"]),
        ("Overall-score MAE", lambda r: r["per_category"]["overall"]["MAE"]),
        ("Overall-score SROCC", lambda r: r["per_category"]["overall"]["SROCC"]),
        ("Best-release accuracy (RSA)", lambda r: r["ranking"]["best_release_accuracy_RSA"]),
        ("Exact R1/R2/R3 ranking accuracy", lambda r: r["ranking"]["exact_ranking_accuracy"]),
        ("Mean Kendall tau (ranking)", lambda r: r["ranking"]["mean_kendall_tau"]),
    ]
    for label, fn in rowsdef:
        L.append(f"| {label} | " + " | ".join(_fmt(fn(results[n])) for n in names) + " |")
    if len(names) >= 2:
        a, b = names[0], names[-1]
        d = results[a]["all_metrics_pooled"]["MAE"] - results[b]["all_metrics_pooled"]["MAE"]
        L += ["", f"Pooled MAE changes by **{-d:+.3f}** from `{a}` to `{b}` "
                  f"({'improvement' if d > 0 else 'no improvement'})."]
    for n in names:
        r = results[n]
        L += ["", f"## Per-metric accuracy - {n}", "",
              "| Metric | MAE | RMSE | PLCC | SROCC | +-0.10 | Band acc | Bias | Pairwise pref. acc |",
              "|---|---|---|---|---|---|---|---|---|"]
        for k in METRIC_KEYS:
            m = r["per_metric"][k]
            L.append(f"| {METRIC_NAMES[k]} | {_fmt(m.get('MAE'))} | {_fmt(m.get('RMSE'))} | {_fmt(m.get('PLCC'))} | "
                     f"{_fmt(m.get('SROCC'))} | {_fmt(m.get('acc@0.10'))} | {_fmt(m.get('band_acc'))} | {_fmt(m.get('bias'))} | "
                     f"{_fmt(r['ranking']['pairwise_preference_accuracy'][k])} |")
        L += ["", "| Category | MAE | RMSE | PLCC | SROCC |", "|---|---|---|---|---|"]
        for c in CATEGORIES + ["overall"]:
            m = r["per_category"][c]
            L.append(f"| {CATEGORY_NAMES.get(c, 'Overall')} | {_fmt(m.get('MAE'))} | {_fmt(m.get('RMSE'))} | "
                     f"{_fmt(m.get('PLCC'))} | {_fmt(m.get('SROCC'))} |")
        L += ["", f"### Diagnostic audit - {n}", "",
              f"{len(r['top_errors'])} metric predictions have |error| > 0.30 "
              f"({len(r['top_errors']) / max(1, len(r['error_rows'])):.1%} of all).", ""]
        if r["failure_patterns"]:
            L += ["| Metric | Template | Count | Direction |", "|---|---|---|---|"]
            for p in r["failure_patterns"][:10]:
                L.append(f"| {METRIC_NAMES[p['metric']]} | {p['template']} | {p['n']} | {p['direction']} |")
        L += ["", "MAE by ground-truth severity bucket (does the model see *minute* changes?):", "",
              "| Metric | untouched | minute | moderate | strong |", "|---|---|---|---|---|"]
        for k in METRIC_KEYS:
            v = list(r["error_by_severity"][k].values())
            L.append(f"| {METRIC_NAMES[k]} | " + " | ".join(_fmt(x["MAE"]) for x in v) + " |")
    if human:
        L += ["", "## Human-ceiling check (pilot annotations vs pre-defined scores)", "",
              "| Metric | Human sigma | Human ceiling error | Human vs pre-defined MAE |", "|---|---|---|---|"]
        for k in METRIC_KEYS:
            h = human[k]
            L.append(f"| {METRIC_NAMES[k]} | {_fmt(h['mean_sigma'])} | {_fmt(h['human_ceiling_error'])} | {_fmt(h['human_vs_predefined_MAE'])} |")
        L += ["", "A metric whose model MAE is close to its human-ceiling error is limited by subjectivity, not by the model."]
    L += ["", "## Files", "", "- `evaluation_metrics.xlsx` - every table above plus top errors and per-sample rankings",
          "- `release_rankings_<model>.csv` - per sample: ground-truth vs predicted R1/R2/R3 ranking and best release",
          "- `figures/` - MAE per metric, GT-vs-prediction scatter per metric, quality-band confusion"]
    with open(os.path.join(out_dir, "evaluation_report.md"), "w") as f:
        f.write("\n".join(L) + "\n")
    with open(os.path.join(out_dir, "evaluation_results.json"), "w") as f:
        json.dump({n: {k: v for k, v in r.items() if k not in ("error_rows",)} for n, r in results.items()}, f, indent=1, default=str)
    return os.path.join(out_dir, "evaluation_report.md")
