from __future__ import annotations

from Bio.Seq import Seq


def normalize_peptide(sequence: str) -> str:
    return str(Seq(sequence.strip().upper()))
