"""Generate Figure S10: five-year net survival by ICESCR ratification, 2x2 panel.

Reuses box_panel() and the plotting style from 11_figures_tufte.py so that the
ICESCR panel matches the constitutional-right panel (Figure 2) and the other
binary-indicator panels (Figures S6, S7). The unratified group is very small
(three countries for the primary outcome, two for the rarer histologies), so the
panel is uninformative and is provided only for completeness alongside Table S7.

Usage:
    python code/09_figure_icescr.py \
        --analytic data/processed/analytic_dataset.csv \
        --supp_dir figures/supplementary
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import pandas as pd


def _load_figure_module():
    path = Path(__file__).with_name("11_figures_tufte.py")
    spec = importlib.util.spec_from_file_location("figtufte", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--analytic", required=True, type=Path)
    ap.add_argument("--supp_dir", required=True, type=Path)
    args = ap.parse_args()

    mod = _load_figure_module()
    df = pd.read_csv(args.analytic)
    df["concord_flag_less_reliable"] = pd.to_numeric(
        df["concord_flag_less_reliable"], errors="coerce")
    for c in ("brain_adult_5yr_pct", "glioblastoma_5yr_pct",
              "diffuse_anap_astro_5yr", "oligodendroglioma_5yr"):
        df[c] = pd.to_numeric(df[c], errors="coerce")

    out_dfs = {}
    for outcome_id, _label, ycol in mod.OUTCOMES:
        d = df.dropna(subset=[ycol]).copy()
        d = d.loc[d["concord_flag_less_reliable"] != 1]
        out_dfs[outcome_id] = d

    mod.box_panel(out_dfs, "icescr_ratified",
                  ("ICESCR\nnot ratified", "ICESCR\nratified"),
                  args.supp_dir, "figS10_icescr_ratification_panel")
    print("figS10_icescr_ratification_panel written to", args.supp_dir)


if __name__ == "__main__":
    main()
