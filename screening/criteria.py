"""
PECO inclusion/exclusion criteria for the systematic review on sociotechnical
barriers to ODL/e-learning in SADC higher education institutions.

P = Population (students and/or faculty in higher education)
E = Exposure (ODL, ODeL, e-learning, blended learning or similar modality)
C = Context (at least one SADC member state)
O = Outcome (barrier/challenge/access/engagement/performance/retention/equity)

Keyword sets are lowercase tuples for case-insensitive substring matching.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import FrozenSet


@dataclass(frozen=True)
class Criteria:
    # --- Stage 1: deterministic filters ------------------------------------- #

    # Scopus `type` field values to exclude unconditionally (Excl_TipoEstudo)
    excluded_doc_types: FrozenSet[str] = field(default_factory=lambda: frozenset({
        "book",
        "book chapter",
        "editorial",
        "note",
        "letter",
        "retracted",
        "erratum",
    }))

    year_min: int = 2010
    year_max: int = 2026

    # --- Stage 2: deduplication --------------------------------------------- #
    # (handled in code by DOI then normalised title)

    # --- Stage 3: PECO keyword screening ------------------------------------ #

    # P — Population: keywords signalling higher education context
    p_include: tuple[str, ...] = (
        "universit",        # university / universities / université
        "college",
        "higher education",
        "tertiary education",
        "tertiary institution",
        "institution of higher learning",
        "higher learning institution",
        "undergraduate",
        "postgraduate",
        "graduate student",
        "academic staff",
        "faculty member",
        "faculty staff",
        "lecturer",
        "professor",
        "polytechnic",
        "institute of technology",
        "open university",
        "distance university",
        "higher institution",
        "hei ",                # higher education institution abbreviation
        "university student",
        "campus",
    )

    # P — Signals that the study is NOT in higher education (hard exclusion)
    p_exclude: tuple[str, ...] = (
        "primary school",
        "secondary school",
        "high school",
        "k-12",
        "k12",
        "elementary school",
        "middle school",
        "secondary education",
        "basic education",
        "grade school",
        "pre-school",
        "preschool",
        "kindergarten",
        "vocational college",      # FET/VET is borderline — exclude unless also higher ed
        "further education and training college",  # FET college = not higher ed in SADC
        "technical and vocational",
        "tvet",
    )

    # E — Exposure/Intervention: ODL / e-learning / online / blended modality
    e_include: tuple[str, ...] = (
        "odl",
        "odel",
        "open and distance",
        "distance education",
        "distance learning",
        "distance teaching",
        "online education",
        "online learning",
        "online teaching",
        "online course",
        "online program",
        "e-learning",
        "elearning",
        "electronic learning",
        "blended learning",
        "hybrid learning",
        "hybrid course",
        "hybrid teaching",
        "virtual learning",
        "virtual classroom",
        "remote learning",
        "remote teaching",
        "digital learning",
        "technology-mediated",
        "ict-mediated",
        "ict-enhanced",
        "web-based learning",
        "web-based instruction",
        "web-based course",
        "mooc",
        "lms",
        "learning management system",
        "moodle",
        "blackboard",
        "canvas lms",
        "asynchronous learning",
        "synchronous learning",
        "mobile learning",
        "m-learning",
        "open distance",
        "telelearning",
        "tele-education",
    )

    # E — Signals of fully face-to-face instruction (may trigger Excl_Modalidade)
    e_exclude_signals: tuple[str, ...] = (
        "face-to-face only",
        "exclusively face-to-face",
        "traditional classroom only",
        "conventional classroom only",
        "in-person only",
    )

    # C — Context: SADC member states and regional identifiers
    # Source: SADC official membership list (as of 2024, 16 member states)
    c_include: tuple[str, ...] = (
        "angola", "angolan",
        "botswana", "motswana", "batswana",
        "comoro", "comorian",
        "congo",                    # DRC is a SADC member; Republic of Congo is not,
                                    # but Congo alone → MAYBE (ambiguous)
        "democratic republic of congo",
        "eswatini",
        "swaziland",                # former name
        "lesotho", "basotho",
        "madagascar", "malagasy",
        "malawi", "malawian",
        "mauritius", "mauritian",
        "mozambique", "mozambican",
        "namibia", "namibian",
        "seychelles", "seychellois",
        "south africa", "south african",
        "south africa's",
        "tanzania", "tanzanian",
        "zambia", "zambian",
        "zimbabwe", "zimbabwean",
        "sadc",
        "southern african development community",
        # Broader regional terms → weaker signal (used as MAYBE support)
        "southern africa",
        "sub-saharan africa",
        "africa",
    )

    # Strong SADC signals (country-specific → sufficient alone)
    c_strong: tuple[str, ...] = (
        "angola", "angolan",
        "botswana", "motswana", "batswana",
        "comoro", "comorian",
        "democratic republic of congo",
        "eswatini", "swaziland",
        "lesotho", "basotho",
        "madagascar", "malagasy",
        "malawi", "malawian",
        "mauritius", "mauritian",
        "mozambique", "mozambican",
        "namibia", "namibian",
        "seychelles", "seychellois",
        "south africa", "south african",
        "south africa's",
        "tanzania", "tanzanian",
        "zambia", "zambian",
        "zimbabwe", "zimbabwean",
        "sadc",
        "southern african development community",
        # DRC city-level signals (Kinshasa/Lubumbashi are unambiguously DRC/SADC)
        "kinshasa",
        "lubumbashi",
        "kisangani",
        "goma",
        # DRCongo alternate spellings
        "drc ",
        "dr congo",
        "d.r. congo",
        "congolese universit",   # "Congolese universities" → DRC context
    )

    # Clearly non-SADC regions (if ONLY these appear, geography not met)
    c_non_sadc: tuple[str, ...] = (
        "united states", "usa", "u.s.a",
        "united kingdom", "britain", "england", "scotland", "wales",
        "canada", "canadian",
        "australia", "australian",
        "new zealand",
        "china", "chinese",
        "india", "indian",
        "pakistan", "pakistan",
        "bangladesh",
        "malaysia", "malaysian",
        "indonesia", "indonesian",
        "philippines", "philippine",
        "turkey", "turkish",
        "iran", "iranian",
        "saudi arabia",
        "egypt", "egyptian",
        "nigeria", "nigerian",
        "kenya", "kenyan",
        "ghana", "ghanaian",
        "ethiopia", "ethiopian",
        "rwanda", "rwandan",
        "uganda", "ugandan",
        "europe", "european",
        "asia", "asian",
        "middle east",
        "latin america",
        "caribbean",
        "north america",
        "korea", "korean",
        "japan", "japanese",
        "brazil", "brazilian",
        "mexico", "mexican",
        "germany", "german",
        "france", "french",
        "spain", "spanish",
        "italy", "italian",
        "sweden", "swedish",
        "norway", "norwegian",
        "finland", "finnish",
        "denmark", "danish",
        "netherlands", "dutch",
        "portugal", "portuguese",
    )

    # O — Outcome: barriers, access, participation, performance, equity,
    #              or student/faculty experience in digital/online education
    o_include: tuple[str, ...] = (
        "barrier",
        "challenge",
        "constraint",
        "obstacle",
        "limitation",
        "difficulty",
        "difficulties",
        "problem",
        "access",
        "accessibility",
        "affordability",
        "equity",
        "inequity",
        "inequality",
        "divide",
        "digital divide",
        "engagement",
        "participation",
        "academic performance",
        "student performance",
        "learning outcome",
        "outcome",
        "retention",
        "persistence",
        "dropout",
        "drop-out",
        "attrition",
        "completion",
        "evasion",
        "experience",
        "perception",
        "attitude",
        "agency",           # student agency = active participation/outcome
        "voice",            # photovoice / student voice → experience outcome
        "narrative",
        "perspective",
        "satisfaction",
        "quality",
        "effectiveness",
        "adoption",
        "implementation",
        "infrastructure",
        "connectivity",
        "internet access",
        "bandwidth",
        "device",
        "electricity",
        "power outage",
        "load shedding",
        "data cost",
        "digital literacy",
        "digital skills",
        "digital competenc",
        "ict skill",
        "sociotechnical",
        "technology adoption",
        "factor",
        "success factor",
        "failure factor",
        "support",
        "enabler",
        "facilitator",
        "readiness",        # digital readiness is an access/equity outcome
        "preparedness",
        "awareness",
    )


# Module-level singleton — import this in other modules
CRITERIA = Criteria()
