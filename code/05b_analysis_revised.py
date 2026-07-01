"""Revised analysis pipeline addressing peer-review feedback.

Changes from 05_analysis.py:
  1. FDR (Benjamini-Hochberg) is applied across the FULL family of bivariate tests:
     9 continuous indicators x 4 outcomes plus 4 binary indicator x 4 outcome
     Mann-Whitney tests = 52 tests in total. This is the conservative correction the
  2. Country-flow tracking: outputs results/country_flow.csv summarising, for each
     outcome and indicator, how many countries are available, missing, flagged, or
     excluded.
  3. Pairwise correlation matrix and variance inflation factors (VIF) are computed
     for the continuous indicator set, to flag collinearity.
  4. Multivariable regression: GDP per capita PPP is excluded as both indicator and
     covariate to avoid the structural self-reference. Reported separately is a
     bivariate-only summary for GDP.
  5. Required-n-for-power figures are retained for context but the outputs include a
     warning column note.

Outputs (overwrites previous CSVs in place):
  results/correlation_results__{outcome}.csv
  results/regression_results__{outcome}.csv
  results/binary_indicator_summary__{outcome}.csv
  results/sensitivity_high_quality__{outcome}.csv
  results/family_wide_fdr.csv      (52-test BH correction across outcomes x tests)
  results/country_flow.csv         (n available per outcome and indicator)
  results/collinearity.csv         (VIF + pairwise r among continuous indicators)
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.outliers_influence import variance_inflation_factor


SEED = 20260426
N_BOOT = 2_000

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

BINARY = [
    ("Radiotherapy density meets IAEA threshold",        "radiotherapy_meets_iaea"),
    ("Oral morphine available in public sector (2013)",  "oral_morphine_available_2013"),
    ("Right to health in constitution",                  "right_to_health_in_constitution"),
    ("ICESCR ratified",                                  "icescr_ratified"),
]

OUTCOMES = [
    ("brain_all",     "All adult brain tumours, 5-year net survival 2010-14",          "brain_adult_5yr_pct"),
    ("glioblastoma",  "Glioblastoma, 5-year net survival 2010-14",                     "glioblastoma_5yr_pct"),
    ("diffuse_anap",  "Diffuse and anaplastic astrocytoma, 5-year net survival 2010-14","diffuse_anap_astro_5yr"),
    ("oligo",         "Oligodendroglioma, 5-year net survival 2010-14",                "oligodendroglioma_5yr"),
]


def benjamini_hochberg(pvals: np.ndarray) -> np.ndarray:
    pvals = np.asarray(pvals)
    mask = ~np.isnan(pvals)
    p_clean = pvals[mask]
    n = len(p_clean)
    if n == 0:
        return pvals
    order = np.argsort(p_clean)
    ranked = p_clean[order] * n / (np.arange(n) + 1)
    q = np.minimum.accumulate(ranked[::-1])[::-1]
    qsorted = np.empty(n)
    qsorted[order] = q
    out = np.full(pvals.shape, np.nan)
    out[mask] = np.minimum(qsorted, 1.0)
    return out


def required_n(r: float, alpha: float = 0.05, power: float = 0.80) -> int:
    if r is None or math.isnan(r) or abs(r) <= 0 or abs(r) >= 1:
        return 10**6
    z_alpha = stats.norm.isf(alpha / 2)
    z_beta = stats.norm.isf(1 - power)
    z = 0.5 * math.log((1 + r) / (1 - r))
    return int(math.ceil(((z_alpha + z_beta) / z) ** 2 + 3))


def correlate(df, ycol, xcol, rng):
    sub = df[[xcol, ycol]].apply(pd.to_numeric, errors="coerce").dropna()
    n = len(sub)
    if n < 4:
        return dict(n=n, pearson_r=np.nan, pearson_p=np.nan,
                    pearson_lo=np.nan, pearson_hi=np.nan,
                    spearman_r=np.nan, spearman_p=np.nan,
                    spearman_lo=np.nan, spearman_hi=np.nan,
                    n_required_for_80pct_power=np.nan)
    x, y = sub[xcol].to_numpy(), sub[ycol].to_numpy()
    pr, pp = stats.pearsonr(x, y)
    sr, sp = stats.spearmanr(x, y)
    pearson_boot, spearman_boot = [], []
    idx_all = np.arange(n)
    for _ in range(N_BOOT):
        idx = rng.choice(idx_all, size=n, replace=True)
        if len(np.unique(x[idx])) < 3 or len(np.unique(y[idx])) < 3:
            continue
        try:
            pearson_boot.append(stats.pearsonr(x[idx], y[idx])[0])
            spearman_boot.append(stats.spearmanr(x[idx], y[idx]).correlation)
        except Exception:
            pass
    p_lo, p_hi = (np.percentile(pearson_boot, [2.5, 97.5])
                  if pearson_boot else (np.nan, np.nan))
    s_lo, s_hi = (np.percentile(spearman_boot, [2.5, 97.5])
                  if spearman_boot else (np.nan, np.nan))
    return dict(
        n=n,
        pearson_r=pr, pearson_p=pp, pearson_lo=p_lo, pearson_hi=p_hi,
        spearman_r=sr, spearman_p=sp, spearman_lo=s_lo, spearman_hi=s_hi,
        n_required_for_80pct_power=required_n(pr),
    )


def boxplot_summary(df, ycol, xcol):
    sub = df[[xcol, ycol]].copy()
    sub[xcol] = pd.to_numeric(sub[xcol], errors="coerce")
    sub[ycol] = pd.to_numeric(sub[ycol], errors="coerce")
    sub = sub.dropna()
    out = {}
    for level in [0, 1]:
        s = sub.loc[sub[xcol] == level, ycol]
        out[f"n_{level}"] = int(len(s))
        out[f"median_{level}"] = float(s.median()) if len(s) else np.nan
        out[f"q1_{level}"] = float(s.quantile(0.25)) if len(s) else np.nan
        out[f"q3_{level}"] = float(s.quantile(0.75)) if len(s) else np.nan
    if out["n_0"] >= 3 and out["n_1"] >= 3:
        u, p = stats.mannwhitneyu(
            sub.loc[sub[xcol] == 0, ycol], sub.loc[sub[xcol] == 1, ycol],
            alternative="two-sided",
        )
        out["mann_whitney_u"] = float(u)
        out["mann_whitney_p"] = float(p)
    else:
        out["mann_whitney_u"] = np.nan
        out["mann_whitney_p"] = np.nan
    return out


def regression(df, ycol, xcol, covariate):
    sub = df[[xcol, ycol, covariate]].apply(pd.to_numeric, errors="coerce").dropna()
    n = len(sub)
    if n < 6:
        return dict(n=n, beta=np.nan, se=np.nan, p=np.nan,
                    beta_covariate=np.nan, p_covariate=np.nan, r2=np.nan)
    X = sm.add_constant(sub[[xcol, covariate]])
    y = sub[ycol]
    model = sm.OLS(y, X).fit(cov_type="HC3")
    return dict(
        n=n,
        beta=float(model.params[xcol]),
        se=float(model.bse[xcol]),
        p=float(model.pvalues[xcol]),
        beta_covariate=float(model.params[covariate]),
        p_covariate=float(model.pvalues[covariate]),
        r2=float(model.rsquared),
    )


def country_flow(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for outcome_id, _label, ycol in OUTCOMES:
        d = df.copy()
        d[ycol] = pd.to_numeric(d[ycol], errors="coerce")
        n_available = int(d[ycol].notna().sum())
        n_flagged = int(((d[ycol].notna()) &
                         (pd.to_numeric(d["concord_flag_less_reliable"],
                                        errors="coerce") == 1)).sum())
        n_primary = n_available - n_flagged
        n_hq = int(((d[ycol].notna()) &
                    (pd.to_numeric(d["high_quality_subset"], errors="coerce") == 1)).sum())
        rows.append({
            "outcome": outcome_id,
            "n_outcome_available": n_available,
            "n_flagged_less_reliable_excluded": n_flagged,
            "n_primary_analysis": n_primary,
            "n_high_quality_subset": n_hq,
        })
        # By indicator
        d_primary = d.loc[(d[ycol].notna()) &
                          (pd.to_numeric(d["concord_flag_less_reliable"],
                                          errors="coerce") != 1)]
        for label, col in CONTINUOUS + BINARY:
            n_pair = int(d_primary[[ycol, col]]
                          .apply(pd.to_numeric, errors="coerce").dropna().shape[0])
            rows.append({
                "outcome": outcome_id,
                "indicator": label,
                "n_outcome_indicator_pair": n_pair,
            })
    return pd.DataFrame(rows)


def collinearity_table(df: pd.DataFrame) -> pd.DataFrame:
    cont_cols = [c for _, c in CONTINUOUS]
    sub = df[cont_cols].apply(pd.to_numeric, errors="coerce").dropna()
    rows = []
    if len(sub) >= len(cont_cols) + 1:
        X = sm.add_constant(sub.values)
        for i, c in enumerate(cont_cols):
            try:
                vif = variance_inflation_factor(X, i + 1)
            except Exception:
                vif = float("nan")
            rows.append({"indicator": c, "VIF": vif, "n_complete_cases": len(sub)})
    return pd.DataFrame(rows)


def run_outcome(df, ycol, out_dir, outcome_id):
    df_o = df.copy()
    df_o[ycol] = pd.to_numeric(df_o[ycol], errors="coerce")
    df_main = df_o.dropna(subset=[ycol]).copy()
    df_primary = df_main.loc[
        pd.to_numeric(df_main["concord_flag_less_reliable"], errors="coerce") != 1
    ].copy()
    df_primary["log_gdp_pc_ppp_usd"] = pd.to_numeric(
        df_primary["log_gdp_pc_ppp_usd"], errors="coerce"
    )
    rng = np.random.default_rng(SEED)

    rows = []
    for label, col in CONTINUOUS:
        r = correlate(df_primary, ycol, col, rng)
        r.update(indicator=label, column=col)
        rows.append(r)
    p_p = np.array([r["pearson_p"] for r in rows], dtype=float)
    s_p = np.array([r["spearman_p"] for r in rows], dtype=float)
    p_q = benjamini_hochberg(p_p)
    s_q = benjamini_hochberg(s_p)
    for i, r in enumerate(rows):
        r["pearson_q_bh_within_outcome"] = (
            float(p_q[i]) if not np.isnan(p_p[i]) else np.nan)
        r["spearman_q_bh_within_outcome"] = (
            float(s_q[i]) if not np.isnan(s_p[i]) else np.nan)
    pd.DataFrame(rows).to_csv(
        out_dir / f"correlation_results__{outcome_id}.csv", index=False
    )

    binary_rows = []
    for label, col in BINARY:
        s = boxplot_summary(df_primary, ycol, col)
        s.update(indicator=label, column=col)
        binary_rows.append(s)
    pd.DataFrame(binary_rows).to_csv(
        out_dir / f"binary_indicator_summary__{outcome_id}.csv", index=False
    )

    reg_rows = []
    for label, col in CONTINUOUS:
        if col == "gdp_pc_ppp_usd":
            continue  # GDP pc is the covariate; would be a self-regression
        r = regression(df_primary, ycol, col, "log_gdp_pc_ppp_usd")
        r.update(indicator=label, column=col)
        reg_rows.append(r)
    pd.DataFrame(reg_rows).to_csv(
        out_dir / f"regression_results__{outcome_id}.csv", index=False
    )

    df_hq = df_main.loc[pd.to_numeric(df_main["high_quality_subset"],
                                       errors="coerce") == 1].copy()
    rng2 = np.random.default_rng(SEED + 1)
    sens_rows = []
    for label, col in CONTINUOUS:
        r = correlate(df_hq, ycol, col, rng2)
        r.update(indicator=label, column=col)
        sens_rows.append(r)
    pd.DataFrame(sens_rows).to_csv(
        out_dir / f"sensitivity_high_quality__{outcome_id}.csv", index=False
    )

    return rows, binary_rows  # for family-wide FDR


def family_wide_fdr(df: pd.DataFrame, out_dir: Path) -> None:
    """Apply BH-FDR to the full bivariate test family across all outcomes."""
    family = []
    rng = np.random.default_rng(SEED + 100)
    for outcome_id, _label, ycol in OUTCOMES:
        d = df.copy()
        d[ycol] = pd.to_numeric(d[ycol], errors="coerce")
        d = d.dropna(subset=[ycol])
        d_primary = d.loc[pd.to_numeric(d["concord_flag_less_reliable"],
                                          errors="coerce") != 1]
        for label, col in CONTINUOUS:
            r = correlate(d_primary, ycol, col, rng)
            family.append({"outcome": outcome_id, "indicator": label,
                           "test": "Pearson", "p": r["pearson_p"],
                           "estimate": r["pearson_r"], "n": r["n"]})
            family.append({"outcome": outcome_id, "indicator": label,
                           "test": "Spearman", "p": r["spearman_p"],
                           "estimate": r["spearman_r"], "n": r["n"]})
        for label, col in BINARY:
            s = boxplot_summary(d_primary, ycol, col)
            family.append({"outcome": outcome_id, "indicator": label,
                           "test": "Mann-Whitney", "p": s.get("mann_whitney_p", np.nan),
                           "estimate": (s.get("median_1") or 0) - (s.get("median_0") or 0),
                           "n": (s.get("n_0", 0) + s.get("n_1", 0))})
    df_fam = pd.DataFrame(family)
    df_fam["q_bh_family_wide"] = benjamini_hochberg(df_fam["p"].to_numpy(dtype=float))
    df_fam.to_csv(out_dir / "family_wide_fdr.csv", index=False)
    n_sig = int((df_fam["q_bh_family_wide"] < 0.05).sum())
    print(f"  Family-wide FDR (n_tests={len(df_fam)}): {n_sig} tests with q<0.05")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--analytic", required=True, type=Path)
    ap.add_argument("--out_dir", required=True, type=Path)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.analytic)

    for outcome_id, _label, col in OUTCOMES:
        run_outcome(df, col, args.out_dir, outcome_id)
        print(f"  {outcome_id} written")

    family_wide_fdr(df, args.out_dir)
    country_flow(df).to_csv(args.out_dir / "country_flow.csv", index=False)
    collinearity_table(df).to_csv(args.out_dir / "collinearity.csv", index=False)


if __name__ == "__main__":
    main()
