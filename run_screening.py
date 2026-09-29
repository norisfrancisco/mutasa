"""
Entry point: PRISMA/PECO screening of a Scopus BibTeX export.

Usage:
    python run_screening.py <path_to.bib> [--output-dir results]

The script runs five sequential stages:
  1. Year filter (2010–2026)
  2. Document type filter (exclude books, book chapters, editorials, notes)
  3. Deduplication (DOI and normalised title)
  4. PECO keyword screening (Population / Exposure / Context / Outcome)
  5. Conservative aggregation (MAYBE → full-text review)

Outputs written to --output-dir:
  screening_decisions.csv  — all records with decision + reason code
  included.csv             — INCLUDE decisions
  excluded.csv             — EXCLUDE decisions with reason codes
  maybe_full_text.csv      — MAYBE decisions for manual full-text review
  prisma_flow.txt          — PRISMA flow counts per stage
  audit_log.json           — full audit trail (every decision, all fields)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from screening.parser import parse_bib
from screening.screener import screen
from screening.output import save_results, save_prisma

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PRISMA/PECO systematic review screener for Scopus BibTeX exports.",
    )
    parser.add_argument(
        "bib_path",
        help="Path to the Scopus .bib export file.",
    )
    parser.add_argument(
        "--output-dir",
        default="results",
        help="Directory to write output files (default: results/).",
    )
    args = parser.parse_args()

    bib_path = Path(args.bib_path)
    if not bib_path.exists():
        logger.error("File not found: %s", bib_path)
        sys.exit(1)

    logger.info("Parsing BibTeX file: %s", bib_path)
    records = parse_bib(bib_path)
    logger.info("Records loaded: %d", len(records))

    logger.info("Running PRISMA/PECO screening pipeline...")
    decisions = screen(records)

    n_include = sum(1 for d in decisions if d.decision == "INCLUDE")
    n_maybe   = sum(1 for d in decisions if d.decision == "MAYBE")
    n_exclude = sum(1 for d in decisions if d.decision == "EXCLUDE")
    logger.info(
        "Screening complete — INCLUDE: %d | MAYBE: %d | EXCLUDE: %d",
        n_include, n_maybe, n_exclude,
    )

    save_results(decisions, args.output_dir)
    save_prisma(decisions, args.output_dir)
    logger.info("Results written to: %s/", args.output_dir)


if __name__ == "__main__":
    main()
