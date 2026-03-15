from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import re


@dataclass(frozen=True)
class VariantRecord:
    variant_id: str
    local_variant_id: str
    peptide_id: str
    allele_name: str
    wildtype_peptide: str
    mutant_peptide: str
    mutated_position: int | None
    wt_residue: str | None
    mut_residue: str | None
    is_wildtype: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def generate_single_mutants(
    allele_name: str,
    reference_peptide: str,
    mutation_positions: list[int],
    allowed_amino_acids: list[str],
    peptide_id: str | None = None,
) -> list[VariantRecord]:
    peptide_id = peptide_id or build_peptide_id(reference_peptide)
    variants: list[VariantRecord] = [
        VariantRecord(
            variant_id=build_variant_id(allele_name, peptide_id, "WT"),
            local_variant_id="WT",
            peptide_id=peptide_id,
            allele_name=allele_name,
            wildtype_peptide=reference_peptide,
            mutant_peptide=reference_peptide,
            mutated_position=None,
            wt_residue=None,
            mut_residue=None,
            is_wildtype=True,
        )
    ]

    seen_sequences = {reference_peptide}
    for position in mutation_positions:
        zero_based = position - 1
        wt_residue = reference_peptide[zero_based]
        for mut_residue in allowed_amino_acids:
            if mut_residue == wt_residue:
                continue
            mutant_peptide = (
                reference_peptide[:zero_based] + mut_residue + reference_peptide[zero_based + 1 :]
            )
            if mutant_peptide in seen_sequences:
                continue
            seen_sequences.add(mutant_peptide)
            local_variant_id = f"pos{position}_{wt_residue}to{mut_residue}"
            variants.append(
                VariantRecord(
                    variant_id=build_variant_id(allele_name, peptide_id, local_variant_id),
                    local_variant_id=local_variant_id,
                    peptide_id=peptide_id,
                    allele_name=allele_name,
                    wildtype_peptide=reference_peptide,
                    mutant_peptide=mutant_peptide,
                    mutated_position=position,
                    wt_residue=wt_residue,
                    mut_residue=mut_residue,
                    is_wildtype=False,
                )
            )
    return variants


def build_peptide_id(sequence: str) -> str:
    digest = hashlib.sha1(sequence.encode("utf-8")).hexdigest()[:8]
    return f"pep_{sequence}_{digest}"


def build_variant_id(allele_name: str, peptide_id: str, local_variant_id: str) -> str:
    allele_slug = _slugify(allele_name)
    local_slug = _slugify(local_variant_id)
    return f"{allele_slug}__{peptide_id}__{local_slug}"


def _slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
