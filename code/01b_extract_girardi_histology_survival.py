"""Extract histology-specific 5-year net survival from Girardi et al. 2023 Supplementary Table 3A.

Source: Girardi F, Di Carlo V, Stiller C, et al. Global survival trends for brain tumors,
by histology: analysis of individual records for 556,237 adults diagnosed in 59 countries
during 2000-2014 (CONCORD-3). Neuro-Oncology 2023;25:580-92.
DOI: 10.1093/neuonc/noac217.

Supplementary Table 3A contains 6 histology columns. Column identifications were
validated against the paper text:

  Column 1: Pilocytic astrocytoma          (high survival, ~65-90%)
  Column 2: Diffuse and anaplastic astrocytoma  (validated: Canada 2010-14 = 32.7,
                                                  in paper-stated 30-39% band)
  Column 3: Glioblastoma                   (validated: Ecuador 2010-14 = 4.4 == 4.4)
                                           (validated: China 2010-14 = 16.9 == 16.9)
  Column 4: Ependymoma                     (very high survival in adults, 80-95%)
  Column 5: Unspecified astrocytoma        (validated: Ecuador 2010-14 = 27.2 in paper)
  Column 6: Oligodendroglioma              (validated: Canada 2010-14 = 58.9, in
                                            paper-stated 50-59% band)

Cell estimates carry CONCORD's reliability flag (§ = less reliable; * = 100% national
coverage; † = not age-standardised in some renderings).

Usage:
  python code/01b_extract_girardi_histology_survival.py \
    --pdf data/raw/girardi_concord3_brain_supp_table_3a.pdf \
    --out data/processed/girardi_histology_5yr_2010_14.csv
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import fitz  # PyMuPDF


# Column 0-indexed -> histology label
HISTOLOGY_COLS = {
    0: "pilocytic_astrocytoma",
    1: "diffuse_anaplastic_astrocytoma",
    2: "glioblastoma",
    3: "ependymoma",
    4: "unspecified_astrocytoma",
    5: "oligodendroglioma",
}


def _extract_spans(pdf_path: Path) -> list[tuple[float, float, str]]:
    """Return all text spans across all pages as (page_y, page_x, text)."""
    doc = fitz.open(pdf_path)
    spans: list[tuple[int, float, float, str]] = []
    for page_idx in range(doc.page_count):
        page = doc[page_idx]
        d = page.get_text("dict")
        for block in d.get("blocks", []):
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span.get("text", "").strip()
                    if not text:
                        continue
                    bbox = span.get("bbox", [0, 0, 0, 0])
                    spans.append((page_idx, bbox[1], bbox[0], text))
    return spans


def _group_into_rows(spans, y_tol: float = 6.0):
    """Bucket spans by (page, y) into table rows."""
    rows: dict[tuple[int, float], list[tuple[float, str]]] = {}
    for page_idx, y, x, text in spans:
        # find nearest existing y bucket
        key = None
        for existing_key in rows:
            if existing_key[0] == page_idx and abs(existing_key[1] - y) < y_tol:
                key = existing_key
                break
        if key is None:
            key = (page_idx, y)
            rows[key] = []
        rows[key].append((x, text))
    out = []
    for (page_idx, y), items in rows.items():
        items.sort()
        out.append((page_idx, y, items))
    out.sort(key=lambda r: (r[0], r[1]))
    return out


def _country_key(s: str) -> str | None:
    s = s.strip()
    if not s:
        return None
    if re.match(r"^[A-Z][A-Za-z* ()\-]+[*]?$", s) and len(s) < 50:
        if s.upper() in {"AFRICA", "AMERICA (CENTRAL AND SOUTH)",
                         "AMERICA (NORTH)", "ASIA", "EUROPE", "OCEANIA",
                         "COUNTRY", "PERIOD OF DIAGNOSIS"}:
            return None
        return s
    return None


def _is_period(s: str) -> bool:
    return s in ("2000-2004", "2005-2009", "2010-2014",
                 "2000\u20132004", "2005\u20132009", "2010\u20132014")


def _normalise_period(s: str) -> str:
    return s.replace("\u2013", "-")


# 6 column x-centroids extracted by inspecting Supp Table 3A; values are bbox left edges
# observed in the 2-page table dump above. Each column has a left-edge for the estimate
# and a left-edge for the lower bound of the CI.
COLUMN_X_RANGES = [
    (480, 740),   # col 0: Pilocytic astrocytoma   (Argentina 2005-09 row showed 42.0 at x=531)
    (740, 945),   # col 1: Diffuse/anaplastic     (Argentina 2010-14 showed 47.4 at x=751)
    (945, 1190),  # col 2: Glioblastoma           (Argentina 2010-14 showed 9.7 at x=977)
    (1190, 1390), # col 3: Ependymoma             (Argentina row had no value -- "-")
    (1390, 1590), # col 4: Unspecified astrocytoma (Argentina 2010-14 showed 33.4 at x=1404)
    (1590, 1820), # col 5: Oligodendroglioma      (Argentina 2010-14 showed 57.3 at x=1607)
]


def _column_for_x(x: float) -> int | None:
    for i, (lo, hi) in enumerate(COLUMN_X_RANGES):
        if lo <= x < hi:
            return i
    return None


def parse_table_3a(pdf_path: Path) -> list[dict]:
    spans = _extract_spans(pdf_path)
    rows = _group_into_rows(spans)

    out: list[dict] = []
    current_country: str | None = None
    for page_idx, y, items in rows:
        # First check for country header (left-most x position, single token)
        first_x, first_text = items[0]
        if first_x < 350 and _country_key(first_text):
            current_country = first_text
            continue

        # Period detection: look for a 2000-2004 / 2005-2009 / 2010-2014 token
        period = None
        for x, t in items:
            tn = _normalise_period(t)
            if _is_period(tn):
                period = tn
                break
        if period is None or current_country is None:
            continue

        # Pull cell estimates: for each x position, identify the column and the leftmost
        # numeric value in that column's range. The leftmost numeric in the column range
        # is the estimate; subsequent numbers in the same row are CI bounds.
        col_estimates: dict[int, str] = {}
        col_flags: dict[int, str] = {}
        seen_first_in_col: set[int] = set()
        for x, t in items:
            tn = _normalise_period(t)
            if _is_period(tn) or tn == "-" or current_country == tn:
                continue
            col = _column_for_x(x)
            if col is None:
                continue
            # First numeric in that column = estimate
            m = re.match(r"^(\d+(?:\.\d+)?)$", t)
            if m and col not in seen_first_in_col:
                col_estimates[col] = m.group(1)
                seen_first_in_col.add(col)
            elif t in ("\u00a7", "\u2020", "*", "\u2021") and col in col_estimates and col not in col_flags:
                col_flags[col] = t

        if not col_estimates:
            continue

        rec = {"country": current_country, "period": period}
        for col, label in HISTOLOGY_COLS.items():
            rec[label] = col_estimates.get(col, "")
            rec[f"{label}_flag"] = col_flags.get(col, "")
        out.append(rec)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    rows = parse_table_3a(args.pdf)
    rows_2010 = [r for r in rows if r["period"] == "2010-2014"]
    rows_2010.sort(key=lambda r: r["country"])

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["country", "period"]
    for label in HISTOLOGY_COLS.values():
        fields.extend([label, f"{label}_flag"])
    with args.out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows_2010:
            w.writerow(r)
    n_gbm = sum(1 for r in rows_2010 if r["glioblastoma"])
    print(f"Wrote {len(rows_2010)} (country, 2010-14) rows; {n_gbm} have glioblastoma value")


if __name__ == "__main__":
    main()
