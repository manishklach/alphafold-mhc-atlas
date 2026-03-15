from __future__ import annotations

SCOPE_HEADING = "What It Does Not Claim"
SCOPE_SUBHEADING = "Conservative by design"
SCOPE_TAKEAWAY = "The framework is intended for exploratory structural analysis and hypothesis generation."

SCOPE_POINTS = [
    "not a binding affinity predictor",
    "not an immunogenicity predictor",
    "not proof of mechanism",
    "not a substitute for experimental validation",
    "residue overlap is not treated as canonical equivalence without explicit mapping",
]

EXPANDED_SCOPE_HEADING = "What This Framework Is — and Is Not"
EXPANDED_SCOPE_BODY = (
    "This framework is built for exploratory structural analysis of peptide–MHC perturbations. "
    "It helps users compare variants, inspect structural contact changes, generate transparent summaries, "
    "and formulate follow-up hypotheses."
)
EXPANDED_SCOPE_NOT_CLAIMS = [
    "a binding affinity predictor",
    "an immunogenicity predictor",
    "proof of biological mechanism",
    "a replacement for wet-lab validation",
    "a canonical residue-equivalence system without explicit mapping",
]
EXPANDED_SCOPE_TAKEAWAY = (
    "In practical terms: this framework is meant to support interpretation, prioritization, "
    "and experimental planning, while keeping uncertainty and biological caveats explicit."
)


def brief_scope_markdown() -> str:
    lines = [f"## {SCOPE_HEADING}", "", SCOPE_SUBHEADING, "", "Key points:"]
    lines.extend(f"- {point}" for point in SCOPE_POINTS)
    lines.extend(["", f"Takeaway: {SCOPE_TAKEAWAY}"])
    return "\n".join(lines)


def expanded_scope_markdown() -> str:
    lines = [f"## {EXPANDED_SCOPE_HEADING}", "", SCOPE_SUBHEADING, "", EXPANDED_SCOPE_BODY, "", "It does not claim to be:"]
    lines.extend(f"- {point}" for point in EXPANDED_SCOPE_NOT_CLAIMS)
    lines.extend(["", EXPANDED_SCOPE_TAKEAWAY])
    return "\n".join(lines)
