# Curated indicator file: data/raw/curated_indicators.csv

The four indicators below cannot be retrieved automatically through a single open API and
are therefore provided as a curated CSV with explicit source attribution per cell.

| Field | Definition | Reference period | Primary source |
|-------|------------|------------------|----------------|
| `radiotherapy_units_per_million` | Number of operational megavoltage external-beam radiotherapy units per million population. | 2012-2014 (closest available) | International Atomic Energy Agency Directory of Radiotherapy Centres (DIRAC) snapshot used in Atun R et al. *Lancet Oncol* 2015;16:1153-86 (table 1) and IAEA *Radiotherapy in Cancer Care: Facing the Global Challenge*, 2017. |
| `radiotherapy_meets_iaea_threshold` | Binary: 1 if the country has at least one radiotherapy unit per 500,000 population (the IAEA-AGaRT operational threshold), 0 otherwise. | 2012-2014 | Derived from the column above. |
| `morphine_consumption_mg_per_capita` | Annual licit consumption of morphine in mg per person, expressed as the mean defined daily dose for statistical purposes (S-DDD). | 2010-2013 mean | International Narcotics Control Board *Narcotic Drugs Estimated World Requirements* statistical report (annual). Pain & Policy Studies Group / WHO Collaborating Center mirrors. |
| `right_to_health_in_constitution` | Binary: 1 if the right to health (or to medical care, or to highest attainable standard of physical and mental health) is recognised in the national Constitution as a justiciable individual right; 0 otherwise. | 2007-2013 (legal status stable across this window for almost all states) | Heymann J et al. *Glob Public Health* 2013;8:639-53; Kavanagh MM et al. *Health Hum Rights* 2018;20:75; Backman G et al. *Lancet* 2008;372:2047-85 appendix. |
| `icescr_ratified` | Binary: 1 if the State has ratified the International Covenant on Economic, Social and Cultural Rights, 0 if signed only or not signed. | as of 31 Dec 2014 | UN Treaty Collection (https://treaties.un.org). |

The CSV is hand-coded from the cited sources. Where two sources conflict, the IAEA DIRAC
or UN Treaty Collection (as primary registries) take precedence over secondary literature
syntheses. All cell-level provenance is logged in the `provenance` column of the CSV.
