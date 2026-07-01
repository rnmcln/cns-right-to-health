# Summary of findings

## Question

Country-level right-to-health and health-system indicators, derived from
availability, accessibility, acceptability and quality (AAAQ) domains, are
increasingly used to evaluate whether health systems deliver equitable
cancer outcomes. We tested whether such indicators explain population-
based five-year net survival from adult brain tumours, a disease in which
no validated screening modality exists, glioblastoma forms a major
component of malignant primary brain tumour mortality, and survival
depends on neurosurgical access, radiotherapy access, neuropathology and
histomolecular classification.

## Design

Cross-national ecological analysis. Country is the unit of analysis. The
primary outcome was age-standardised five-year net survival from adult
primary brain tumours (ICD-O-3 topography C71, malignant or nonmalignant)
for patients diagnosed in 2010-14, from CONCORD-3. Three histology-
resolved secondary outcomes (glioblastoma; diffuse and anaplastic
astrocytoma; oligodendroglioma) were taken from the CONCORD-3 brain
analysis. Exposures were 14 indicators (10 continuous, 4 binary) covering
AAAQ domains plus a macroeconomic confounder (GDP per capita PPP) and one
contextual covariate (life expectancy at birth). Up to 68 countries
contributed at least one indicator; 43 entered the primary analysis after
exclusion of CONCORD-3 less reliable estimates.

## Statistical analysis

Pearson and Spearman correlations with bootstrap percentile 95% confidence
intervals (2000 resamples; deterministic seed 20260426). Benjamini-Hochberg
false-discovery-rate correction applied (i) within outcome (10 continuous
tests per outcome) and (ii) as a conservative full-family correction over
all 96 reported bivariate tests across the four outcomes. Univariate-plus-
GDP ordinary least-squares regression with HC3 heteroscedasticity-robust
standard errors. Variance inflation factors as exploratory diagnostics of
collinearity in the indicator set. Sensitivity analysis on the high-
quality CONCORD subset (countries with 100% national population coverage
and no reliability flags; n=27).

## Headline finding

No association survived false-discovery-rate correction across the full
bivariate test family (smallest q = 0.59); within-outcome corrected q-
values were also above 0.30 for every continuous indicator. Estimated
correlations were small to moderate and uniformly imprecise; the largest
were morphine consumption (Pearson r = +0.28, 95% CI +0.01 to +0.53), GDP
per capita (+0.26, -0.03 to +0.54) and current health expenditure per
capita (+0.23, -0.12 to +0.53). After adjustment for log-GDP per capita
PPP, no indicator retained an independent association.

## Interpretation

Three independent claims, supported by the present analysis but not
mutually entailed:

1. Generic country-level macro-indicators have limited disease-specific
   resolution. Macroeconomic and health-financing indicators are highly
   collinear with each other and with national wealth; after adjustment
   for GDP per capita PPP, none retained an independent association with
   survival.

2. Brain tumour survival estimates are vulnerable to classification and
   registry artefact. International heterogeneity in coding (proportion
   unspecified-histology 4.2% to 65.2%; survival from unspecified tumours
   7% to 82%) introduces measurement error that may dominate any
   indicator-survival signal.

3. Pathway-level neuro-oncology indicators are required to operationalise
   right-to-health measurement in this disease area. Time to imaging and
   neurosurgical resection, completeness of molecular diagnosis, fidelity
   of evidence-based chemoradiation, and neuro-palliative care
   integration are not currently collected in a harmonised way across
   countries; this is itself a right-to-health measurement gap.

## What this is not

- It is not a definitive test of the right-to-health framework. The study
  was underpowered to rule out moderate associations.
- It is not a treatment-effectiveness analysis. The outcome is population-
  based net survival, which combines incidence-mix, registration practice
  and treatment delivery.

## Where to start

- Headline correlations: `results/correlation_results__brain_all.csv`.
- Cross-outcome FDR control: `results/family_wide_fdr.csv`.
- Country-level analytic table: `data/processed/analytic_dataset.csv`.
- Main figures (2): `figures/main/`.
- Supplementary figures (9 panels): `figures/supplementary/`.
- Companion tables file: `results/tables.docx`.
