"""
keywords.py — Emerging-keyword list for the "Developments to Watch" scanner.

Edit this file freely to add, remove, or recategorise keywords.
No code changes elsewhere are required — the scanner reads these lists at runtime.

EMERGING_KEYWORDS   : list[str] — full set searched across SEC filings and UK RNS.
BIOTECH_KEYWORD_HINTS : set[str] — subset that additionally triggers a
                        ClinicalTrials.gov Phase 2/3 trial look-up.
"""

EMERGING_KEYWORDS: list[str] = [

    # ── AI & Digital Infrastructure ───────────────────────────────────────────
    "sovereign AI",
    "AI inference",
    "AI data centre",
    "agentic AI",
    "liquid cooling",
    "private 5G",
    "edge computing",
    "quantum computing",

    # ── Energy Transition ─────────────────────────────────────────────────────
    "grid modernisation",
    "long-duration storage",
    "green hydrogen",
    "carbon capture utilisation",
    "small modular reactor",
    "offshore wind repowering",
    "heat pump",
    "virtual power plant",

    # ── Defence & Security ────────────────────────────────────────────────────
    "directed energy weapon",
    "autonomous systems",
    "hypersonic",
    "cyber resilience",
    "space domain awareness",

    # ── Healthcare & Biotech ──────────────────────────────────────────────────
    "GLP-1",
    "obesity drug",
    "radiopharmaceutical",
    "bispecific antibody",
    "cell therapy",
    "mRNA platform",
    "CRISPR",

    # ── Critical Materials ────────────────────────────────────────────────────
    "rare earth processing",
    "lithium refining",
    "copper recycling",
    "gallium",
    "nickel sulphate",

    # ── Finance & Digital Assets ──────────────────────────────────────────────
    "tokenisation",
    "real-world assets",
    "embedded finance",
    "payments infrastructure",

    # ── Space & Connectivity ──────────────────────────────────────────────────
    "commercial launch services",
    "satellite broadband",
    "in-space manufacturing",

]

BIOTECH_KEYWORD_HINTS: set[str] = {
    "GLP-1",
    "obesity drug",
    "radiopharmaceutical",
    "bispecific antibody",
    "cell therapy",
    "mRNA platform",
    "CRISPR",
}
