"""Tufte-style figures for revision-20260430.

Figure design rules:
  - No in-figure titles. Every label that belongs to the legend goes to the
    legend, not to the panel.
  - Statistical results (Pearson r, Spearman rho, p, n) are reported in the
    figure legend in the manuscript, not as on-panel text.
  - Sans-serif font throughout.
  - Tufte-inspired economy: only the lower and left spines, in light grey;
    no grid; minimal axis ticks; small markers; soft colour palette.
  - Selective country labelling: only the three highest, three lowest and
    the four geographic anchors USA, GBR, DEU, JPN are labelled, with
    leader lines from adjustText.
  - Binary boxplot x-axis labels are spelled out unambiguously.

Output: PNG (300 dpi) + SVG. The script writes to whichever directory the
caller specifies.

Files produced (and their canonical mapping in the manuscript):
  fig1_forest_indicator_outcome_correlations.{png,svg}
       Forest plot of Pearson r and bootstrap 95% CI for each continuous
       indicator x each of the four outcomes. Cited as Figure 1.
  fig2_constitutional_right_panel.{png,svg}
       2x2 panel of box plots of survival by binary constitutional
       recognition of the right to health, one panel per outcome. Cited as
       Figure 2.

Supplementary figures (a curated subset; not the full 56-panel grid):
  figS1_morphine_consumption_brain_all.{png,svg}
  figS2_gdp_per_capita_brain_all.{png,svg}
  figS3_che_per_capita_brain_all.{png,svg}
  figS4_radiotherapy_density_brain_all.{png,svg}
  figS5_oop_pct_che_brain_all.{png,svg}
  figS6_iaea_threshold_panel.{png,svg}
  figS7_oral_morphine_panel.{png,svg}
  figS8_pairwise_correlation_heatmap.{png,svg}
  figS9_vif_bar.{png,svg}
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from adjustText import adjust_text


# ---------------------------------------------------------------------------
# Tufte-style rcParams. Sans-serif, light spines, no top/right.
# ---------------------------------------------------------------------------
TUFTE_RCPARAMS = {
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial"],
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": True,
    "axes.spines.bottom": True,
    "axes.edgecolor": "#555555",
    "axes.linewidth": 0.6,
    "xtick.color": "#444444",
    "ytick.color": "#444444",
    "xtick.major.size": 3,
    "ytick.major.size": 3,
    "xtick.major.width": 0.5,
    "ytick.major.width": 0.5,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "axes.grid": False,
    "figure.dpi": 110,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.10,
    "savefig.facecolor": "white",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
}
plt.rcParams.update(TUFTE_RCPARAMS)


CONTINUOUS = [
    ("Out-of-pocket expenditure (% CHE)",                "oop_pct_che"),
    ("Government health expenditure (% CHE)",            "gov_pct_che"),
    ("Current health expenditure (% GDP)",               "che_pct_gdp"),
    ("Current health expenditure per capita (PPP USD)",  "che_pc_ppp_usd"),
    ("Nurses and midwives per 1000 population",          "nurses_per_1000"),
    ("Physicians per 1000 population",                   "physicians_per_1000"),
    ("GDP per capita (PPP USD)",                         "gdp_pc_ppp_usd"),
    ("Life expectancy at birth (years)",                 "life_expectancy"),
    ("Radiotherapy units per million population",        "radiotherapy_units_per_million"),
    ("Morphine consumption (mg/capita/year)",            "morphine_consumption_mg_per_capita"),
]

OUTCOMES = [
    ("brain_all",     "Adult primary brain tumours",                "brain_adult_5yr_pct"),
    ("glioblastoma",  "Glioblastoma",                                "glioblastoma_5yr_pct"),
    ("diffuse_anap",  "Diffuse and anaplastic astrocytoma",         "diffuse_anap_astro_5yr"),
    ("oligo",         "Oligodendroglioma",                           "oligodendroglioma_5yr"),
]


# Anchor countries to always label in scatters
ANCHOR_LABELS = {"USA", "GBR", "DEU", "JPN", "BRA", "CHN", "IND", "RUS"}


def save_fig(fig: plt.Figure, out_dir: Path, stem: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(out_dir / f"{stem}.{ext}")
    plt.close(fig)


def _select_labels(iso_codes, x, y, n_extreme: int = 3) -> set[str]:
    """Label only the n_extreme highest and lowest by y, plus the anchors."""
    if len(y) == 0:
        return set()
    df = pd.DataFrame({"iso": iso_codes, "x": x, "y": y})
    extreme = set(df.nlargest(n_extreme, "y")["iso"]) | set(df.nsmallest(n_extreme, "y")["iso"])
    anchors = ANCHOR_LABELS & set(iso_codes)
    return extreme | anchors


def scatter_clean(df_sub: pd.DataFrame, xcol: str, ycol: str,
                  xlabel: str, ylabel: str,
                  out_dir: Path, stem: str) -> None:
    sub = df_sub[[xcol, ycol, "iso3"]].copy()
    sub[xcol] = pd.to_numeric(sub[xcol], errors="coerce")
    sub[ycol] = pd.to_numeric(sub[ycol], errors="coerce")
    sub = sub.dropna()
    if len(sub) < 4:
        return
    x = sub[xcol].to_numpy(); y = sub[ycol].to_numpy()
    iso = sub["iso3"].to_numpy()
    fig, ax = plt.subplots(figsize=(4.6, 3.6))
    ax.scatter(x, y, s=18, color="#3a6f8f", alpha=0.85,
               edgecolors="white", linewidths=0.5, zorder=3)
    # Linear fit
    if len(np.unique(x)) > 1:
        m, b = np.polyfit(x, y, 1)
        xx = np.linspace(np.nanmin(x), np.nanmax(x), 30)
        ax.plot(xx, m*xx + b, color="#888888", linewidth=1.0,
                 alpha=0.7, zorder=2)
    # Selective country labels
    label_set = _select_labels(iso, x, y, n_extreme=3)
    texts = []
    for xi, yi, code in zip(x, y, iso):
        if code in label_set:
            texts.append(ax.text(xi, yi, code, fontsize=7,
                                 color="#333333", zorder=4))
    if texts:
        adjust_text(texts, ax=ax,
                    arrowprops=dict(arrowstyle="-", color="#aaaaaa",
                                    lw=0.4, alpha=0.6),
                    expand_points=(1.5, 1.6),
                    expand_text=(1.2, 1.4),
                    only_move={"text": "xy"},
                    force_points=0.6, force_text=0.6)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    save_fig(fig, out_dir, stem)


def box_panel(df_outcomes: dict[str, pd.DataFrame], xcol: str,
              labels: tuple[str, str], out_dir: Path, stem: str,
              ylabel_prefix: str = "5-year net survival (%)") -> None:
    """2x2 panel of box plots for one binary indicator across 4 outcomes.

    df_outcomes: dict of outcome_id -> dataframe with [xcol, ycol, iso3].
    Each panel shows the distribution by the two levels of xcol.
    """
    fig, axes = plt.subplots(2, 2, figsize=(7.0, 6.4), sharex=True)
    axes_flat = axes.flatten()
    for ax, (outcome_id, label, ycol) in zip(axes_flat, OUTCOMES):
        sub = df_outcomes[outcome_id][[xcol, ycol]].copy()
        sub[xcol] = pd.to_numeric(sub[xcol], errors="coerce")
        sub[ycol] = pd.to_numeric(sub[ycol], errors="coerce")
        sub = sub.dropna()
        groups = [sub.loc[sub[xcol] == v, ycol].values for v in (0, 1)]
        counts = [len(g) for g in groups]
        if min(counts) == 0:
            ax.set_visible(False); continue
        bp = ax.boxplot(groups, widths=0.45, patch_artist=True,
                        medianprops=dict(color="#222222", linewidth=1.0),
                        whiskerprops=dict(linewidth=0.6, color="#444444"),
                        capprops=dict(linewidth=0.6, color="#444444"),
                        flierprops=dict(marker="", markersize=0))
        # Tufte: pale unfilled boxes, just show structure
        for patch in bp["boxes"]:
            patch.set_facecolor("#dfe7ec")
            patch.set_edgecolor("#3a6f8f")
            patch.set_linewidth(0.7)
        rng = np.random.default_rng(0)
        for i, g in enumerate(groups):
            if len(g) == 0: continue
            xj = i + 1 + rng.normal(0, 0.04, size=len(g))
            ax.scatter(xj, g, s=10, color="#444444", alpha=0.6, zorder=3)
        ax.set_xticks([1, 2])
        ax.set_xticklabels([f"{labels[0]}\n(n={counts[0]})",
                            f"{labels[1]}\n(n={counts[1]})"],
                           fontsize=8)
        ax.set_ylabel(f"{ylabel_prefix}\n{label}", fontsize=8)
    fig.subplots_adjust(hspace=0.35, wspace=0.30)
    save_fig(fig, out_dir, stem)


def forest_plot(corr_by_outcome: dict[str, pd.DataFrame],
                out_dir: Path, stem: str) -> None:
    """Forest plot: rows = continuous indicators, columns = outcomes.

    Each row shows Pearson r with 95% bootstrap CI for the four outcomes,
    side by side with a small offset, colour-coded by outcome.
    """
    indicator_labels = [label for label, _ in CONTINUOUS]
    indicator_cols = [col for _, col in CONTINUOUS]
    n_ind = len(indicator_labels)

    fig, ax = plt.subplots(figsize=(7.0, 5.5))
    outcome_colors = {
        "brain_all":     "#3a6f8f",
        "glioblastoma":  "#8e3a4f",
        "diffuse_anap":  "#6f7a3a",
        "oligo":         "#3a6f4f",
    }
    outcome_labels = {oid: lbl for oid, lbl, _ in OUTCOMES}
    offsets = {"brain_all": 0.30, "glioblastoma": 0.10,
               "diffuse_anap": -0.10, "oligo": -0.30}
    y_positions = np.arange(n_ind)[::-1]  # top to bottom
    for outcome_id in offsets:
        df_o = corr_by_outcome[outcome_id].set_index("indicator")
        for j, ind_label in enumerate(indicator_labels):
            if ind_label not in df_o.index:
                continue
            row = df_o.loc[ind_label]
            r = float(row["pearson_r"])
            lo = float(row["pearson_lo"]); hi = float(row["pearson_hi"])
            yy = y_positions[j] + offsets[outcome_id]
            ax.errorbar(r, yy, xerr=[[r - lo], [hi - r]],
                        fmt="o", markersize=3.5,
                        color=outcome_colors[outcome_id],
                        ecolor=outcome_colors[outcome_id],
                        elinewidth=0.7, capsize=0, alpha=0.9)
    ax.axvline(0, color="#888888", linewidth=0.5, linestyle="--")
    ax.set_yticks(y_positions)
    ax.set_yticklabels(indicator_labels, fontsize=8)
    ax.set_xlabel("Pearson correlation with 5-year net survival (95% CI)")
    ax.set_xlim(-0.7, 0.7)
    # Outcome legend placed below the panel to avoid overlap with data
    handles = [plt.Line2D([0], [0], marker="o", color="w",
                          markerfacecolor=outcome_colors[oid],
                          markeredgecolor=outcome_colors[oid],
                          markersize=5, label=outcome_labels[oid])
               for oid in ("brain_all", "glioblastoma",
                           "diffuse_anap", "oligo")]
    ax.legend(handles=handles, loc="upper center",
              bbox_to_anchor=(0.5, -0.12), ncol=4,
              frameon=False, fontsize=8)
    fig.subplots_adjust(bottom=0.15)
    save_fig(fig, out_dir, stem)


def heatmap_pairwise(df: pd.DataFrame, out_dir: Path, stem: str) -> None:
    cols = [c for _, c in CONTINUOUS]
    sub = df[cols].apply(pd.to_numeric, errors="coerce").dropna()
    corr = sub.corr(method="pearson")
    labels = [name for name, _ in CONTINUOUS]
    fig, ax = plt.subplots(figsize=(6.4, 5.6))
    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7.5)
    ax.set_yticklabels(labels, fontsize=7.5)
    cbar = plt.colorbar(im, ax=ax, shrink=0.7)
    cbar.ax.tick_params(labelsize=7)
    cbar.set_label("Pearson r", fontsize=8)
    save_fig(fig, out_dir, stem)


def vif_bar(coll_csv: Path, out_dir: Path, stem: str) -> None:
    coll = pd.read_csv(coll_csv)
    label_map = {col: lbl for lbl, col in CONTINUOUS}
    coll["label"] = coll["indicator"].map(label_map).fillna(coll["indicator"])
    coll = coll.sort_values("VIF")
    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    ax.barh(coll["label"], coll["VIF"], color="#3a6f8f", alpha=0.8)
    ax.axvline(5, color="#aaaaaa", linewidth=0.5, linestyle="--")
    ax.axvline(10, color="#aaaaaa", linewidth=0.5, linestyle="--")
    ax.set_xlabel("Variance inflation factor (10-variable design matrix)")
    ax.set_yticklabels(coll["label"], fontsize=7.5)
    save_fig(fig, out_dir, stem)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--analytic", required=True, type=Path)
    ap.add_argument("--results_dir", required=True, type=Path)
    ap.add_argument("--main_dir", required=True, type=Path)
    ap.add_argument("--supp_dir", required=True, type=Path)
    args = ap.parse_args()

    df = pd.read_csv(args.analytic)
    df["concord_flag_less_reliable"] = pd.to_numeric(
        df["concord_flag_less_reliable"], errors="coerce")
    for c in ("brain_adult_5yr_pct", "glioblastoma_5yr_pct",
              "diffuse_anap_astro_5yr", "oligodendroglioma_5yr"):
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Per-outcome filtered frames (primary set: drop CONCORD-flagged less reliable)
    out_dfs = {}
    for outcome_id, _, ycol in OUTCOMES:
        d = df.dropna(subset=[ycol]).copy()
        d = d.loc[d["concord_flag_less_reliable"] != 1]
        out_dfs[outcome_id] = d

    # Correlation tables for forest plot
    corr_by_outcome = {}
    for outcome_id, _, _ in OUTCOMES:
        corr_by_outcome[outcome_id] = pd.read_csv(
            args.results_dir / f"correlation_results__{outcome_id}.csv")

    # ------------------------------------------------------------------
    # Main figures
    # ------------------------------------------------------------------
    forest_plot(corr_by_outcome, args.main_dir,
                "fig1_forest_indicator_outcome_correlations")
    box_panel(out_dfs, "right_to_health_in_constitution",
              ("Right to health\nnot in constitution",
               "Right to health\nin constitution"),
              args.main_dir, "fig2_constitutional_right_panel")

    # ------------------------------------------------------------------
    # Supplementary figures (curated)
    # ------------------------------------------------------------------
    db = out_dfs["brain_all"]
    scatter_clean(db, "morphine_consumption_mg_per_capita", "brain_adult_5yr_pct",
                  "Morphine consumption (mg/capita/year)",
                  "5-year net survival (%): adult primary brain tumours",
                  args.supp_dir, "figS1_morphine_consumption_brain_all")
    scatter_clean(db, "gdp_pc_ppp_usd", "brain_adult_5yr_pct",
                  "GDP per capita (PPP USD)",
                  "5-year net survival (%): adult primary brain tumours",
                  args.supp_dir, "figS2_gdp_per_capita_brain_all")
    scatter_clean(db, "che_pc_ppp_usd", "brain_adult_5yr_pct",
                  "Current health expenditure per capita (PPP USD)",
                  "5-year net survival (%): adult primary brain tumours",
                  args.supp_dir, "figS3_che_per_capita_brain_all")
    scatter_clean(db, "radiotherapy_units_per_million", "brain_adult_5yr_pct",
                  "Radiotherapy units per million population",
                  "5-year net survival (%): adult primary brain tumours",
                  args.supp_dir, "figS4_radiotherapy_density_brain_all")
    scatter_clean(db, "oop_pct_che", "brain_adult_5yr_pct",
                  "Out-of-pocket expenditure (% current health expenditure)",
                  "5-year net survival (%): adult primary brain tumours",
                  args.supp_dir, "figS5_oop_pct_che_brain_all")

    box_panel(out_dfs, "radiotherapy_meets_iaea",
              ("Below\nIAEA threshold", "At or above\nIAEA threshold"),
              args.supp_dir, "figS6_iaea_threshold_panel")
    box_panel(out_dfs, "oral_morphine_available_2013",
              ("Oral morphine\nnot available", "Oral morphine\navailable"),
              args.supp_dir, "figS7_oral_morphine_panel")
    heatmap_pairwise(out_dfs["brain_all"], args.supp_dir,
                     "figS8_pairwise_correlation_heatmap")
    vif_bar(args.results_dir / "collinearity.csv", args.supp_dir,
            "figS9_vif_bar")
    print("Done")


if __name__ == "__main__":
    main()
