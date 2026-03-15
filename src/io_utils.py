from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from .input_builder import VariantInputRecord
from .mutation_generator import VariantRecord


def ensure_output_dirs(base_output_dir: Path) -> dict[str, Path]:
    paths = {
        "root": base_output_dir,
        "manifests": base_output_dir / "manifests",
        "inputs": base_output_dir / "colabfold_inputs",
        "fasta": base_output_dir / "colabfold_inputs" / "fastas",
        "predictions": base_output_dir / "predictions",
        "analysis": base_output_dir / "analysis",
        "analysis_prioritization": base_output_dir / "analysis" / "prioritization",
        "analysis_robustness": base_output_dir / "analysis" / "robustness",
        "analysis_benchmarking": base_output_dir / "analysis" / "benchmarking",
        "analysis_panel_design": base_output_dir / "analysis" / "panel_design",
        "report_inputs": base_output_dir / "analysis" / "report_inputs",
        "plots": base_output_dir / "plots",
        "case_studies": base_output_dir / "case_studies",
        "publication_bundle": base_output_dir / "publication_bundle",
        "publication_figures": base_output_dir / "publication_bundle" / "figures",
        "publication_tables": base_output_dir / "publication_bundle" / "tables",
        "publication_manifests": base_output_dir / "publication_bundle" / "manifests",
        "publication_notebook_exports": base_output_dir / "publication_bundle" / "notebook_exports",
        "logs": base_output_dir / "logs",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def write_manifest_csv(variants: Iterable[VariantRecord], manifest_path: Path) -> None:
    rows = [variant.to_dict() for variant in variants]
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "variant_id",
                "local_variant_id",
                "peptide_id",
                "allele_name",
                "wildtype_peptide",
                "mutant_peptide",
                "mutated_position",
                "wt_residue",
                "mut_residue",
                "is_wildtype",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def write_variant_inputs_csv(inputs: list[VariantInputRecord], output_path: Path) -> None:
    fieldnames = [
        "variant_id",
        "local_variant_id",
        "peptide_id",
        "allele_name",
        "chain_a_role",
        "chain_a_length",
        "chain_b_role",
        "chain_b_length",
        "chain_c_role",
        "chain_c_length",
        "peptide_sequence",
        "mutant_peptide",
        "mutated_position",
        "wt_residue",
        "mut_residue",
        "multimer_fasta_path",
        "colabfold_query",
        "resolution_source",
        "metadata_only",
        "resolution_notes",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for variant_input in inputs:
            writer.writerow(variant_input.variant_table_row())


def write_chain_manifest(rows: list[dict[str, object]], output_path: Path) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "variant_id",
                "local_variant_id",
                "peptide_id",
                "allele_name",
                "chain_id",
                "chain_role",
                "sequence_length",
                "sequence_hash",
                "fasta_path",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def write_json(data: dict, output_path: Path) -> None:
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
