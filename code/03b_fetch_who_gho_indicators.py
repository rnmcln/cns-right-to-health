"""Fetch radiotherapy and oral morphine availability from the WHO Global Health Observatory.

The WHO GHO OData API exposes:

  DEVICES22         Total density per million population: Radiotherapy units. Annual
                    snapshots 2010, 2013, 2014, 2021. Source: IAEA DIRAC, harmonised by
                    WHO. https://www.who.int/data/gho/indicator-metadata-registry/imr-details/2486

  NCD_CCS_OralMorph General availability of oral morphine in the public health sector
                    (Yes / No / NR). Survey years: 2013, 2015, 2017, 2019, 2021.
                    Source: WHO NCD Country Capacity Survey.

For our analytic period (patients diagnosed 2010-14) we take:
  - Radiotherapy density: 2013 value if present else 2014 else 2010, after age-
    standardisation per the WHO methodology.
  - Oral morphine availability: 2013 survey value, since this is the earliest survey
    that overlaps the survival window.

Both indicators replace earlier curated values whose provenance was a literature recall
rather than a direct API pull.
"""
from __future__ import annotations

import argparse
import csv
import json
import urllib.request
from pathlib import Path


WHO_GHO = "https://ghoapi.azureedge.net/api/{ind}"


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "cns-rth-research/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_devices22() -> dict[str, tuple[float, int]]:
    """Return iso3 -> (radiotherapy units per million, year)."""
    data = _get_json(WHO_GHO.format(ind="DEVICES22"))
    out: dict[str, tuple[float, int]] = {}
    for r in data.get("value", []):
        iso = r.get("SpatialDim")
        year = r.get("TimeDim")
        val = r.get("NumericValue")
        if not iso or year is None or val is None:
            continue
        if year not in (2010, 2013, 2014):
            continue
        prev = out.get(iso)
        # Prefer 2013, then 2014, then 2010
        priority = {2013: 0, 2014: 1, 2010: 2}
        if prev is None or priority[year] < priority[prev[1]]:
            out[iso] = (float(val), year)
    return out


def fetch_oral_morphine() -> dict[str, tuple[str, int]]:
    """Return iso3 -> (Yes/No string, year). 2013 survey preferred."""
    data = _get_json(WHO_GHO.format(ind="NCD_CCS_OralMorph"))
    out: dict[str, tuple[str, int]] = {}
    for r in data.get("value", []):
        iso = r.get("SpatialDim")
        year = r.get("TimeDim")
        val = r.get("Value")
        if not iso or year is None or val is None:
            continue
        if year != 2013:
            continue
        out[iso] = (str(val), year)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--country_master", required=True, type=Path)
    ap.add_argument("--out_csv", required=True, type=Path)
    args = ap.parse_args()

    isos = [r["iso3"] for r in csv.DictReader(args.country_master.open())]

    rt = fetch_devices22()
    morph = fetch_oral_morphine()

    rows = []
    for iso in isos:
        rt_val, rt_year = rt.get(iso, (None, None))
        morph_val, morph_year = morph.get(iso, (None, None))
        rows.append({
            "iso3": iso,
            "who_radiotherapy_units_per_million": rt_val if rt_val is not None else "",
            "who_radiotherapy_year": rt_year if rt_year is not None else "",
            "who_oral_morphine_available": (
                "1" if morph_val == "Yes" else ("0" if morph_val == "No" else "")
            ),
            "who_oral_morphine_year": morph_year if morph_year is not None else "",
        })

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    n_rt = sum(1 for r in rows if r["who_radiotherapy_units_per_million"])
    n_morph = sum(1 for r in rows if r["who_oral_morphine_available"])
    print(f"Wrote {len(rows)} rows; RT density {n_rt}/{len(rows)}, "
          f"oral morphine {n_morph}/{len(rows)} to {args.out_csv}")


if __name__ == "__main__":
    main()
