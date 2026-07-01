"""Extract age-standardised 5-year net survival for adult brain tumours from CONCORD-3 Table 7.

Source PDF: Allemani C, Matsuda T, Di Carlo V, Harewood R, Matz M, Niksic M, et al.
Global surveillance of trends in cancer survival 2000-14 (CONCORD-3): analysis of
individual records for 37,513,025 patients diagnosed with one of 18 cancers from 322
population-based registries in 71 countries. Lancet 2018; 391: 1023-75.
DOI: 10.1016/S0140-6736(17)33326-3

Table 7 column order (10 cells per period row):
  0 Breast (women)
  1 Cervix
  2 Ovary
  3 Prostate
  4 Brain (adults)            <-- target
  5 Myeloid (adults)
  6 Lymphoid (adults)
  7 Brain (children)
  8 Acute lymphoblastic leukaemia (children)
  9 Lymphoma (children)

Pages 30-41 of the open-access PDF host Table 7. The PDF text stream interleaves country
header rows with three calendar period rows (2000-04, 2005-09, 2010-14), each followed
by up to 10 estimate cells, each given as 'value[flags]' followed by '(low-high)'. Cells
without an estimate appear as '..'.

Flags:
  * 100% national population coverage
  ‡ 100% national coverage for childhood malignancies only
  † estimate not age-standardised
  § estimate considered less reliable (>=15% of patients lost to follow-up, censored
    alive within 5 years, registered only from a death certificate, or with incomplete
    dates).

Estimates flagged § are excluded from the primary analysis here, in line with Allemani
et al.'s practice of excluding less reliable estimates from headline ranges.
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import fitz  # PyMuPDF


PERIODS = ("2000-04", "2005-09", "2010-14")  # ASCII; PDF uses en-dash, normalised below


def _normalise(text: str) -> str:
    return (
        text.replace("\u00b7", ".")  # middle dot decimal
            .replace("\u2013", "-")  # en-dash
            .replace("\u2014", "-")  # em-dash
    )


_COUNTRY_RE = re.compile(r"^[A-Z][A-Za-z0-9()*\u2021 \-,'\u2019]+[*\u2021]?$")
_BAD_HEADER_SUBSTR = (
    "CONCORD", "www", "Articles", "Continued", "Population",
    "Percentage", "Number", "Total", "online", "cancer", "survival",
    "Estimate", "Less reliable", "Five-year", "5-year",
)
_TABLE_HEADERS = (
    "Breast", "Cervix", "Ovary", "Prostate", "Brain", "Myeloid",
    "Lymphoid", "Acute", "Lymph", "Childhood", "Women", "Haem",
    "America", "Africa", "Asia", "Europe", "Oceania",
)


def _is_country_header(line: str) -> bool:
    s = line.strip()
    if not s or len(s) > 60:
        return False
    if not _COUNTRY_RE.match(s):
        return False
    if any(b in s for b in _BAD_HEADER_SUBSTR):
        return False
    if any(s.startswith(b) for b in _TABLE_HEADERS):
        return False
    return True


def _parse_cells(tokens: list[str]) -> list[tuple[str | None, str]]:
    """Walk through tokens; return up to 10 (estimate, flags) cells."""
    cells: list[tuple[str | None, str]] = []
    k = 0
    while k < len(tokens) and len(cells) < 10:
        t = tokens[k]
        if t == "..":
            cells.append((None, ""))
            k += 1
        elif re.match(r"^\d+(?:\.\d+)?", t):
            m = re.match(r"^(\d+(?:\.\d+)?)([†§*‡]*)$", t)
            if m:
                cells.append((m.group(1), m.group(2)))
            else:
                m2 = re.match(r"^(\d+(?:\.\d+)?)", t)
                cells.append((m2.group(1), ""))
            k += 1
            if k < len(tokens) and tokens[k].startswith("("):
                k += 1
        else:
            k += 1
    while len(cells) < 10:
        cells.append((None, ""))
    return cells


def extract_brain_survival(pdf_path: Path, page_range: tuple[int, int] = (30, 41)) -> list[dict]:
    """Return rows: country_label, period, brain_adult_5yr_pct, flags."""
    doc = fitz.open(pdf_path)
    text = "\n".join(doc[i].get_text() for i in range(page_range[0] - 1, page_range[1]))
    text = _normalise(text)
    lines = text.split("\n")

    rows: dict[tuple[str, str], dict] = {}
    current_country = None
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if _is_country_header(line):
            ahead = " ".join(lines[i + 1 : i + 6])
            if any(p in ahead for p in PERIODS):
                current_country = line
        if line in PERIODS and current_country is not None:
            period = line
            j = i + 1
            tokens: list[str] = []
            while j < len(lines):
                t = lines[j].strip()
                if t in PERIODS:
                    break
                if _is_country_header(t):
                    break
                if t:
                    tokens.append(t)
                j += 1
                if len(tokens) > 60:
                    break
            cells = _parse_cells(tokens)
            est, flags = cells[4]  # column index 4 = Brain (adults)
            rows[(current_country, period)] = {
                "country_label_concord": current_country,
                "period": period,
                "brain_adult_5yr_pct": est,
                "flags": flags,
            }
            i = j
            continue
        i += 1

    return list(rows.values())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    rows = extract_brain_survival(args.pdf)
    rows_2010 = [r for r in rows if r["period"] == "2010-14"]

    # Manual additions for rows that the table-footer text confuses with a country header.
    have = {r["country_label_concord"] for r in rows_2010}
    if "New Zealand*" not in have:
        rows_2010.append({
            "country_label_concord": "New Zealand*",
            "period": "2010-14",
            "brain_adult_5yr_pct": "23.3",
            "flags": "",
        })

    rows_2010.sort(key=lambda r: r["country_label_concord"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["country_label_concord", "period",
                                          "brain_adult_5yr_pct", "flags"])
        w.writeheader()
        for r in rows_2010:
            w.writerow(r)
    n = sum(1 for r in rows_2010 if r["brain_adult_5yr_pct"])
    print(f"Wrote {len(rows_2010)} rows ({n} with survival values) to {args.out}")


if __name__ == "__main__":
    main()
