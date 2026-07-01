# cns-right-to-health

Reproducibility package for an ecological analysis of country-level right-
to-health and health-system indicators against five-year net survival from
adult brain tumours, using CONCORD-3 data.

This repository contains the data, analysis code, results and figures.
The manuscript itself is not included here.

## What is in this repository

```
.
|-- README.md                        # this file
|-- SUMMARY.md                       # one-page summary of the findings
|-- LICENSE                          # MIT (code) and CC BY 4.0 (data)
|-- requirements.txt                 # Python dependencies
|-- code/
|   |-- 01_extract_concord3_brain_survival.py
|   |-- 01b_extract_girardi_histology_survival.py
|   |-- 02_build_country_master.py
|   |-- 03_fetch_worldbank_indicators.py
|   |-- 03b_fetch_who_gho_indicators.py
|   |-- 04_merge_analytic_dataset.py
|   |-- 05b_analysis_revised.py
|   |-- 05c_sensitivity_region_income.py   # income/region sensitivity analysis
|   |-- 06_figures.py                # legacy per-outcome exploratory scatter/box set
|   |-- 07_word_tables.py
|   |-- 08_manuscript.py             # (kept for reproducibility; not run here)
|   |-- 09_figure_icescr.py          # supplementary ICESCR panel (Figure S10)
|   `-- 11_figures_tufte.py          # main + supplementary manuscript figures (Fig 1, 2, S1-S10)
|-- data/
|   |-- raw/                         # curated indicator file + provenance
|   `-- processed/                   # CSV inputs used by the analysis
|-- results/
|   |-- correlation_results__{outcome}.csv
|   |-- regression_results__{outcome}.csv
|   |-- binary_indicator_summary__{outcome}.csv
|   |-- sensitivity_high_quality__{outcome}.csv
|   |-- sensitivity_income_hic__{outcome}.csv        # high-income subset correlations
|   |-- sensitivity_region_eur__{outcome}.csv        # WHO European Region subset correlations
|   |-- sensitivity_income_adjusted_regression__brain_all.csv
|   |-- family_wide_fdr.csv
|   |-- country_flow.csv
|   |-- country_flow_detailed.csv    # per-country inclusion/exclusion record
|   |-- collinearity.csv
|   `-- tables.docx                  # publication-ready tables
`-- figures/
    |-- main/                        # 2 figures cited in the main paper
    `-- supplementary/               # 10 supplementary panels
```

Figures cited in the manuscript (main Figures 1-2 and supplementary Figures
S1-S10) are produced by `11_figures_tufte.py` and `09_figure_icescr.py`.
`06_figures.py` is a legacy exploratory generator that produces a larger,
per-outcome scatter/box set and is retained for completeness.

## Reproducing the analysis

```bash
pip install -r requirements.txt

# 01 + 01b: extract CONCORD-3 survival from open-access PDFs (obtain from
# the publisher and place in data/raw/ before running)
python code/01_extract_concord3_brain_survival.py \
    --pdf data/raw/concord3_main.pdf \
    --out data/processed/concord3_brain_adult_survival_2010_14.csv
python code/01b_extract_girardi_histology_survival.py \
    --pdf data/raw/concord3_brain_supp_table_3a.pdf \
    --out data/processed/girardi_histology_5yr_2010_14.csv

# 02: ISO3 + region/income mapping
python code/02_build_country_master.py \
    --survival_csv data/processed/concord3_brain_adult_survival_2010_14.csv \
    --out_csv data/processed/country_master.csv \
    --out_log data/processed/exclusions.md

# 03 + 03b: fetch open-API indicators
python code/03_fetch_worldbank_indicators.py \
    --country_master data/processed/country_master.csv \
    --out_csv data/processed/worldbank_indicators.csv
python code/03b_fetch_who_gho_indicators.py \
    --country_master data/processed/country_master.csv \
    --out_csv data/processed/who_gho_indicators.csv

# 04: merge into the analytic dataset
python code/04_merge_analytic_dataset.py \
    --country_master data/processed/country_master.csv \
    --worldbank data/processed/worldbank_indicators.csv \
    --who_gho data/processed/who_gho_indicators.csv \
    --girardi data/processed/girardi_histology_5yr_2010_14.csv \
    --curated data/raw/curated_indicators.csv \
    --out_csv data/processed/analytic_dataset.csv

# 05b: main analysis pipeline
python code/05b_analysis_revised.py \
    --analytic data/processed/analytic_dataset.csv \
    --out_dir results/

# 05c: income / region sensitivity analysis
python code/05c_sensitivity_region_income.py \
    data/processed/analytic_dataset.csv \
    results/

# 11: manuscript figures (Fig 1, Fig 2, Fig S1-S9)
python code/11_figures_tufte.py \
    --analytic data/processed/analytic_dataset.csv \
    --results_dir results/ \
    --main_dir figures/main \
    --supp_dir figures/supplementary

# 09: supplementary ICESCR panel (Fig S10)
python code/09_figure_icescr.py \
    --analytic data/processed/analytic_dataset.csv \
    --supp_dir figures/supplementary

# 07: companion tables file
python code/07_word_tables.py \
    --results_dir results/ \
    --analytic data/processed/analytic_dataset.csv \
    --out_docx results/tables.docx
```

The pipeline is deterministic given the bootstrap seed (20260426).

## Data sources

- CONCORD-3 (Allemani C, Matsuda T, Di Carlo V, et al. *Lancet* 2018,
  doi:10.1016/S0140-6736(17)33326-3) for the all-adult-brain primary
  outcome.
- CONCORD-3 brain (Girardi F, Matz M, Stiller C, et al. *Neuro-Oncology*
  2023, doi:10.1093/neuonc/noac217) for the histology-resolved secondary
  outcomes.
- World Bank Open Data API (https://api.worldbank.org/v2/) for health
  expenditure, workforce, GDP per capita PPP and life expectancy.
- WHO Global Health Observatory (https://ghoapi.azureedge.net/api/) for
  the IAEA DIRAC radiotherapy density and the WHO NCD Country Capacity
  Survey 2013 oral morphine availability indicator.
- INCB *Narcotic Drugs: Estimated World Requirements for 2015 - Statistics
  for 2013* (https://www.incb.org/) for continuous morphine consumption.
- Backman G, Hunt P, Khosla R, et al. *Lancet* 2008,
  doi:10.1016/S0140-6736(08)61781-X (supplementary list) for
  constitutional recognition of the right to health.
- UN Treaty Collection (https://treaties.un.org/) for ICESCR ratification.

## Licence

Code: MIT. Data and curated indicator file: CC BY 4.0, with original
sources retaining their respective licences. World Bank Open Data is
CC BY 4.0. CONCORD-3 survival values are extracted from open-access
publications and are reproduced under fair use; please cite the original
papers.
