"""Build the country master file: CONCORD-3 label -> ISO3 code -> WHO/UN region.

Two outputs:
  - data/processed/country_master.csv   one row per country in the CONCORD-3 brain table
  - data/processed/exclusions.md        narrative log of dropped countries and rationale

The CONCORD-3 brain (adults) table covers some sub-national registries (e.g. China 21
registries, Russia 5 registries, US 48 registries). For the analysis we treat a registry
group as representative of the country (same convention used in Montel et al. 2026).

Pure-paediatric registries (Belarus childhood, Greece childhood, Mexico childhood) are
dropped because they contribute no adult brain data.
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


# Manual map: CONCORD-3 label -> (ISO3, country_name, who_region, world_bank_income_2014)
COUNTRY_MAP = {
    "Algeria (three registries)":      ("DZA", "Algeria",          "AFR", "UMC"),
    "Argentina (five registries)":     ("ARG", "Argentina",        "AMR", "UMC"),
    "Australia (eight registries)":    ("AUS", "Australia",        "WPR", "HIC"),
    "Austria":                         ("AUT", "Austria",          "EUR", "HIC"),
    "Belarus (childhood)":             None,
    "Belgium":                         ("BEL", "Belgium",          "EUR", "HIC"),
    "Brazil (six registries)":         ("BRA", "Brazil",           "AMR", "UMC"),
    "Bulgaria":                        ("BGR", "Bulgaria",         "EUR", "UMC"),
    "Canada (nine registries)":        ("CAN", "Canada",           "AMR", "HIC"),
    "Chile (four registries)":         ("CHL", "Chile",            "AMR", "HIC"),
    "China (21 registries)":           ("CHN", "China",            "WPR", "UMC"),
    "Colombia (four registries)":      ("COL", "Colombia",         "AMR", "UMC"),
    "Costa Rica":                      ("CRI", "Costa Rica",       "AMR", "UMC"),
    "Croatia":                         ("HRV", "Croatia",          "EUR", "HIC"),
    "Cuba":                            ("CUB", "Cuba",             "AMR", "UMC"),
    "Cyprus":                          ("CYP", "Cyprus",           "EUR", "HIC"),
    "Czech Republic":                  ("CZE", "Czechia",          "EUR", "HIC"),
    "Denmark":                         ("DNK", "Denmark",          "EUR", "HIC"),
    "Ecuador (five registries)":       ("ECU", "Ecuador",          "AMR", "UMC"),
    "Estonia":                         ("EST", "Estonia",          "EUR", "HIC"),
    "Finland":                         ("FIN", "Finland",          "EUR", "HIC"),
    "France (23 registries)":          ("FRA", "France",           "EUR", "HIC"),
    "Germany (ten registries)":        ("DEU", "Germany",          "EUR", "HIC"),
    "Gibraltar":                       ("GIB", "Gibraltar",        "EUR", "HIC"),
    "Greece (childhood)":              None,
    "Guadeloupe":                      ("GLP", "Guadeloupe",       "AMR", "HIC"),
    "Hong Kong":                       ("HKG", "Hong Kong SAR",    "WPR", "HIC"),
    "Iceland":                         ("ISL", "Iceland",          "EUR", "HIC"),
    "India (two registries)":          ("IND", "India",            "SEAR", "LMC"),
    "Iran (Golestan)":                 ("IRN", "Iran",             "EMR", "UMC"),
    "Ireland":                         ("IRL", "Ireland",          "EUR", "HIC"),
    "Israel":                          ("ISR", "Israel",           "EUR", "HIC"),
    "Italy (45 registries)":           ("ITA", "Italy",            "EUR", "HIC"),
    "Japan (16 registries)":           ("JPN", "Japan",            "WPR", "HIC"),
    "Jordan":                          ("JOR", "Jordan",           "EMR", "UMC"),
    "Korea":                           ("KOR", "South Korea",      "WPR", "HIC"),
    "Kuwait":                          ("KWT", "Kuwait",           "EMR", "HIC"),
    "Latvia":                          ("LVA", "Latvia",           "EUR", "HIC"),
    "Lithuania":                       ("LTU", "Lithuania",        "EUR", "HIC"),
    "Malaysia (Penang)":               ("MYS", "Malaysia",         "WPR", "UMC"),
    "Mali (Bamako)":                   ("MLI", "Mali",             "AFR", "LIC"),
    "Malta":                           ("MLT", "Malta",            "EUR", "HIC"),
    "Martinique":                      ("MTQ", "Martinique",       "AMR", "HIC"),
    "Mauritius":                       ("MUS", "Mauritius",        "AFR", "UMC"),
    "Mexico (childhood)":              None,
    "Mongolia":                        ("MNG", "Mongolia",         "WPR", "LMC"),
    "Morocco (Casablanca)":            ("MAR", "Morocco",          "EMR", "LMC"),
    "Netherlands":                     ("NLD", "Netherlands",      "EUR", "HIC"),
    "New Zealand":                     ("NZL", "New Zealand",      "WPR", "HIC"),
    "Nigeria (Ibadan)":                ("NGA", "Nigeria",          "AFR", "LMC"),
    "Norway":                          ("NOR", "Norway",           "EUR", "HIC"),
    "Peru (Lima)":                     ("PER", "Peru",             "AMR", "UMC"),
    "Poland (16 registries)":          ("POL", "Poland",           "EUR", "HIC"),
    "Portugal (four registries)":      ("PRT", "Portugal",         "EUR", "HIC"),
    "Puerto Rico":                     ("PRI", "Puerto Rico",      "AMR", "HIC"),
    "Qatar":                           ("QAT", "Qatar",            "EMR", "HIC"),
    "Romania (Cluj)":                  ("ROU", "Romania",          "EUR", "UMC"),
    "Russia (five registries)":        ("RUS", "Russia",           "EUR", "UMC"),
    "Singapore":                       ("SGP", "Singapore",        "WPR", "HIC"),
    "Slovakia":                        ("SVK", "Slovakia",         "EUR", "HIC"),
    "Slovenia":                        ("SVN", "Slovenia",         "EUR", "HIC"),
    "South Africa (Eastern Cape)":     ("ZAF", "South Africa",     "AFR", "UMC"),
    "Spain (ten registries)":          ("ESP", "Spain",            "EUR", "HIC"),
    "Sweden":                          ("SWE", "Sweden",           "EUR", "HIC"),
    "Switzerland (ten registries)":    ("CHE", "Switzerland",      "EUR", "HIC"),
    "Taiwan":                          ("TWN", "Taiwan",           "WPR", "HIC"),
    "Thailand (six registries)":       ("THA", "Thailand",         "SEAR", "UMC"),
    "Turkey (nine registries)":        ("TUR", "Turkiye",          "EUR", "UMC"),
    "UK (four registries)":            ("GBR", "United Kingdom",   "EUR", "HIC"),
    "Uruguay":                         ("URY", "Uruguay",          "AMR", "HIC"),
    "USA (48 registries)":             ("USA", "United States",    "AMR", "HIC"),
}


def _strip_label(s: str) -> str:
    return re.sub(r"[*\u2021]+\s*$", "", s).strip()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--survival_csv", required=True, type=Path)
    ap.add_argument("--out_csv", required=True, type=Path)
    ap.add_argument("--out_log", required=True, type=Path)
    args = ap.parse_args()

    rows_in: list[dict] = []
    with args.survival_csv.open() as f:
        for row in csv.DictReader(f):
            rows_in.append(row)

    rows_out: list[dict] = []
    excluded: list[tuple[str, str]] = []
    for r in rows_in:
        label_raw = r["country_label_concord"]
        key = _strip_label(label_raw)
        mapping = COUNTRY_MAP.get(key)
        if mapping is None:
            excluded.append((label_raw, "paediatric-only registry; no adult data"))
            continue
        iso3, name, who, inc = mapping
        rows_out.append({
            "iso3": iso3,
            "country": name,
            "concord_label": label_raw,
            "who_region": who,
            "wb_income_2014": inc,
            "brain_adult_5yr_pct": r.get("brain_adult_5yr_pct", ""),
            "concord_flag_less_reliable": "1" if "§" in (r.get("flags") or "") else "0",
            "concord_flag_not_age_std": "1" if "†" in (r.get("flags") or "") else "0",
        })

    rows_out.sort(key=lambda x: x["iso3"])
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        w.writeheader()
        for r in rows_out:
            w.writerow(r)

    with args.out_log.open("w") as f:
        f.write("# Country exclusions\n\n")
        for label, reason in excluded:
            f.write(f"- {label}: {reason}\n")
        if not excluded:
            f.write("None.\n")

    print(f"Wrote {len(rows_out)} countries to {args.out_csv}")
    print(f"Excluded {len(excluded)} (see {args.out_log})")


if __name__ == "__main__":
    main()
