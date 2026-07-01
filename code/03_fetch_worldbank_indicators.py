"""Fetch World Bank Open Data indicators for the analytic country set.

For each country and indicator we average over 2010-2013 and emit one row per (iso3,
indicator). Period choice:
  - Survival window: patients diagnosed 2010-2014 (CONCORD-3 period approach).
  - Indicator window: 2010-2013 inclusive (most contemporaneous to start of survival
    accrual; matches Montel et al.'s practice of using indicators time-aligned to
    precede or overlap the survival window).

Indicators are listed in code/INDICATORS.csv. The script handles HTTP retries and
respects the World Bank API per_page paging.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path


WB_BASE = "https://api.worldbank.org/v2"


# Country codes recognised by the World Bank API. Codes outside this set (e.g. TWN, GIB,
# GLP, MTQ for territories not in WB lending classifications, HKG handled separately)
# are skipped here and back-filled from alternative sources where possible.
WB_RECOGNISED = {
    "ARG", "AUS", "AUT", "BEL", "BRA", "BGR", "CAN", "CHL", "CHN", "COL",
    "CRI", "HRV", "CUB", "CYP", "CZE", "DNK", "ECU", "EST", "FIN", "FRA",
    "DEU", "GRC", "HKG", "ISL", "IND", "IRN", "IRL", "ISR", "ITA", "JPN",
    "JOR", "KOR", "KWT", "LVA", "LTU", "MYS", "MLI", "MLT", "MUS", "MNG",
    "MAR", "NLD", "NZL", "NGA", "NOR", "PER", "POL", "PRT", "PRI", "QAT",
    "ROU", "RUS", "SGP", "SVK", "SVN", "ZAF", "ESP", "SWE", "CHE", "THA",
    "TUR", "GBR", "URY", "USA", "DZA",
}


def _get_json(url: str, retries: int = 2, sleep: float = 1.0) -> list:
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "cns-rth-research/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(sleep * (attempt + 1))
    raise RuntimeError(f"Failed after {retries} retries: {url} - {last_err}")


def fetch_indicator(iso3: str, indicator: str,
                    year_from: int, year_to: int) -> dict[int, float]:
    url = (f"{WB_BASE}/country/{iso3}/indicator/{indicator}"
           f"?format=json&date={year_from}:{year_to}&per_page=200")
    data = _get_json(url)
    if not isinstance(data, list) or len(data) < 2 or data[1] is None:
        return {}
    out: dict[int, float] = {}
    for row in data[1]:
        v = row.get("value")
        d = row.get("date")
        if v is None or d is None:
            continue
        try:
            out[int(d)] = float(v)
        except (ValueError, TypeError):
            continue
    return out


def average(values: dict[int, float]) -> tuple[float | None, int]:
    if not values:
        return None, 0
    vs = [v for v in values.values()]
    return sum(vs) / len(vs), len(vs)


INDICATORS = [
    # World Bank code, short name, time window
    ("SH.XPD.OOPC.CH.ZS", "oop_pct_che", 2010, 2013),
    ("SH.XPD.GHED.CH.ZS", "gov_pct_che", 2010, 2013),
    ("SH.XPD.CHEX.GD.ZS", "che_pct_gdp", 2010, 2013),
    ("SH.XPD.CHEX.PP.CD", "che_pc_ppp_usd", 2010, 2013),
    ("SH.MED.NUMW.P3",    "nurses_per_1000", 2010, 2013),
    ("SH.MED.PHYS.ZS",    "physicians_per_1000", 2010, 2013),
    ("NY.GDP.PCAP.PP.CD", "gdp_pc_ppp_usd", 2010, 2013),
    ("SP.DYN.LE00.IN",    "life_expectancy", 2010, 2013),
    ("SH.UHC.SRVS.CV.XD", "uhc_service_cov_index", 2010, 2017),  # earliest 2010
]


def fetch_indicator_bulk(iso3_list: list[str], indicator: str,
                          year_from: int, year_to: int,
                          chunk_size: int = 8) -> dict[str, dict[int, float]]:
    """Multi-country query, chunked to keep URL length under server limits."""
    out: dict[str, dict[int, float]] = {c: {} for c in iso3_list}
    for i in range(0, len(iso3_list), chunk_size):
        chunk = iso3_list[i : i + chunk_size]
        iso = ";".join(chunk)
        url = (f"{WB_BASE}/country/{iso}/indicator/{indicator}"
               f"?format=json&date={year_from}:{year_to}&per_page=2000")
        try:
            data = _get_json(url)
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(data, list) or len(data) < 2 or data[1] is None:
            continue
        for row in data[1]:
            v = row.get("value")
            d = row.get("date")
            cc = row.get("countryiso3code") or ""
            if v is None or d is None or not cc:
                continue
            try:
                out.setdefault(cc, {})[int(d)] = float(v)
            except (ValueError, TypeError):
                continue
        time.sleep(0.02)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--country_master", required=True, type=Path)
    ap.add_argument("--out_csv", required=True, type=Path)
    args = ap.parse_args()

    countries: list[dict] = []
    with args.country_master.open() as f:
        countries = list(csv.DictReader(f))

    iso_list_all = [c["iso3"] for c in countries]
    iso_list = [iso for iso in iso_list_all if iso in WB_RECOGNISED]
    skipped = sorted(set(iso_list_all) - set(iso_list))
    if skipped:
        print(f"  skipping non-WB codes: {skipped}")
    rows_by_iso: dict[str, dict] = {
        c["iso3"]: {"iso3": c["iso3"], "country": c["country"]} for c in countries
    }

    for code, short, yfrom, yto in INDICATORS:
        print(f"  fetching {code} ({short}) ...", flush=True)
        try:
            data = fetch_indicator_bulk(iso_list, code, yfrom, yto, chunk_size=22)
        except Exception as e:  # noqa: BLE001
            print(f"    ! failed: {e}")
            data = {iso: {} for iso in iso_list}
        for iso in iso_list_all:
            avg, n = average(data.get(iso, {}))
            rows_by_iso[iso][short] = avg if avg is not None else ""
            rows_by_iso[iso][f"{short}_n_obs"] = n

    rows = list(rows_by_iso.values())

    fieldnames = list(rows[0].keys())
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"Wrote {len(rows)} rows to {args.out_csv}")


if __name__ == "__main__":
    main()
