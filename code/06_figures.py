"""Generate publication-quality figures for all four outcomes.

  - No in-figure title. Figure captions live in the manuscript / tables file.
  - Country labels are placed by `adjustText.adjust_text` to avoid overlap with
    each other and with data points; only the ISO3 code is plotted.
  - The statistics annotation (Pearson r, Spearman rho, n) is placed in the
    plot corner with the lowest local data density, computed per panel.
  - Coherent visual style across all panels: same axes, same dot colour,
    same fit-line colour, same font sizes.

Each figure is saved at PNG (300 dpi) and SVG to figures/{outcome_id}/.
File names follow the convention figXX_{type}_{column}.{ext} with a single
numbering sequence per outcome (1-14). The numbering corresponds to the order
in which figures are referenced in the manuscript supplement.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from adjustText import adjust_text
from scipy import stats


plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.6,
    "figure.dpi": 110,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.10,
})


# Indicator order matches Methods Table 1 in the manuscript
CONTINUOUS = [
    ("Out-of-pocket expenditure (% CHE)",                "oop_pct_che",                          "OOP % CHE"),
    ("Government health expenditure (% CHE)",            "gov_pct_che",                          "Government % CHE"),
    ("Current health expenditure (% GDP)",               "che_pct_gdp",                          "CHE % GDP"),
    ("Current health expenditure per capita (PPP USD)",  "che_pc_ppp_usd",                       "CHE per capita PPP USD"),
    ("Nurses and midwives per 1000 population",          "nurses_per_1000",                      "Nurses & midwives per 1000"),
    ("Physicians per 1000 population",                   "physicians_per_1000",                  "Physicians per 1000"),
    ("GDP per capita (PPP USD)",                         "gdp_pc_ppp_usd",                       "GDP per capita PPP USD"),
    ("Life expectancy at birth (years)",                 "life_expectancy",                      "Life expectancy at birth"),
    ("Radiotherapy units per million population",        "radiotherapy_units_per_million",       "Radiotherapy units per million"),
    ("Morphine consumption (mg/capita/year)",            "morphine_consumption_mg_per_capita",   "Morphine consumption mg/capita"),
]

BINARY = [
    ("Radiotherapy density meets IAEA threshold",        "radiotherapy_meets_iaea",
        ["Below threshold", "At or above threshold"]),
    ("Oral morphine available in public sector (2013)",  "oral_morphine_available_2013",
        ["Not available", "Available"]),
    ("Right to health in constitution",                  "right_to_health_in_constitution",
        ["Not recognised", "Recognised"]),
    ("ICESCR ratified",                                  "icescr_ratified",
        ["Not ratified", "Ratified"]),
]

OUTCOMES = [
    ("brain_all",     "5-year net survival (%)\nadult primary brain tumours",          "brain_adult_5yr_pct"),
    ("glioblastoma",  "5-year net survival (%)\nglioblastoma",                          "glioblastoma_5yr_pct"),
    ("diffuse_anap",  "5-year net survival (%)\ndiffuse and anaplastic astrocytoma",   "diffuse_anap_astro_5yr"),
    ("oligo",         "5-year net survival (%)\noligodendroglioma",                    "oligodendroglioma_5yr"),
]


def save_fig(fig: plt.Figure, out_dir: Path, stem: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(out_dir / f"{stem}.{ext}", dpi=300)
    plt.close(fig)


def plot_box(df: pd.DataFrame, ycol: str, ylabel: str, xcol: str, labels: list[str],
             out_dir: Path, stem: str) -> None:
    sub = df[[xcol, ycol]].apply(pd.to_numeric, errors="coerce").dropna()
    groups = [sub.loc[sub[xcol] == v, ycol].values for v in (0, 1)]
    counts = [len(g) for g in groups]
    if min(counts) == 0:
        return
    fig, ax = plt.subplots(figsize=(4.6, 4.4))
    bp = ax.boxplot(groups, widths=0.55, patch_artist=True,
                    medianprops=dict(color="#222"),
                    flierprops=dict(marker="o", markersize=3, alpha=0.5))
    colours = ["#9ec5d8", "#3a6f8f"]
    for patch, c in zip(bp["boxes"], colours):
        patch.set_facecolor(c); patch.set_alpha(0.85)
    rng = np.random.default_rng(0)
    for i, g in enumerate(groups):
        if len(g) == 0: continue
        x = i + 1 + rng.normal(0, 0.04, size=len(g))
        ax.scatter(x, g, s=14, color="#444", alpha=0.55, zorder=3)
    ax.set_xticks([1, 2])
    ax.set_xticklabels([f"{labels[0]}\n(n={counts[0]})",
                        f"{labels[1]}\n(n={counts[1]})"])
    ax.set_ylabel(ylabel)
    if min(counts) >= 3:
        u, p = stats.mannwhitneyu(groups[0], groups[1], alternative="two-sided")
        # Place the p-value text outside the densest part of the data:
        # use the y-axis position above the maximum data point, away from boxes.
        y_max = max(np.max(g) for g in groups if len(g))
        y_min = min(np.min(g) for g in groups if len(g))
        y_pad = (y_max - y_min) * 0.06
        ax.text(0.5, 1.02,
                f"Mann-Whitney p = {p:.3f}",
                transform=ax.transAxes, ha="center", va="bottom",
                fontsize=9, color="#333")
    save_fig(fig, out_dir, stem)


def _choose_corner(x: np.ndarray, y: np.ndarray) -> tuple[float, float, str, str]:
    """Choose plot corner with fewest data points; return (xfrac, yfrac, ha, va)."""
    if len(x) == 0:
        return 0.97, 0.97, "right", "top"
    x_lo, x_hi = np.percentile(x, [10, 90])
    y_lo, y_hi = np.percentile(y, [10, 90])
    quadrants = {
        # name : (xfrac, yfrac, ha, va, predicate)
        "TR": (0.99, 0.99, "right", "top",
               np.sum((x >= x_hi) & (y >= y_hi))),
        "TL": (0.02, 0.99, "left", "top",
               np.sum((x <= x_lo) & (y >= y_hi))),
        "BR": (0.99, 0.02, "right", "bottom",
               np.sum((x >= x_hi) & (y <= y_lo))),
        "BL": (0.02, 0.02, "left", "bottom",
               np.sum((x <= x_lo) & (y <= y_lo))),
    }
    best = min(quadrants.items(), key=lambda kv: kv[1][4])
    xfrac, yfrac, ha, va, _ = best[1]
    return xfrac, yfrac, ha, va


def plot_scatter(df: pd.DataFrame, ycol: str, ylabel: str, xcol: str, xlabel: str,
                 out_dir: Path, stem: str) -> None:
    sub = df[[xcol, ycol, "iso3"]].copy()
    sub[xcol] = pd.to_numeric(sub[xcol], errors="coerce")
    sub[ycol] = pd.to_numeric(sub[ycol], errors="coerce")
    sub = sub.dropna()
    if len(sub) < 4:
        return
    x = sub[xcol].to_numpy()
    y = sub[ycol].to_numpy()
    iso = sub["iso3"].to_numpy()
    r, p = stats.pearsonr(x, y)
    rs, ps = stats.spearmanr(x, y)

    fig, ax = plt.subplots(figsize=(5.4, 4.6))
    ax.scatter(x, y, s=26, color="#3a6f8f", alpha=0.82,
               edgecolors="white", linewidths=0.6, zorder=3)
    slope, intercept, _, _, _ = stats.linregress(x, y)
    xx = np.linspace(np.nanmin(x), np.nanmax(x), 50)
    ax.plot(xx, intercept + slope * xx, color="#cc5500",
             linewidth=1.3, alpha=0.85, zorder=2)

    # Country labels with adjustText to prevent overlap
    texts = []
    for xi, yi, code in zip(x, y, iso):
        texts.append(ax.text(xi, yi, code, fontsize=7, color="#333", zorder=4))
    adjust_text(
        texts,
        ax=ax,
        arrowprops=dict(arrowstyle="-", color="#999", lw=0.4, alpha=0.5),
        expand_points=(1.4, 1.6),
        expand_text=(1.2, 1.4),
        only_move={"points": "y", "text": "xy"},
        force_points=0.5,
        force_text=0.5,
    )

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    # Stat box in the data-sparsest corner
    xfrac, yfrac, ha, va = _choose_corner(x, y)
    stat_text = (f"Pearson r = {r:+.3f} (p = {p:.3f})\n"
                  f"Spearman rho = {rs:+.3f} (p = {ps:.3f})\n"
                  f"n = {len(sub)}")
    ax.text(xfrac, yfrac, stat_text,
             transform=ax.transAxes, ha=ha, va=va, fontsize=8,
             bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                       edgecolor="#bbb", alpha=0.92))
    save_fig(fig, out_dir, stem)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--analytic", required=True, type=Path)
    ap.add_argument("--out_dir", required=True, type=Path)
    args = ap.parse_args()

    df = pd.read_csv(args.analytic)
    df["concord_flag_less_reliable"] = pd.to_numeric(
        df["concord_flag_less_reliable"], errors="coerce")

    for outcome_id, ylabel, ycol in OUTCOMES:
        df_o = df.copy()
        df_o[ycol] = pd.to_numeric(df_o[ycol], errors="coerce")
        df_o = df_o.dropna(subset=[ycol]).copy()
        df_o = df_o.loc[df_o["concord_flag_less_reliable"] != 1].copy()
        out_dir = args.out_dir / outcome_id
        n_panel = 0
        # Numbered figures: 1-4 = binary boxplots, 5-14 = continuous scatters
        for i, (_title, col, labels) in enumerate(BINARY, start=1):
            plot_box(df_o, ycol, ylabel, col, labels, out_dir,
                     f"fig{i:02d}_box_{col}")
            n_panel += 1
        for j, (_title, col, xlabel) in enumerate(CONTINUOUS, start=len(BINARY) + 1):
            plot_scatter(df_o, ycol, ylabel, col, xlabel, out_dir,
                         f"fig{j:02d}_scatter_{col}")
            n_panel += 1
        print(f"  {outcome_id}: {n_panel} panels rendered to {out_dir}")


if __name__ == "__main__":
    main()
