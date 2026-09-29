"""
Results export: CSV tables + PRISMA flow summary + JSON audit log.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Optional

import pandas as pd

from .screener import Decision


# ──────────────────────────────────────────────────────────────────────────────
# CSV export
# ──────────────────────────────────────────────────────────────────────────────

def _decision_to_row(d: Decision) -> dict:
    r = d.record
    return {
        "key": r.key,
        "decision": d.decision,
        "reason_code": d.reason_code or "",
        "stage": d.stage,
        "rationale": d.rationale,
        "P": d.peco_flags.get("P", ""),
        "E": d.peco_flags.get("E", ""),
        "C": d.peco_flags.get("C", ""),
        "O": d.peco_flags.get("O", ""),
        "year": r.year or "",
        "doc_type": r.doc_type,
        "title": r.title,
        "authors": r.authors[:120] if r.authors else "",
        "journal": r.journal,
        "doi": r.doi,
        "affiliations": r.affiliations[:200] if r.affiliations else "",
        "abstract": r.abstract[:400] if r.abstract else "",
    }


def save_results(decisions: list[Decision], output_dir: str | Path) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    rows = [_decision_to_row(d) for d in decisions]
    df = pd.DataFrame(rows)

    # Full screening table
    df.to_csv(out / "screening_decisions.csv", index=False)

    # Subset tables
    df[df.decision == "INCLUDE"].to_csv(out / "included.csv", index=False)
    df[df.decision == "EXCLUDE"].to_csv(out / "excluded.csv", index=False)
    df[df.decision == "MAYBE"].to_csv(out / "maybe_full_text.csv", index=False)

    # JSON audit log (full details, no truncation)
    log = []
    for d in decisions:
        log.append({
            "key": d.record.key,
            "decision": d.decision,
            "reason_code": d.reason_code,
            "stage": d.stage,
            "rationale": d.rationale,
            "peco_flags": d.peco_flags,
            "year": d.record.year,
            "doc_type": d.record.doc_type,
            "doi": d.record.doi,
            "title": d.record.title,
            "affiliations": d.record.affiliations,
        })
    with open(out / "audit_log.json", "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────────────────────────────────────
# PRISMA flow
# ──────────────────────────────────────────────────────────────────────────────

def _count_by_code(decisions: list[Decision], code: str) -> int:
    return sum(1 for d in decisions if d.reason_code == code)


def prisma_flow(decisions: list[Decision]) -> str:
    total = len(decisions)

    n_s1_excl = sum(1 for d in decisions if d.stage == 1 and d.decision == "EXCLUDE")
    n_s2_excl = sum(1 for d in decisions if d.stage == 2 and d.decision == "EXCLUDE")
    n_s3_excl = sum(1 for d in decisions if d.stage == 3 and d.decision == "EXCLUDE")
    n_s4_excl = sum(1 for d in decisions if d.stage == 4 and d.decision == "EXCLUDE")

    n_excl_periodo    = _count_by_code(decisions, "Excl_Período")
    n_excl_tipo       = _count_by_code(decisions, "Excl_TipoEstudo")
    n_excl_dup        = _count_by_code(decisions, "Excl_Duplicado")
    n_excl_pop        = _count_by_code(decisions, "Excl_População")
    n_excl_geo        = _count_by_code(decisions, "Excl_Geografia")
    n_excl_mod        = _count_by_code(decisions, "Excl_Modalidade")
    n_excl_desfecho   = _count_by_code(decisions, "Excl_Desfecho")
    n_excl_tema       = _count_by_code(decisions, "Excl_Tema")
    n_excl_dados      = _count_by_code(decisions, "Excl_Dados")

    n_total_excl = sum([
        n_excl_periodo, n_excl_tipo, n_excl_dup,
        n_excl_pop, n_excl_geo, n_excl_mod,
        n_excl_desfecho, n_excl_tema, n_excl_dados,
    ])

    n_include = sum(1 for d in decisions if d.decision == "INCLUDE")
    n_maybe = sum(1 for d in decisions if d.decision == "MAYBE")
    n_forward = n_include + n_maybe  # forwarded to full-text review

    lines = [
        "=" * 68,
        "  PRISMA FLOW DIAGRAM — Title/Abstract Screening",
        "=" * 68,
        "",
        f"  Records retrieved from Scopus               {total:>5}",
        "",
        "  ── Stage 1: Year filter ────────────────────────────────",
        f"  Excluded (Excl_Período, year < 2010)         {n_excl_periodo:>5}",
        "",
        "  ── Stage 2: Document type filter ───────────────────────",
        f"  Excluded (Excl_TipoEstudo)                   {n_excl_tipo:>5}",
        "    (books, book chapters, editorials, notes)",
        "",
        "  ── Stage 3: Deduplication ──────────────────────────────",
        f"  Excluded (Excl_Duplicado)                    {n_excl_dup:>5}",
        "",
        "  ── Stage 4: PECO keyword screening ─────────────────────",
        f"  Excluded (Excl_População)                    {n_excl_pop:>5}",
        f"  Excluded (Excl_Geografia)                    {n_excl_geo:>5}",
        f"  Excluded (Excl_Modalidade)                   {n_excl_mod:>5}",
        f"  Excluded (Excl_Desfecho)                     {n_excl_desfecho:>5}",
        f"  Excluded (Excl_Tema)                         {n_excl_tema:>5}",
        f"  Excluded (Excl_Dados)                        {n_excl_dados:>5}",
        "",
        "  ── Summary ──────────────────────────────────────────────",
        f"  Total excluded                               {n_total_excl:>5}",
        f"  INCLUDE (all 4 PECO dimensions clearly met)  {n_include:>5}",
        f"  MAYBE   (uncertain, forwarded to full text)  {n_maybe:>5}",
        f"  ─────────────────────────────────────────────────────",
        f"  Forwarded to full-text review (INCLUDE+MAYBE){n_forward:>5}",
        "",
        "  NOTE: MAYBE records must be reviewed manually.",
        "        At title/abstract phase, uncertainty → include (conservative rule).",
        "=" * 68,
    ]
    return "\n".join(lines)


def save_prisma(decisions: list[Decision], output_dir: str | Path) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    flow_text = prisma_flow(decisions)
    with open(out / "prisma_flow.txt", "w", encoding="utf-8") as f:
        f.write(flow_text)
    print(flow_text)
