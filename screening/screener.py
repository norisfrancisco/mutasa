"""
PRISMA/PECO screener — five sequential stages:

  Stage 1 | Deterministic: year out of range         → Excl_Período
  Stage 2 | Deterministic: ineligible document type  → Excl_TipoEstudo
  Stage 3 | Deduplication: duplicate DOI or title    → Excl_Duplicado
  Stage 4 | PECO keyword screening                   → INCLUDE / EXCLUDE / MAYBE
  Stage 5 | Aggregate: MAYBE records remain for full-text review

Conservative rule (gold standard for title/abstract phase):
  When evidence is insufficient → MAYBE, never EXCLUDE.
  MAYBE = forward to full-text review.

Each decision carries:
  - decision: "INCLUDE" | "EXCLUDE" | "MAYBE"
  - reason_code: None or one of the Excl_* codes defined in the protocol
  - rationale: short human-readable explanation
  - stage: which pipeline stage made the decision
  - peco_flags: dict with per-dimension signal strength (for transparency)
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

from .criteria import CRITERIA
from .parser import Record


# ──────────────────────────────────────────────────────────────────────────────
# Decision data-class
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Decision:
    record: Record
    decision: str                       # INCLUDE | EXCLUDE | MAYBE
    reason_code: Optional[str]          # Excl_* code or None
    rationale: str
    stage: int
    peco_flags: dict[str, str] = field(default_factory=dict)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _normalise(text: str) -> str:
    """Lowercase + strip accents for robust substring matching."""
    nfc = unicodedata.normalize("NFC", text.lower())
    return re.sub(r"\s+", " ", nfc)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    norm = _normalise(text)
    return any(t in norm for t in terms)


def _first_match(text: str, terms: tuple[str, ...]) -> Optional[str]:
    norm = _normalise(text)
    for t in terms:
        if t in norm:
            return t
    return None


def _searchable(r: Record) -> str:
    """Concatenate all text fields for keyword matching."""
    return " ".join([
        r.title,
        r.abstract,
        r.affiliations,
        r.author_keywords,
        r.journal,
    ])


def _normalise_title(title: str) -> str:
    """Compact title for deduplication (remove punctuation, extra spaces)."""
    t = re.sub(r"[^\w\s]", "", title.lower())
    return re.sub(r"\s+", " ", t).strip()


# ──────────────────────────────────────────────────────────────────────────────
# Main screener
# ──────────────────────────────────────────────────────────────────────────────

def screen(records: list[Record]) -> list[Decision]:
    """
    Apply the five-stage PRISMA pipeline to a list of records.
    Returns one Decision per record, in the same order as input.
    """
    decisions: list[Decision] = []

    # Deduplication state
    seen_dois: set[str] = set()
    seen_titles: set[str] = set()

    for r in records:
        d = _screen_single(r, seen_dois, seen_titles)
        decisions.append(d)

        # Register in dedup sets only for non-excluded records
        if d.decision != "EXCLUDE" or d.reason_code == "Excl_Duplicado":
            pass  # duplicates already registered below
        if d.reason_code != "Excl_Duplicado":
            if r.doi:
                seen_dois.add(r.doi.lower())
            norm_t = _normalise_title(r.title)
            if norm_t:
                seen_titles.add(norm_t)

    return decisions


def _screen_single(
    r: Record,
    seen_dois: set[str],
    seen_titles: set[str],
) -> Decision:

    # ── Stage 1: Year ─────────────────────────────────────────────────────── #
    if r.year is None:
        return Decision(
            record=r,
            decision="MAYBE",
            reason_code=None,
            rationale="Year not found; cannot apply year filter — forward to full text.",
            stage=1,
        )

    if r.year < CRITERIA.year_min:
        return Decision(
            record=r,
            decision="EXCLUDE",
            reason_code="Excl_Período",
            rationale=f"Published in {r.year}, before the 2010 cut-off.",
            stage=1,
        )

    if r.year > CRITERIA.year_max:
        return Decision(
            record=r,
            decision="EXCLUDE",
            reason_code="Excl_Período",
            rationale=f"Published in {r.year}, after the 2026 cut-off.",
            stage=1,
        )

    # ── Stage 2: Document type ─────────────────────────────────────────────  #
    doc_type_lower = r.doc_type.lower().strip()
    for excluded in CRITERIA.excluded_doc_types:
        if doc_type_lower == excluded or doc_type_lower.startswith(excluded):
            return Decision(
                record=r,
                decision="EXCLUDE",
                reason_code="Excl_TipoEstudo",
                rationale=f"Document type '{r.doc_type}' is not eligible "
                           f"(books, book chapters, editorials, notes excluded).",
                stage=2,
            )

    # ── Stage 3: Deduplication ─────────────────────────────────────────────  #
    if r.doi and r.doi.lower() in seen_dois:
        return Decision(
            record=r,
            decision="EXCLUDE",
            reason_code="Excl_Duplicado",
            rationale=f"Duplicate DOI: {r.doi}",
            stage=3,
        )

    norm_t = _normalise_title(r.title)
    if norm_t and norm_t in seen_titles:
        return Decision(
            record=r,
            decision="EXCLUDE",
            reason_code="Excl_Duplicado",
            rationale=f"Duplicate title: '{r.title[:80]}'",
            stage=3,
        )

    # ── Stage 4: PECO keyword screening ───────────────────────────────────── #
    return _peco_screen(r)


def _peco_screen(r: Record) -> Decision:
    """
    Evaluate the four PECO dimensions using keyword matching.
    Decision logic:
      - Clear NOT MET on any dimension → EXCLUDE with specific code
      - All dimensions at least POSSIBLE → INCLUDE
      - Any dimension UNCERTAIN (missing abstract or ambiguous) → MAYBE
    """
    text = _searchable(r)
    peco_flags: dict[str, str] = {}
    missing_abstract = not r.abstract.strip()

    # ── P: Population ──────────────────────────────────────────────────── #
    has_he = _contains_any(text, CRITERIA.p_include)
    has_non_he = _contains_any(text, CRITERIA.p_exclude)

    if has_non_he and not has_he:
        peco_flags["P"] = "NOT_MET"
        return Decision(
            record=r,
            decision="EXCLUDE",
            reason_code="Excl_População",
            rationale="Explicit signals of non-higher-education population (primary/secondary/vocational).",
            stage=4,
            peco_flags=peco_flags,
        )
    elif has_he:
        peco_flags["P"] = "MET"
    elif missing_abstract:
        peco_flags["P"] = "UNCERTAIN_NO_ABSTRACT"
    else:
        peco_flags["P"] = "UNCERTAIN"

    # ── E: Exposure / Modality ─────────────────────────────────────────── #
    has_odl = _contains_any(text, CRITERIA.e_include)
    has_f2f_only = _contains_any(text, CRITERIA.e_exclude_signals)

    if has_f2f_only and not has_odl:
        peco_flags["E"] = "NOT_MET"
        return Decision(
            record=r,
            decision="EXCLUDE",
            reason_code="Excl_Modalidade",
            rationale="Explicit signals of exclusively face-to-face instruction.",
            stage=4,
            peco_flags=peco_flags,
        )
    elif has_odl:
        peco_flags["E"] = "MET"
    elif missing_abstract:
        peco_flags["E"] = "UNCERTAIN_NO_ABSTRACT"
    else:
        peco_flags["E"] = "UNCERTAIN"

    # ── C: Context / Geography (SADC) ─────────────────────────────────── #
    # Affiliations are the strongest signal (institution country is explicit).
    # Prioritise affiliations, then title + abstract.
    affil_text = _normalise(r.affiliations)
    full_text = _normalise(text)

    has_strong_sadc_affil = any(t in affil_text for t in CRITERIA.c_strong)
    has_strong_sadc_text = any(t in full_text for t in CRITERIA.c_strong)
    has_sadc_signal = has_strong_sadc_affil or has_strong_sadc_text

    # Count non-SADC signals
    non_sadc_hits = [t for t in CRITERIA.c_non_sadc if t in full_text]

    if not has_sadc_signal:
        if non_sadc_hits:
            # Only non-SADC countries detected, no SADC country → exclude
            peco_flags["C"] = "NOT_MET"
            sample = ", ".join(non_sadc_hits[:3])
            return Decision(
                record=r,
                decision="EXCLUDE",
                reason_code="Excl_Geografia",
                rationale=f"No SADC country detected; non-SADC signals found: [{sample}].",
                stage=4,
                peco_flags=peco_flags,
            )
        elif missing_abstract and not affil_text:
            peco_flags["C"] = "UNCERTAIN_NO_ABSTRACT"
        else:
            # No geographic signal at all → MAYBE (could be SADC, information insufficient)
            peco_flags["C"] = "UNCERTAIN"
    else:
        peco_flags["C"] = "MET"

    # ── O: Outcome ─────────────────────────────────────────────────────── #
    has_outcome = _contains_any(text, CRITERIA.o_include)

    if has_outcome:
        peco_flags["O"] = "MET"
    elif missing_abstract:
        peco_flags["O"] = "UNCERTAIN_NO_ABSTRACT"
    else:
        peco_flags["O"] = "UNCERTAIN"

    # ── Aggregation ────────────────────────────────────────────────────── #
    statuses = set(peco_flags.values())
    all_met = all(v == "MET" for v in peco_flags.values())
    any_uncertain = any("UNCERTAIN" in v for v in peco_flags.values())
    any_not_met = any(v == "NOT_MET" for v in peco_flags.values())  # handled above

    if all_met:
        return Decision(
            record=r,
            decision="INCLUDE",
            reason_code=None,
            rationale="All four PECO dimensions met (P={P}, E={E}, C={C}, O={O}).".format(**peco_flags),
            stage=4,
            peco_flags=peco_flags,
        )

    # When P+E+C are met but O is uncertain (keyword absent, not clearly absent):
    # send to MAYBE for full-text review rather than excluding.
    if (
        peco_flags.get("P") == "MET"
        and peco_flags.get("E") == "MET"
        and peco_flags.get("C") == "MET"
        and peco_flags.get("O") == "UNCERTAIN"
    ):
        return Decision(
            record=r,
            decision="MAYBE",
            reason_code=None,
            rationale=(
                "P/E/C met but outcome keywords absent. "
                "Cannot rule out relevance from abstract alone — forward to full-text review."
            ),
            stage=4,
            peco_flags=peco_flags,
        )

    # Conservative default: if any dimension is uncertain → MAYBE
    if any_uncertain:
        uncertain_dims = [k for k, v in peco_flags.items() if "UNCERTAIN" in v]
        return Decision(
            record=r,
            decision="MAYBE",
            reason_code=None,
            rationale=f"Uncertain PECO dimensions: {uncertain_dims}. Forward to full-text review.",
            stage=4,
            peco_flags=peco_flags,
        )

    # Fallback: if we got here without a clear path, include conservatively
    return Decision(
        record=r,
        decision="MAYBE",
        reason_code=None,
        rationale="Insufficient information to determine eligibility; forward to full-text review.",
        stage=4,
        peco_flags=peco_flags,
    )
