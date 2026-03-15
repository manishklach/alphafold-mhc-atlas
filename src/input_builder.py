from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from .mutation_generator import VariantRecord
from .sequence_resolver import ResolvedMHCSequences


@dataclass(frozen=True)
class ChainRecord:
    variant_id: str
    chain_id: str
    chain_role: str
    sequence: str
    fasta_path: Path | None

    @property
    def sequence_length(self) -> int:
        return len(self.sequence)

    @property
    def sequence_hash(self) -> str:
        return hashlib.sha256(self.sequence.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class VariantInputRecord:
    variant: VariantRecord
    chain_records: list[ChainRecord]
    multimer_fasta_path: Path | None
    colabfold_query: str | None
    resolution_source: str
    resolution_notes: str | None
    metadata_only: bool

    def variant_table_row(self) -> dict[str, object]:
        chain_map = {chain.chain_id: chain for chain in self.chain_records}
        return {
            "variant_id": self.variant.variant_id,
            "local_variant_id": self.variant.local_variant_id,
            "peptide_id": self.variant.peptide_id,
            "allele_name": self.variant.allele_name,
            "chain_a_role": chain_map.get("A").chain_role if chain_map.get("A") else None,
            "chain_a_length": chain_map.get("A").sequence_length if chain_map.get("A") else None,
            "chain_b_role": chain_map.get("B").chain_role if chain_map.get("B") else None,
            "chain_b_length": chain_map.get("B").sequence_length if chain_map.get("B") else None,
            "chain_c_role": chain_map.get("C").chain_role if chain_map.get("C") else None,
            "chain_c_length": chain_map.get("C").sequence_length if chain_map.get("C") else None,
            "peptide_sequence": self.variant.wildtype_peptide,
            "mutant_peptide": self.variant.mutant_peptide,
            "mutated_position": self.variant.mutated_position,
            "wt_residue": self.variant.wt_residue,
            "mut_residue": self.variant.mut_residue,
            "multimer_fasta_path": str(self.multimer_fasta_path) if self.multimer_fasta_path else None,
            "colabfold_query": self.colabfold_query,
            "resolution_source": self.resolution_source,
            "metadata_only": self.metadata_only,
            "resolution_notes": self.resolution_notes,
        }


def build_variant_inputs(
    variants: list[VariantRecord],
    resolved_mhc: ResolvedMHCSequences,
    fasta_dir: Path,
    write_multimer_fasta: bool,
) -> list[VariantInputRecord]:
    input_records: list[VariantInputRecord] = []
    for variant in variants:
        chain_records = _build_chain_records(variant, resolved_mhc)
        fasta_path = None
        query = None
        if chain_records:
            query = build_colabfold_query(chain_records)
            if write_multimer_fasta:
                fasta_path = fasta_dir / f"{variant.variant_id}.fasta"
                fasta_path.write_text(build_multimer_fasta_text(variant.variant_id, chain_records), encoding="utf-8")
        input_records.append(
            VariantInputRecord(
                variant=variant,
                chain_records=chain_records,
                multimer_fasta_path=fasta_path,
                colabfold_query=query,
                resolution_source=resolved_mhc.source,
                resolution_notes="; ".join(resolved_mhc.notes) if resolved_mhc.notes else None,
                metadata_only=resolved_mhc.metadata_only,
            )
        )
    return input_records


def build_multimer_fasta_text(variant_id: str, chains: list[ChainRecord]) -> str:
    lines: list[str] = []
    for chain in chains:
        lines.append(f">{variant_id}|chain={chain.chain_id}|role={chain.chain_role}")
        lines.append(chain.sequence)
    return "\n".join(lines) + "\n"


def build_colabfold_query(chains: list[ChainRecord]) -> str:
    return ":".join(chain.sequence for chain in chains)


def build_chain_manifest_rows(inputs: list[VariantInputRecord]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for variant_input in inputs:
        for chain in variant_input.chain_records:
            rows.append(
                {
                    "variant_id": variant_input.variant.variant_id,
                    "local_variant_id": variant_input.variant.local_variant_id,
                    "peptide_id": variant_input.variant.peptide_id,
                    "allele_name": variant_input.variant.allele_name,
                    "chain_id": chain.chain_id,
                    "chain_role": chain.chain_role,
                    "sequence_length": chain.sequence_length,
                    "sequence_hash": chain.sequence_hash,
                    "fasta_path": str(variant_input.multimer_fasta_path) if variant_input.multimer_fasta_path else None,
                }
            )
    return rows


def _build_chain_records(variant: VariantRecord, resolved_mhc: ResolvedMHCSequences) -> list[ChainRecord]:
    if not resolved_mhc.resolved or not resolved_mhc.heavy_chain_sequence or not resolved_mhc.beta2m_sequence:
        return []
    return [
        ChainRecord(variant.variant_id, "A", "mhc_heavy_chain", resolved_mhc.heavy_chain_sequence, None),
        ChainRecord(variant.variant_id, "B", "beta2m", resolved_mhc.beta2m_sequence, None),
        ChainRecord(variant.variant_id, "C", "peptide", variant.mutant_peptide, None),
    ]
