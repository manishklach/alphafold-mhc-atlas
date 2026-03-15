from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import pandas as pd

from .allele_fingerprint import (
    build_allele_position_fingerprint,
    build_allele_substitution_fingerprint,
    build_allele_tolerance_fingerprint,
)
from .case_study import run_case_studies
from .cluster_analysis import run_clustering
from .config import AlleleSpec, get_peptides_for_allele, load_config
from .contact_analysis import analyze_variant_structure, merge_structural_results
from .cross_allele_analysis import run_cross_allele_analysis
from .fingerprint import (
    aggregate_tolerance_by_position,
    aggregate_tolerance_by_substitution,
    build_tolerance_fingerprint,
)
from .hypothesis_generation import build_hypotheses, write_hypothesis_evidence
from .input_builder import build_chain_manifest_rows, build_variant_inputs
from .io_utils import ensure_output_dirs, write_chain_manifest, write_manifest_csv, write_variant_inputs_csv
from .metrics import (
    build_confidence_ranking,
    build_position_summary,
    build_substitution_matrix,
    build_substitution_summary,
    build_variant_summary,
)
from .mutation_generator import build_peptide_id, generate_single_mutants
from .parse_predictions import parse_prediction_outputs
from .pocket_region_analysis import build_pocket_region_outputs
from .pocket_signature import build_pocket_signature_residues, build_pocket_signature_summary
from .provenance import build_provenance
from .publication_bundle import write_publication_bundle
from .reporting import (
    build_analysis_snapshot,
    build_figure_manifest,
    build_markdown_report,
    build_publication_tables,
    build_report_summary,
    build_table_manifest,
    write_report_package,
)
from .sequence_resolver import resolve_mhc_sequences
from .structure_utils import load_structure, map_chain_roles
from .visualize import create_plots


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate peptide-MHC inputs, parse predictions, and run cross-allele structural comparisons."
    )
    parser.add_argument("--config", required=True, help="Path to YAML or JSON config file.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    directories = ensure_output_dirs(config.output_dir)

    all_variants = []
    all_variant_inputs = []

    for allele in config.alleles:
        resolved_mhc = resolve_mhc_sequences(allele)
        for peptide_sequence in get_peptides_for_allele(config, allele.allele_name):
            peptide_id = build_peptide_id(peptide_sequence)
            variants = generate_single_mutants(
                allele_name=allele.allele_name,
                reference_peptide=peptide_sequence,
                mutation_positions=config.peptides.mutation_positions,
                allowed_amino_acids=config.peptides.allowed_substitutions,
                peptide_id=peptide_id,
            )
            variant_inputs = build_variant_inputs(
                variants=variants,
                resolved_mhc=resolved_mhc,
                fasta_dir=directories["fasta"],
                write_multimer_fasta=config.prediction_inputs.write_multimer_fasta,
            )
            all_variants.extend(variants)
            all_variant_inputs.extend(variant_inputs)

    write_manifest_csv(all_variants, directories["manifests"] / "manifest.csv")
    if config.prediction_inputs.write_colabfold_csv:
        write_variant_inputs_csv(all_variant_inputs, directories["inputs"] / "variants.csv")
    if config.prediction_inputs.write_chain_manifest:
        write_chain_manifest(build_chain_manifest_rows(all_variant_inputs), directories["inputs"] / "chain_manifest.csv")

    prediction_root = config.parsing.prediction_root or directories["predictions"]
    parsed_records = parse_prediction_outputs(all_variants, prediction_root)
    input_map = {record.variant.variant_id: record for record in all_variant_inputs}
    _attach_input_context(parsed_records, input_map)
    manifest_df = pd.DataFrame([variant.to_dict() for variant in all_variants])

    structural_results = _run_structure_analysis(
        parsed_records=parsed_records,
        variant_inputs=input_map,
        structure_config=config.structure_analysis,
    )
    merged_records = merge_structural_results(parsed_records, structural_results)

    summary_df = build_variant_summary(merged_records, baseline_variant_id=config.analysis.baseline_variant_id)
    summary_output_df = _sanitize_summary_df(summary_df)
    ranking_df = build_confidence_ranking(summary_output_df)
    position_df = build_position_summary(summary_output_df)
    substitution_df = build_substitution_summary(summary_output_df)
    heatmap_df = build_substitution_matrix(summary_output_df)

    chain_map_df = pd.DataFrame([result.chain_map_row for result in structural_results])
    structural_contacts_df = pd.DataFrame([_sanitize_dict(result.structural_contacts_row) for result in structural_results])
    peptide_position_df = pd.DataFrame([row for result in structural_results for row in result.peptide_position_rows])
    heavy_chain_contact_df = pd.DataFrame([row for result in structural_results for row in result.heavy_chain_rows])
    structural_deltas_df = pd.DataFrame([result.structural_deltas_row for result in structural_results])
    peptide_position_df = peptide_position_df.reindex(
        columns=[
            "variant_id",
            "local_variant_id",
            "peptide_id",
            "allele_name",
            "peptide_position",
            "peptide_residue",
            "num_mhc_residues_in_contact",
            "min_distance_to_mhc",
            "contacting_mhc_residue_count",
            "contacting_mhc_residues_serialized",
        ]
    )
    heavy_chain_contact_df = heavy_chain_contact_df.reindex(
        columns=[
            "variant_id",
            "local_variant_id",
            "peptide_id",
            "allele_name",
            "mhc_residue_identifier",
            "mhc_residue_name",
            "num_peptide_positions_contacted",
            "peptide_positions_contacted",
        ]
    )

    fingerprint_df = build_tolerance_fingerprint(summary_output_df, config.structure_analysis)
    tolerance_by_position_df = aggregate_tolerance_by_position(fingerprint_df)
    tolerance_by_substitution_df = aggregate_tolerance_by_substitution(fingerprint_df)
    allele_tolerance_df = build_allele_tolerance_fingerprint(fingerprint_df)
    allele_position_df = build_allele_position_fingerprint(fingerprint_df)
    allele_substitution_df = build_allele_substitution_fingerprint(fingerprint_df)

    pocket_signature_residues_df = build_pocket_signature_residues(
        heavy_chain_contact_df,
        peptide_position_df,
        config.pocket_signature,
    )
    pocket_signature_summary_df = build_pocket_signature_summary(
        pocket_signature_residues_df,
        config.pocket_signature,
    )
    pocket_region_contacts_df, allele_region_signature_df, region_overlap_summary_df = build_pocket_region_outputs(
        heavy_chain_contact_df,
        config.pocket_regions,
        class_type=config.alleles[0].class_type if config.alleles else "I",
    )

    variant_clustering_result = run_clustering(fingerprint_df, config.clustering, directories["plots"])
    cross_allele_result = run_cross_allele_analysis(
        allele_tolerance_df,
        pocket_signature_residues_df,
        allele_position_df,
        config.cross_allele_analysis,
        directories["plots"],
    )

    plot_paths = create_plots(
        summary_df=summary_output_df,
        position_df=position_df,
        heatmap_df=heatmap_df,
        plot_dir=directories["plots"],
        peptide_position_df=peptide_position_df,
        fingerprint_df=fingerprint_df,
    )

    written_outputs = _write_outputs(
        directories=directories,
        summary_output_df=summary_output_df,
        ranking_df=ranking_df,
        position_df=position_df,
        substitution_df=substitution_df,
        heatmap_df=heatmap_df,
        chain_map_df=chain_map_df,
        structural_contacts_df=structural_contacts_df,
        peptide_position_df=peptide_position_df,
        heavy_chain_contact_df=heavy_chain_contact_df,
        structural_deltas_df=structural_deltas_df,
        fingerprint_df=fingerprint_df,
        tolerance_by_position_df=tolerance_by_position_df,
        tolerance_by_substitution_df=tolerance_by_substitution_df,
        allele_tolerance_df=allele_tolerance_df,
        allele_position_df=allele_position_df,
        allele_substitution_df=allele_substitution_df,
        pocket_signature_residues_df=pocket_signature_residues_df,
        pocket_signature_summary_df=pocket_signature_summary_df,
        pocket_region_contacts_df=pocket_region_contacts_df,
        allele_region_signature_df=allele_region_signature_df,
        region_overlap_summary_df=region_overlap_summary_df,
        variant_clustering_result=variant_clustering_result,
        cross_allele_result=cross_allele_result,
    )

    hypotheses_result = build_hypotheses(
        fingerprint_df=fingerprint_df,
        allele_tolerance_df=allele_tolerance_df,
        cross_allele_summary_df=cross_allele_result.cross_allele_summary,
        pocket_signature_summary_df=pocket_signature_summary_df,
        region_overlap_df=region_overlap_summary_df,
        config=config.hypothesis_generation,
    )
    hypotheses_result.hypotheses_df.to_csv(directories["analysis"] / "hypotheses.csv", index=False)
    (directories["analysis"] / "hypotheses.md").write_text(hypotheses_result.markdown, encoding="utf-8")
    write_hypothesis_evidence(
        hypotheses_result.evidence,
        directories["analysis"] / "hypothesis_supporting_evidence.json",
    )
    written_outputs["table_hypothesis_summary.csv"] = directories["analysis"] / "hypotheses.csv"

    publication_tables = build_publication_tables(
        summary_output_df,
        allele_tolerance_df,
        pocket_signature_residues_df,
        hypotheses_result.hypotheses_df,
        directories["analysis"],
    )
    written_outputs.update(publication_tables)

    case_study_results = []
    if config.case_studies_enabled and config.case_studies:
        case_study_results = run_case_studies(
            config.case_studies,
            directories["case_studies"],
            summary_output_df,
            fingerprint_df,
            structural_contacts_df,
            cross_allele_result.cross_allele_summary,
        )

    report_summary = build_report_summary(
        config.project_name,
        manifest_df,
        summary_output_df,
        allele_tolerance_df,
        cross_allele_result.cross_allele_summary,
        hypotheses_result.hypotheses_df,
        case_study_results,
    )
    figure_manifest_df = build_figure_manifest(directories["plots"], config.reporting.core_figure_limit)
    table_manifest_df = build_table_manifest(directories["analysis"], config.reporting.core_table_limit)
    provenance = build_provenance(config.source_config_path, Path(__file__).resolve().parents[1] / "requirements.txt")
    snapshot = build_analysis_snapshot(
        config.project_name,
        manifest_df,
        summary_output_df,
        figure_manifest_df,
        table_manifest_df,
        provenance,
        case_study_results,
        hypotheses_result.hypotheses_df,
    )
    report_markdown = build_markdown_report(
        report_summary,
        case_study_results,
        cross_allele_result.cross_allele_summary,
        hypotheses_result.hypotheses_df,
        caveats=_build_report_caveats(config, summary_output_df, cross_allele_result.ran),
    )
    report_path, report_summary_path = write_report_package(
        directories["analysis"],
        config.reporting,
        report_summary,
        report_markdown,
        figure_manifest_df,
        table_manifest_df,
        snapshot,
    )

    notebook_exports = _build_notebook_exports(
        summary_output_df,
        allele_tolerance_df,
        pocket_signature_residues_df,
        hypotheses_result.hypotheses_df,
        case_study_results,
    )
    if config.publication_bundle.enabled and config.reporting.generate_publication_bundle:
        write_publication_bundle(
            directories["publication_bundle"],
            config.publication_bundle,
            report_path,
            report_summary_path,
            figure_manifest_df.to_dict(orient="records"),
            table_manifest_df.to_dict(orient="records"),
            notebook_exports,
        )

    _print_run_summary(
        output_dir=directories["root"],
        variant_count=len(all_variants),
        allele_count=len(config.alleles),
        prediction_root=prediction_root,
        cross_allele_ran=cross_allele_result.ran,
        variant_clustering_ran=variant_clustering_result.ran,
    )


def _attach_input_context(parsed_records: list[dict[str, object]], input_map: dict[str, object]) -> None:
    for record in parsed_records:
        variant_input = input_map.get(record["variant_id"])
        if variant_input:
            record["allele_name"] = variant_input.variant.allele_name
            record["local_variant_id"] = variant_input.variant.local_variant_id
            record["peptide_id"] = variant_input.variant.peptide_id
            record["wildtype_peptide"] = variant_input.variant.wildtype_peptide
            record["mutant_peptide"] = variant_input.variant.mutant_peptide
            record["mutated_position"] = variant_input.variant.mutated_position
            record["wt_residue"] = variant_input.variant.wt_residue
            record["mut_residue"] = variant_input.variant.mut_residue
            record["is_wildtype"] = variant_input.variant.is_wildtype
            record["metadata_only"] = variant_input.metadata_only
            record["resolution_source"] = variant_input.resolution_source
            record["multimer_fasta_path"] = (
                str(variant_input.multimer_fasta_path) if variant_input.multimer_fasta_path else None
            )


def _run_structure_analysis(parsed_records: list[dict[str, object]], variant_inputs: dict[str, object], structure_config):
    structural_results = []
    precomputed: dict[str, tuple[object, object]] = {}
    grouped_records: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for record in parsed_records:
        grouped_records[(str(record["allele_name"]), str(record["peptide_id"]))].append(record)
        parsed_structure = load_structure(record.get("structure_path")) if structure_config.enabled else None
        chain_map = map_chain_roles(
            variant_id=str(record["variant_id"]),
            parsed_structure=parsed_structure,
            variant_input=variant_inputs.get(str(record["variant_id"])),
            require_confident_mapping=structure_config.require_confident_chain_mapping,
        )
        precomputed[str(record["variant_id"])] = (parsed_structure, chain_map)

    baseline_results: dict[tuple[str, str], object] = {}
    for key, records in grouped_records.items():
        wt_record = next((record for record in records if str(record.get("local_variant_id")) == "WT"), None)
        if wt_record is None:
            continue
        parsed_structure, chain_map = precomputed[str(wt_record["variant_id"])]
        baseline_results[key] = analyze_variant_structure(
            wt_record,
            parsed_structure,
            chain_map,
            structure_config,
            baseline_result=None,
        )

    for record in parsed_records:
        parsed_structure, chain_map = precomputed[str(record["variant_id"])]
        baseline_result = baseline_results.get((str(record["allele_name"]), str(record["peptide_id"])))
        if str(record.get("local_variant_id")) == "WT":
            baseline_result = baseline_result
        result = analyze_variant_structure(
            record,
            parsed_structure,
            chain_map,
            structure_config,
            baseline_result=baseline_result if str(record.get("local_variant_id")) != "WT" else baseline_result,
        )
        structural_results.append(result)
    return structural_results


def _write_outputs(**kwargs) -> None:
    directories = kwargs["directories"]
    written_paths: dict[str, Path] = {}
    _write_df(kwargs["summary_output_df"], directories["analysis"] / "summary.csv", written_paths)
    _write_df(kwargs["summary_output_df"], directories["analysis"] / "variant_summary.csv", written_paths)
    _write_df(kwargs["ranking_df"], directories["analysis"] / "confidence_ranking.csv", written_paths)
    _write_df(kwargs["position_df"], directories["analysis"] / "position_summary.csv", written_paths)
    _write_df(kwargs["substitution_df"], directories["analysis"] / "substitution_summary.csv", written_paths)
    _write_df(kwargs["chain_map_df"], directories["analysis"] / "structure_chain_map.csv", written_paths)
    _write_df(kwargs["structural_contacts_df"], directories["analysis"] / "structural_contacts.csv", written_paths)
    _write_df(kwargs["peptide_position_df"], directories["analysis"] / "peptide_position_contacts.csv", written_paths)
    _write_df(kwargs["heavy_chain_contact_df"], directories["analysis"] / "heavy_chain_contact_residues.csv", written_paths)
    _write_df(kwargs["structural_deltas_df"], directories["analysis"] / "structural_deltas.csv", written_paths)
    _write_df(kwargs["fingerprint_df"], directories["analysis"] / "tolerance_fingerprint.csv", written_paths)
    _write_df(kwargs["tolerance_by_position_df"], directories["analysis"] / "tolerance_by_position.csv", written_paths)
    _write_df(
        kwargs["tolerance_by_substitution_df"],
        directories["analysis"] / "tolerance_by_substitution.csv",
        written_paths,
    )
    _write_df(kwargs["allele_tolerance_df"], directories["analysis"] / "allele_tolerance_fingerprint.csv", written_paths)
    _write_df(kwargs["allele_position_df"], directories["analysis"] / "allele_position_fingerprint.csv", written_paths)
    _write_df(
        kwargs["allele_substitution_df"],
        directories["analysis"] / "allele_substitution_fingerprint.csv",
        written_paths,
    )
    _write_df(
        kwargs["pocket_signature_residues_df"],
        directories["analysis"] / "pocket_signature_residues.csv",
        written_paths,
    )
    _write_df(
        kwargs["pocket_signature_summary_df"],
        directories["analysis"] / "pocket_signature_summary.csv",
        written_paths,
    )
    _write_df(
        kwargs["pocket_region_contacts_df"],
        directories["analysis"] / "pocket_region_contacts.csv",
        written_paths,
    )
    _write_df(
        kwargs["allele_region_signature_df"],
        directories["analysis"] / "allele_region_signature.csv",
        written_paths,
    )
    _write_df(
        kwargs["region_overlap_summary_df"],
        directories["analysis"] / "region_overlap_summary.csv",
        written_paths,
    )
    if not kwargs["heatmap_df"].empty:
        kwargs["heatmap_df"].to_csv(directories["analysis"] / "substitution_heatmap.csv")
        written_paths["substitution_heatmap.csv"] = directories["analysis"] / "substitution_heatmap.csv"

    variant_clustering_result = kwargs["variant_clustering_result"]
    if variant_clustering_result.distance_matrix is not None:
        variant_clustering_result.distance_matrix.to_csv(directories["analysis"] / "fingerprint_distance_matrix.csv")
        written_paths["fingerprint_distance_matrix.csv"] = directories["analysis"] / "fingerprint_distance_matrix.csv"
    if variant_clustering_result.projection_df is not None:
        variant_clustering_result.projection_df.to_csv(
            directories["analysis"] / "fingerprint_projection.csv",
            index=False,
        )
        written_paths["fingerprint_projection.csv"] = directories["analysis"] / "fingerprint_projection.csv"
    pd.DataFrame([{"ran": variant_clustering_result.ran, "notes": variant_clustering_result.notes}]).to_csv(
        directories["analysis"] / "clustering_status.csv",
        index=False,
    )
    written_paths["clustering_status.csv"] = directories["analysis"] / "clustering_status.csv"

    cross_allele_result = kwargs["cross_allele_result"]
    _write_df(cross_allele_result.feature_table, directories["analysis"] / "cross_allele_feature_table.csv", written_paths)
    _write_df(cross_allele_result.allele_similarity_matrix, directories["analysis"] / "allele_similarity_matrix.csv", written_paths, index=True)
    _write_df(
        cross_allele_result.allele_tolerance_distance_matrix,
        directories["analysis"] / "allele_tolerance_distance_matrix.csv",
        written_paths,
        index=True,
    )
    _write_df(
        cross_allele_result.allele_pocket_jaccard_matrix,
        directories["analysis"] / "allele_pocket_jaccard_matrix.csv",
        written_paths,
        index=True,
    )
    _write_df(cross_allele_result.pocket_overlap_residues, directories["analysis"] / "pocket_overlap_residues.csv", written_paths)
    _write_df(cross_allele_result.shared_contact_residues, directories["analysis"] / "shared_contact_residues.csv", written_paths)
    _write_df(
        cross_allele_result.allele_unique_contact_residues,
        directories["analysis"] / "allele_unique_contact_residues.csv",
        written_paths,
    )
    _write_df(cross_allele_result.cross_allele_summary, directories["analysis"] / "cross_allele_summary.csv", written_paths)
    _write_df(
        cross_allele_result.allele_comparison_summary,
        directories["analysis"] / "allele_comparison_summary.csv",
        written_paths,
    )
    return written_paths


def _write_df(df: pd.DataFrame, path: Path, written_paths: dict[str, Path], index: bool = False) -> None:
    df.to_csv(path, index=index)
    written_paths[path.name] = path


def _sanitize_summary_df(summary_df: pd.DataFrame) -> pd.DataFrame:
    if summary_df.empty:
        return summary_df
    removable = [column for column in summary_df.columns if column.startswith("_")]
    return summary_df.drop(columns=removable, errors="ignore")


def _sanitize_dict(data: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in data.items() if not key.startswith("_")}


def _print_run_summary(
    output_dir: Path,
    variant_count: int,
    allele_count: int,
    prediction_root: Path,
    cross_allele_ran: bool,
    variant_clustering_ran: bool,
) -> None:
    print(f"Generated {variant_count} variants across {allele_count} allele(s).")
    print(f"Outputs written under: {output_dir}")
    print(f"Prediction root scanned: {prediction_root}")
    print(f"Variant clustering ran: {variant_clustering_ran}")
    print(f"Cross-allele analysis ran: {cross_allele_ran}")


def _build_notebook_exports(
    summary_df: pd.DataFrame,
    allele_tolerance_df: pd.DataFrame,
    pocket_signature_residues_df: pd.DataFrame,
    hypotheses_df: pd.DataFrame,
    case_study_results: list[dict[str, object]],
) -> dict[str, pd.DataFrame | dict[str, object]]:
    return {
        "notebook_variant_summary.csv": summary_df,
        "notebook_allele_summary.csv": allele_tolerance_df,
        "notebook_pocket_signature.csv": pocket_signature_residues_df,
        "notebook_hypotheses.csv": hypotheses_df,
        "notebook_case_studies.json": {"case_studies": case_study_results},
    }


def _build_report_caveats(config, summary_df: pd.DataFrame, cross_allele_ran: bool) -> list[str]:
    caveats = [
        "These outputs summarize predicted structures and derived contact features only; they are not binding-affinity or immunogenicity predictions.",
        "Cross-allele residue comparisons remain raw-identifier based unless a user-defined pocket-region mapping is provided.",
        "Small geometric differences should be treated as exploratory, especially when structure coverage is incomplete.",
    ]
    if "structure_path" in summary_df.columns and summary_df["structure_path"].isna().all():
        caveats.append("No structure files were available, so structural interpretations are absent for this run.")
    if not cross_allele_ran:
        caveats.append("Cross-allele similarity outputs were skipped because the run did not meet the required allele/data thresholds.")
    if config.pocket_regions.enabled and not config.pocket_regions.mapping_file:
        caveats.append("Pocket-region analysis was requested without a mapping file, so no region-level comparisons were generated.")
    return caveats


if __name__ == "__main__":
    main()
