"""Merge survival, World Bank, WHO GHO, Girardi histology, and curated indicators.

Outputs data/processed/analytic_dataset.csv, one row per country, with all right-to-
health indicators and four survival outcomes:
  - brain_adult_5yr_pct       all adult brain tumours, 2010-14 (Allemani 2018, primary)
  - glioblastoma_5yr_pct      glioblastoma, 2010-14 (Girardi 2023, secondary)
  - diffuse_anap_astro_5yr    diffuse and anaplastic astrocytoma, 2010-14 (Girardi 2023)
  - oligodendroglioma_5yr     oligodendroglioma, 2010-14 (Girardi 2023)

Indicator data sources after the upgrade:
  - oop_pct_che, gov_pct_che, che_pct_gdp, che_pc_ppp_usd, nurses_per_1000,
    physicians_per_1000, gdp_pc_ppp_usd, life_expectancy: World Bank Open Data API,
    2010-13 mean.
  - radiotherapy_units_per_million: WHO Global Health Observatory indicator DEVICES22
    (IAEA DIRAC, 2013 snapshot preferred), replaces the earlier curated value.
  - oral_morphine_available_2013: WHO NCD Country Capacity Survey 2013 indicator
    NCD_CCS_OralMorph, replaces the earlier curated value.
  - right_to_health_in_constitution, icescr_ratified: still drawn from the curated CSV
    (Backman et al. 2008 Lancet supplement; UN Treaty Collection lookup as of 31 Dec
    2014). These are stable structural measures; provenance flagged in the README.
"""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


