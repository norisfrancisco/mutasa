"""
BibTeX parser: reads a Scopus .bib export and returns normalised records.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import logging

import bibtexparser

logger = logging.getLogger(__name__)


@dataclass
class Record:
    """Normalised representation of one bibliographic record."""

    key: str                    # BibTeX citation key
    entry_type: str             # BibTeX entry type: article, conference, book …
    doc_type: str               # Scopus document type: Article, Book chapter …
    title: str
    abstract: str
    year: Optional[int]
    authors: str
    journal: str
    doi: str
    affiliations: str
    author_keywords: str
    note: str                   # Scopus note field (cited-by count, OA status)
    raw: dict[str, str]         # All original fields, for audit purposes


def _get(entry, field: str, default: str = "") -> str:
    """Safely extract a string value from a bibtexparser Entry.

    Duplicate-key recovered entries may retain LaTeX-style curly-brace wrapping
    (e.g. year = {2017}) because they bypass the full middleware pipeline.
    Strip outer braces so downstream parsing works correctly.
    """
    f = entry.fields_dict.get(field)
    if f is None:
        return default
    value = str(f.value).strip()
    # Strip a single layer of wrapping braces left by the raw parser
    if value.startswith("{") and value.endswith("}") and len(value) > 1:
        value = value[1:-1].strip()
    return value


def parse_bib(path: str | Path) -> list[Record]:
    """Parse a Scopus BibTeX export and return a list of normalised Records."""
    path = Path(path)
    library = bibtexparser.parse_file(str(path))

    # Recover entries from DuplicateBlockKeyBlock (Scopus exports sometimes
    # produce duplicate BibTeX keys; bibtexparser keeps only the first in
    # library.entries and wraps the second in a failed block).
    recovered = []
    if library.failed_blocks:
        logger.warning("%d blocks failed to parse.", len(library.failed_blocks))
        for block in library.failed_blocks:
            entry = getattr(block, "ignore_error_block", None)
            if entry is not None and hasattr(entry, "fields_dict"):
                recovered.append(entry)
                logger.info("Recovered duplicate-key entry: %s", entry.key)

    all_entries = list(library.entries) + recovered
    logger.info("Total entries after recovery: %d", len(all_entries))

    records: list[Record] = []
    for entry in all_entries:
        year_str = _get(entry, "year")
        try:
            year = int(year_str)
        except (ValueError, TypeError):
            year = None

        raw = {f.key: str(f.value) for f in entry.fields}

        records.append(Record(
            key=entry.key,
            entry_type=entry.entry_type.lower(),
            doc_type=_get(entry, "type"),
            title=_get(entry, "title"),
            abstract=_get(entry, "abstract"),
            year=year,
            authors=_get(entry, "author"),
            journal=_get(entry, "journal"),
            doi=_get(entry, "doi"),
            affiliations=_get(entry, "affiliations"),
            author_keywords=_get(entry, "author_keywords"),
            note=_get(entry, "note"),
            raw=raw,
        ))

    logger.info("Parsed %d records from %s", len(records), path.name)
    return records
