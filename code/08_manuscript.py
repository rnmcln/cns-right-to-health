"""Generate manuscript .docx from the analytic dataset and result CSVs.

This script renders a Word manuscript from the analytic dataset, the result
CSVs, and the literature corpus. The manuscript itself is not included in
the public release; users who want to re-derive a manuscript can do so
locally from these inputs.

Usage:

    python code/08_manuscript.py \
        --analytic data/processed/analytic_dataset.csv \
        --results_dir results/ \
        --corpus data/processed/literature_corpus.csv \
        --out_docx results/manuscript.docx

Inputs:
    --analytic     country-level analytic dataset (CSV).
    --results_dir  directory containing the per-outcome correlation,
                   regression, binary-summary and sensitivity CSVs, plus
                   family_wide_fdr.csv and country_flow.csv.
    --corpus       literature corpus CSV with PMID, DOI, author list,
                   journal, year, volume and pages.
    --out_docx     output Word file path.

The reproducibility package contains the full analysis pipeline through
code/07_word_tables.py, which produces all results, figures and the
companion tables.docx file. The body of this script is omitted from the
public release.
"""
import argparse
import sys


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--analytic", required=True)
    ap.add_argument("--results_dir", required=True)
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out_docx", required=True)
    ap.parse_args()
    sys.stderr.write(
        "The manuscript generator body is intentionally omitted from this "
        "public release. See the README for what is and is not included.\n"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