def to_float(s: str) -> float | None:
    if s is None or s == "":
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--country_master", required=True, type=Path)
    ap.add_argument("--worldbank", required=True, type=Path)
    ap.add_argument("--who_gho", required=True, type=Path)
    ap.add_argument("--girardi", required=True, type=Path)
    ap.add_argument("--curated", required=True, type=Path)
    ap.add_argument("--out_csv", required=True, type=Path)
    args = ap.parse_args()

    cm = {r["iso3"]: r for r in csv.DictReader(args.country_master.open())}
    wb = {r["iso3"]: r for r in csv.DictReader(args.worldbank.open())}
    who = {r["iso3"]: r for r in csv.DictReader(args.who_gho.open())}
    cu = {r["iso3"]: r for r in csv.DictReader(args.curated.open())}

    # Girardi mapping: country names to ISO3
    girardi_name_to_iso = {
        "Algeria": "DZA", "Argentina": "ARG", "Australia*": "AUS", "Austria*": "AUT",
        "Belgium*": "BEL", "Brazil": "BRA", "Bulgaria*": "BGR",
        "Canada": "CAN", "Chile": "CHL", "China": "CHN", "Colombia": "COL",
        "Costa Rica*": "CRI", "Croatia*": "HRV", "Cuba*": "CUB", "Cyprus*": "CYP",
        "Czech Republic*": "CZE", "Denmark*": "DNK", "Ecuador": "ECU",
        "Estonia*": "EST", "Finland*": "FIN", "France": "FRA", "Germany": "DEU",
        "Gibraltar*": "GIB", "Guadeloupe": "GLP", "Hong Kong*": "HKG",
        "Iceland*": "ISL", "India": "IND", "Iran (Golestan)": "IRN",
        "Ireland*": "IRL", "Israel*": "ISR", "Italy": "ITA", "Japan": "JPN",
        "Jordan*": "JOR", "Korea*": "KOR", "South Korea*": "KOR",
        "Kuwait*": "KWT", "Latvia*": "LVA", "Lithuania*": "LTU",
        "Malaysia (Penang)": "MYS", "Mali (Bamako)": "MLI", "Malta*": "MLT",
        "Martinique*": "MTQ", "Mauritius*": "MUS", "Mongolia*": "MNG",
        "Morocco (Casablanca)": "MAR", "Netherlands*": "NLD", "New Zealand*": "NZL",
        "Nigeria (Ibadan)": "NGA", "Norway*": "NOR", "Peru (Lima)": "PER",
        "Poland*": "POL", "Portugal": "PRT", "Puerto Rico*": "PRI", "Qatar*": "QAT",
        "Romania (Cluj)": "ROU", "Russia": "RUS", "Singapore*": "SGP",
        "Slovakia*": "SVK", "Slovenia*": "SVN", "South Africa (Eastern Cape)": "ZAF",
        "Spain": "ESP", "Sweden*": "SWE", "Switzerland": "CHE", "Taiwan*": "TWN",
        "Thailand": "THA", "Turkey": "TUR", "UK*": "GBR", "United Kingdom*": "GBR",
        "United States": "USA", "Uruguay*": "URY",
    }
    gir = {}
    with args.girardi.open() as f:
        for r in csv.DictReader(f):
            iso = girardi_name_to_iso.get(r["country"])
            if iso is None:
                continue
            gir[iso] = r

    rows: list[dict] = []
    for iso, c in cm.items():
        w = wb.get(iso, {})
        u = cu.get(iso, {})
        wh = who.get(iso, {})
        g = gir.get(iso, {})

        gdp = to_float(w.get("gdp_pc_ppp_usd", ""))
        log_gdp = math.log(gdp) if gdp and gdp > 0 else ""

        rt_who = to_float(wh.get("who_radiotherapy_units_per_million", ""))
        meets_iaea = ""
        if rt_who is not None:
            meets_iaea = 1 if rt_who >= 2.0 else 0

        national_coverage = "*" in c.get("concord_label", "")
        less_reliable = c.get("concord_flag_less_reliable") == "1"
        not_age_std = c.get("concord_flag_not_age_std") == "1"
        high_quality = 1 if (national_coverage and not less_reliable and not not_age_std) else 0

        row = {
            "iso3": iso,
            "country": c["country"],
            "concord_label": c["concord_label"],
            "who_region": c["who_region"],
            "wb_income_2014": c["wb_income_2014"],
            # Outcomes
            "brain_adult_5yr_pct": c["brain_adult_5yr_pct"],
            "glioblastoma_5yr_pct": g.get("glioblastoma", ""),
            "glioblastoma_flag": g.get("glioblastoma_flag", ""),
            "diffuse_anap_astro_5yr": g.get("diffuse_anaplastic_astrocytoma", ""),
            "oligodendroglioma_5yr": g.get("oligodendroglioma", ""),
            "concord_flag_less_reliable": c["concord_flag_less_reliable"],
            "concord_flag_not_age_std": c["concord_flag_not_age_std"],
            "high_quality_subset": high_quality,
            # World Bank
            "oop_pct_che": w.get("oop_pct_che", ""),
            "gov_pct_che": w.get("gov_pct_che", ""),
            "che_pct_gdp": w.get("che_pct_gdp", ""),
            "che_pc_ppp_usd": w.get("che_pc_ppp_usd", ""),
            "nurses_per_1000": w.get("nurses_per_1000", ""),
            "physicians_per_1000": w.get("physicians_per_1000", ""),
            "gdp_pc_ppp_usd": w.get("gdp_pc_ppp_usd", ""),
            "log_gdp_pc_ppp_usd": log_gdp,
            "life_expectancy": w.get("life_expectancy", ""),
            # WHO GHO (verified primary source)
            "radiotherapy_units_per_million": wh.get("who_radiotherapy_units_per_million", ""),
            "radiotherapy_year": wh.get("who_radiotherapy_year", ""),
            "oral_morphine_available_2013": wh.get("who_oral_morphine_available", ""),
            "radiotherapy_meets_iaea": meets_iaea,
            # Continuous morphine consumption (INCB 2014 statistical report,
            # mean of mg/capita 2010-13). This is a continuous proxy for
            # palliative-care service maturity and is used alongside the binary
            # WHO public-sector availability indicator.
            "morphine_consumption_mg_per_capita": u.get("morphine_consumption_mg_per_capita", ""),
            # Curated legal (Backman 2008 + UN Treaty Collection)
            "right_to_health_in_constitution": u.get("right_to_health_in_constitution", ""),
            "icescr_ratified": u.get("icescr_ratified", ""),
        }
        rows.append(row)

    rows.sort(key=lambda r: r["iso3"])
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    n_brain = sum(1 for r in rows if r["brain_adult_5yr_pct"])
    n_gbm = sum(1 for r in rows if r["glioblastoma_5yr_pct"])
    print(f"Wrote {len(rows)} rows; brain n={n_brain}, GBM n={n_gbm}")


if __name__ == "__main__":
    main()
