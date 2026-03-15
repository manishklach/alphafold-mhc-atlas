from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import yaml


AMINO_ACIDS = set("ACDEFGHIKLMNPQRSTVWY")


@dataclass(frozen=True)
class AlleleSpec:
    allele_name: str
    class_type: str
    heavy_chain_sequence: str | None
    beta2m_sequence: str | None
    reference_file: Path | None
    allow_metadata_only_fallback: bool


@dataclass(frozen=True)
class PeptidePanelConfig:
    mode: str
    wildtype_sequences: list[str]
    mutation_positions: list[int]
    allowed_substitutions: list[str]
    allele_specific_sequences: dict[str, list[str]]


@dataclass(frozen=True)
class PredictionInputConfig:
    write_multimer_fasta: bool
    write_chain_manifest: bool
    write_colabfold_csv: bool


@dataclass(frozen=True)
class ParsingConfig:
    prediction_root: Path | None


@dataclass(frozen=True)
class AnalysisConfig:
    baseline_variant_id: str


@dataclass(frozen=True)
class StructureAnalysisConfig:
    enabled: bool
    contact_distance_angstrom: float
    use_all_atom_contacts: bool
    fallback_to_ca_distance: bool
    compute_wt_deltas: bool
    compute_optional_geometry_metrics: bool
    mutated_positions_of_interest: list[int]
    anchor_positions: list[int]
    require_confident_chain_mapping: bool


@dataclass(frozen=True)
class ClusteringConfig:
    enabled: bool
    min_variants_required: int
    features: list[str]
    standardize: bool


@dataclass(frozen=True)
class CrossAlleleAnalysisConfig:
    enabled: bool
    require_min_alleles: int
    compare_pocket_signatures: bool
    compare_tolerance_fingerprints: bool
    compare_anchor_patterns: bool
    use_combined_similarity: bool
    numeric_metric: str
    set_based_metric: str
    standardize_numeric_features: bool


@dataclass(frozen=True)
class PocketSignatureConfig:
    enabled: bool
    min_contact_frequency: int
    anchor_positions: list[int]
    compute_anchor_specific_signatures: bool
    require_confident_chain_mapping: bool


@dataclass(frozen=True)
class MultiAlleleConfig:
    shared_mutation_panel: bool
    allele_specific_reference_peptides: bool


@dataclass(frozen=True)
class ReportingConfig:
    enabled: bool
    generate_markdown_report: bool
    generate_publication_bundle: bool
    include_case_studies: bool
    include_hypotheses: bool
    core_figure_limit: int
    core_table_limit: int


@dataclass(frozen=True)
class HypothesisGenerationConfig:
    enabled: bool
    min_supporting_variants: int
    min_supporting_alleles: int
    include_low_confidence_hypotheses: bool
    require_structural_support: bool
    categories: list[str]


@dataclass(frozen=True)
class PocketRegionsConfig:
    enabled: bool
    mapping_file: Path | None
    require_region_mapping_for_comparison: bool


@dataclass(frozen=True)
class PublicationBundleConfig:
    enabled: bool
    include_notebook_exports: bool
    copy_figures: bool
    copy_tables: bool


@dataclass(frozen=True)
class RankingFeatureConfig:
    name: str
    weight: float


@dataclass(frozen=True)
class RankingModeConfig:
    enabled: bool
    normalize_features: bool
    require_structural_support: bool
    features: list[RankingFeatureConfig]


@dataclass(frozen=True)
class PrioritizationConfig:
    enabled: bool
    default_top_k: int
    ranking_modes: dict[str, RankingModeConfig]


@dataclass(frozen=True)
class UncertaintyConfig:
    enabled: bool
    penalize_missing_features: bool
    penalize_unconfident_chain_mapping: bool


@dataclass(frozen=True)
class RobustnessConfig:
    enabled: bool
    contact_distance_thresholds: list[float]
    weight_perturbation_fraction: float
    missing_feature_drop_tests: bool
    replicate_consistency: bool
    compare_top_k: list[int]


@dataclass(frozen=True)
class BenchmarkingConfig:
    enabled: bool
    reference_structure_map: Path | None
    known_disruptive_variants_file: Path | None
    expected_anchor_positions: list[int]


@dataclass(frozen=True)
class DiversityConstraintsConfig:
    max_variants_per_position: int
    max_variants_per_allele: int
    max_variants_per_substitution: int


@dataclass(frozen=True)
class PanelDesignConfig:
    enabled: bool
    max_panel_size: int
    ranking_goal: str
    require_min_evidence_coverage: float
    penalize_high_uncertainty: bool
    diversity_constraints: DiversityConstraintsConfig
    redundancy_features: list[str]


@dataclass(frozen=True)
class InteractiveAppConfig:
    enabled: bool
    framework: str
    default_project: Path | None
    enable_demo_mode: bool
    enable_scenario_saving: bool
    max_rows_preview: int


@dataclass(frozen=True)
class ScenarioAnalysisConfig:
    enabled: bool
    default_evidence_coverage_threshold: float
    default_uncertainty_levels_allowed: list[str]
    allow_custom_filters: bool
    allow_side_by_side_comparison: bool


@dataclass(frozen=True)
class DemoModeConfig:
    enabled: bool
    default_demo_project: str | None


@dataclass(frozen=True)
class ScenarioTemplatesConfig:
    enabled: bool
    template_file: Path | None


@dataclass(frozen=True)
class CaseStudySpec:
    case_id: str
    description: str
    alleles: list[str]
    peptides: list[str]
    mutation_positions: list[int]
    substitutions: list[str]
    variants: list[str]


@dataclass(frozen=True)
class ProjectConfig:
    project_name: str
    output_dir: Path
    alleles: list[AlleleSpec]
    peptides: PeptidePanelConfig
    prediction_inputs: PredictionInputConfig
    parsing: ParsingConfig
    analysis: AnalysisConfig
    structure_analysis: StructureAnalysisConfig
    clustering: ClusteringConfig
    cross_allele_analysis: CrossAlleleAnalysisConfig
    pocket_signature: PocketSignatureConfig
    multi_allele: MultiAlleleConfig
    reporting: ReportingConfig
    hypothesis_generation: HypothesisGenerationConfig
    pocket_regions: PocketRegionsConfig
    publication_bundle: PublicationBundleConfig
    prioritization: PrioritizationConfig
    uncertainty: UncertaintyConfig
    robustness: RobustnessConfig
    benchmarking: BenchmarkingConfig
    panel_design: PanelDesignConfig
    interactive_app: InteractiveAppConfig
    scenario_analysis: ScenarioAnalysisConfig
    demo_mode: DemoModeConfig
    scenario_templates: ScenarioTemplatesConfig
    case_studies_enabled: bool
    case_studies: list[CaseStudySpec]
    source_config_path: Path


def load_config(config_path: str | Path) -> ProjectConfig:
    path = Path(config_path).resolve()
    data = _load_raw_config(path)
    normalized = _normalize_config_shape(data)
    return _build_project_config(path, normalized)


def _load_raw_config(config_path: Path) -> dict[str, Any]:
    suffix = config_path.suffix.lower()
    text = config_path.read_text(encoding="utf-8")

    if suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(text)
    elif suffix == ".json":
        data = json.loads(text)
    else:
        raise ValueError(f"Unsupported config extension: {config_path.suffix}")

    if not isinstance(data, dict):
        raise ValueError("Config must deserialize to an object.")
    return data


def _normalize_config_shape(data: dict[str, Any]) -> dict[str, Any]:
    if "alleles" in data and "peptides" in data:
        return data

    if "mhc" in data and "peptide" in data:
        mhc = data["mhc"]
        peptide = data["peptide"]
        return {
            "project_name": data.get("project_name") or "phase2_compatible_run",
            "output_dir": data["output_dir"],
            "alleles": [mhc],
            "peptides": {
                "mode": "shared_panel",
                "wildtype_sequences": [peptide["wildtype_sequence"]],
                "mutation_positions": peptide["mutation_positions"],
                "allowed_substitutions": peptide["allowed_substitutions"],
            },
            "prediction_inputs": data.get("prediction_inputs", {}),
            "parsing": data.get("parsing", {}),
            "analysis": data.get("analysis", {}),
            "structure_analysis": data.get("structure_analysis", {}),
            "clustering": data.get("clustering", {}),
            "cross_allele_analysis": data.get("cross_allele_analysis", {}),
            "pocket_signature": data.get("pocket_signature", {}),
            "multi_allele": data.get("multi_allele", {}),
            "reporting": data.get("reporting", {}),
            "hypothesis_generation": data.get("hypothesis_generation", {}),
            "pocket_regions": data.get("pocket_regions", {}),
            "publication_bundle": data.get("publication_bundle", {}),
            "prioritization": data.get("prioritization", {}),
            "uncertainty": data.get("uncertainty", {}),
            "robustness": data.get("robustness", {}),
            "benchmarking": data.get("benchmarking", {}),
            "panel_design": data.get("panel_design", {}),
            "interactive_app": data.get("interactive_app", {}),
            "scenario_analysis": data.get("scenario_analysis", {}),
            "demo_mode": data.get("demo_mode", {}),
            "scenario_templates": data.get("scenario_templates", {}),
            "case_studies": data.get("case_studies", []),
        }

    return {
        "project_name": data.get("project_name") or "phase1_compatible_run",
        "output_dir": data["output_dir"],
        "alleles": [
            {
                "allele_name": str(data.get("allele_name", "")).strip(),
                "class_type": data.get("class_type") or "I",
                "heavy_chain_sequence": data.get("heavy_chain_sequence"),
                "beta2m_sequence": data.get("beta2m_sequence"),
                "reference_file": data.get("reference_file"),
                "allow_metadata_only_fallback": bool(data.get("allow_metadata_only_fallback", True)),
            }
        ],
        "peptides": {
            "mode": "shared_panel",
            "wildtype_sequences": [data["reference_peptide"]],
            "mutation_positions": data["mutation_positions"],
            "allowed_substitutions": data["allowed_amino_acids"],
        },
        "prediction_inputs": {
            "write_multimer_fasta": True,
            "write_chain_manifest": True,
            "write_colabfold_csv": True,
        },
        "parsing": {"prediction_root": data.get("prediction_root")},
        "analysis": {"baseline_variant_id": data.get("baseline_variant_id", "WT")},
        "structure_analysis": {},
        "clustering": {},
        "cross_allele_analysis": {},
        "pocket_signature": {},
        "multi_allele": {},
        "reporting": {},
        "hypothesis_generation": {},
        "pocket_regions": {},
        "publication_bundle": {},
        "prioritization": {},
        "uncertainty": {},
        "robustness": {},
        "benchmarking": {},
        "panel_design": {},
        "interactive_app": {},
        "scenario_analysis": {},
        "demo_mode": {},
        "scenario_templates": {},
        "case_studies": [],
    }


def _build_project_config(config_path: Path, data: dict[str, Any]) -> ProjectConfig:
    project_name = str(data.get("project_name") or config_path.stem).strip()
    output_dir = _resolve_path(config_path.parent, data["output_dir"])

    alleles_raw = data.get("alleles")
    if not isinstance(alleles_raw, list) or not alleles_raw:
        raise ValueError("Config field 'alleles' must be a non-empty list.")
    peptide_raw = _require_mapping(data, "peptides")
    prediction_inputs_raw = _require_mapping(data, "prediction_inputs", optional=True) or {}
    parsing_raw = _require_mapping(data, "parsing", optional=True) or {}
    analysis_raw = _require_mapping(data, "analysis", optional=True) or {}
    structure_analysis_raw = _require_mapping(data, "structure_analysis", optional=True) or {}
    clustering_raw = _require_mapping(data, "clustering", optional=True) or {}
    cross_allele_raw = _require_mapping(data, "cross_allele_analysis", optional=True) or {}
    pocket_raw = _require_mapping(data, "pocket_signature", optional=True) or {}
    multi_allele_raw = _require_mapping(data, "multi_allele", optional=True) or {}
    reporting_raw = _require_mapping(data, "reporting", optional=True) or {}
    hypothesis_raw = _require_mapping(data, "hypothesis_generation", optional=True) or {}
    pocket_regions_raw = _require_mapping(data, "pocket_regions", optional=True) or {}
    publication_bundle_raw = _require_mapping(data, "publication_bundle", optional=True) or {}
    prioritization_raw = _require_mapping(data, "prioritization", optional=True) or {}
    uncertainty_raw = _require_mapping(data, "uncertainty", optional=True) or {}
    robustness_raw = _require_mapping(data, "robustness", optional=True) or {}
    benchmarking_raw = _require_mapping(data, "benchmarking", optional=True) or {}
    panel_design_raw = _require_mapping(data, "panel_design", optional=True) or {}
    interactive_app_raw = _require_mapping(data, "interactive_app", optional=True) or {}
    scenario_analysis_raw = _require_mapping(data, "scenario_analysis", optional=True) or {}
    demo_mode_raw = _require_mapping(data, "demo_mode", optional=True) or {}
    scenario_templates_raw = _require_mapping(data, "scenario_templates", optional=True) or {}
    case_studies_value = data.get("case_studies", [])

    alleles = [_build_allele_spec(config_path.parent, entry, index) for index, entry in enumerate(alleles_raw)]
    peptides = _build_peptide_panel(peptide_raw)
    prediction_inputs = PredictionInputConfig(
        write_multimer_fasta=bool(prediction_inputs_raw.get("write_multimer_fasta", True)),
        write_chain_manifest=bool(prediction_inputs_raw.get("write_chain_manifest", True)),
        write_colabfold_csv=bool(prediction_inputs_raw.get("write_colabfold_csv", True)),
    )
    parsing = ParsingConfig(
        prediction_root=_resolve_optional_path(config_path.parent, parsing_raw.get("prediction_root")),
    )
    analysis = AnalysisConfig(
        baseline_variant_id=str(analysis_raw.get("baseline_variant_id") or "WT").strip(),
    )
    structure_analysis = StructureAnalysisConfig(
        enabled=bool(structure_analysis_raw.get("enabled", True)),
        contact_distance_angstrom=float(structure_analysis_raw.get("contact_distance_angstrom", 4.5)),
        use_all_atom_contacts=bool(structure_analysis_raw.get("use_all_atom_contacts", True)),
        fallback_to_ca_distance=bool(structure_analysis_raw.get("fallback_to_ca_distance", True)),
        compute_wt_deltas=bool(structure_analysis_raw.get("compute_wt_deltas", True)),
        compute_optional_geometry_metrics=bool(
            structure_analysis_raw.get("compute_optional_geometry_metrics", True)
        ),
        mutated_positions_of_interest=_normalize_optional_positions(
            structure_analysis_raw.get("mutated_positions_of_interest", []),
            "structure_analysis.mutated_positions_of_interest",
        ),
        anchor_positions=_normalize_optional_positions(
            structure_analysis_raw.get("anchor_positions", []),
            "structure_analysis.anchor_positions",
        ),
        require_confident_chain_mapping=bool(
            structure_analysis_raw.get("require_confident_chain_mapping", True)
        ),
    )
    clustering = ClusteringConfig(
        enabled=bool(clustering_raw.get("enabled", True)),
        min_variants_required=int(clustering_raw.get("min_variants_required", 5)),
        features=_normalize_string_list(
            clustering_raw.get(
                "features",
                [
                    "delta_confidence_vs_wt",
                    "delta_total_contacts_vs_wt",
                    "delta_mean_min_distance_vs_wt",
                    "delta_contacts_at_mutated_position_vs_wt",
                ],
            ),
            "clustering.features",
        ),
        standardize=bool(clustering_raw.get("standardize", True)),
    )
    cross_allele_analysis = CrossAlleleAnalysisConfig(
        enabled=bool(cross_allele_raw.get("enabled", True)),
        require_min_alleles=int(cross_allele_raw.get("require_min_alleles", 2)),
        compare_pocket_signatures=bool(cross_allele_raw.get("compare_pocket_signatures", True)),
        compare_tolerance_fingerprints=bool(cross_allele_raw.get("compare_tolerance_fingerprints", True)),
        compare_anchor_patterns=bool(cross_allele_raw.get("compare_anchor_patterns", True)),
        use_combined_similarity=bool(cross_allele_raw.get("use_combined_similarity", True)),
        numeric_metric=str(cross_allele_raw.get("similarity_metrics", {}).get("numeric", "euclidean")).strip(),
        set_based_metric=str(cross_allele_raw.get("similarity_metrics", {}).get("set_based", "jaccard")).strip(),
        standardize_numeric_features=bool(cross_allele_raw.get("standardize_numeric_features", True)),
    )
    pocket_signature = PocketSignatureConfig(
        enabled=bool(pocket_raw.get("enabled", True)),
        min_contact_frequency=int(pocket_raw.get("min_contact_frequency", 1)),
        anchor_positions=_normalize_optional_positions(
            pocket_raw.get("anchor_positions", structure_analysis.anchor_positions),
            "pocket_signature.anchor_positions",
        ),
        compute_anchor_specific_signatures=bool(pocket_raw.get("compute_anchor_specific_signatures", True)),
        require_confident_chain_mapping=bool(pocket_raw.get("require_confident_chain_mapping", True)),
    )
    multi_allele = MultiAlleleConfig(
        shared_mutation_panel=bool(multi_allele_raw.get("shared_mutation_panel", True)),
        allele_specific_reference_peptides=bool(
            multi_allele_raw.get("allele_specific_reference_peptides", peptides.mode == "allele_specific")
        ),
    )
    reporting = ReportingConfig(
        enabled=bool(reporting_raw.get("enabled", True)),
        generate_markdown_report=bool(reporting_raw.get("generate_markdown_report", True)),
        generate_publication_bundle=bool(reporting_raw.get("generate_publication_bundle", True)),
        include_case_studies=bool(reporting_raw.get("include_case_studies", True)),
        include_hypotheses=bool(reporting_raw.get("include_hypotheses", True)),
        core_figure_limit=int(reporting_raw.get("core_figure_limit", 8)),
        core_table_limit=int(reporting_raw.get("core_table_limit", 8)),
    )
    hypothesis_generation = HypothesisGenerationConfig(
        enabled=bool(hypothesis_raw.get("enabled", True)),
        min_supporting_variants=int(hypothesis_raw.get("min_supporting_variants", 3)),
        min_supporting_alleles=int(hypothesis_raw.get("min_supporting_alleles", 2)),
        include_low_confidence_hypotheses=bool(hypothesis_raw.get("include_low_confidence_hypotheses", True)),
        require_structural_support=bool(hypothesis_raw.get("require_structural_support", False)),
        categories=_normalize_string_list(
            hypothesis_raw.get(
                "categories",
                [
                    "shared_tolerance_pattern",
                    "anchor_disruption_pattern",
                    "aromatic_substitution_effect",
                    "allele_specific_contact_network",
                    "pocket_region_sensitivity",
                ],
            ),
            "hypothesis_generation.categories",
        ),
    )
    pocket_regions = PocketRegionsConfig(
        enabled=bool(pocket_regions_raw.get("enabled", False)),
        mapping_file=_resolve_optional_path(config_path.parent, pocket_regions_raw.get("mapping_file")),
        require_region_mapping_for_comparison=bool(
            pocket_regions_raw.get("require_region_mapping_for_comparison", False)
        ),
    )
    publication_bundle = PublicationBundleConfig(
        enabled=bool(publication_bundle_raw.get("enabled", True)),
        include_notebook_exports=bool(publication_bundle_raw.get("include_notebook_exports", True)),
        copy_figures=bool(publication_bundle_raw.get("copy_figures", True)),
        copy_tables=bool(publication_bundle_raw.get("copy_tables", True)),
    )
    prioritization = PrioritizationConfig(
        enabled=bool(prioritization_raw.get("enabled", True)),
        default_top_k=int(prioritization_raw.get("default_top_k", 10)),
        ranking_modes=_build_ranking_modes(prioritization_raw.get("ranking_modes", {})),
    )
    uncertainty = UncertaintyConfig(
        enabled=bool(uncertainty_raw.get("enabled", True)),
        penalize_missing_features=bool(uncertainty_raw.get("penalize_missing_features", True)),
        penalize_unconfident_chain_mapping=bool(
            uncertainty_raw.get("penalize_unconfident_chain_mapping", True)
        ),
    )
    robustness = RobustnessConfig(
        enabled=bool(robustness_raw.get("enabled", True)),
        contact_distance_thresholds=_normalize_optional_float_list(
            robustness_raw.get("contact_distance_thresholds", [4.0, 4.5, 5.0]),
            "robustness.contact_distance_thresholds",
        ),
        weight_perturbation_fraction=float(robustness_raw.get("weight_perturbation_fraction", 0.2)),
        missing_feature_drop_tests=bool(robustness_raw.get("missing_feature_drop_tests", True)),
        replicate_consistency=bool(robustness_raw.get("replicate_consistency", True)),
        compare_top_k=_normalize_positive_integer_list(
            robustness_raw.get("compare_top_k", [5, 10]),
            "robustness.compare_top_k",
        ),
    )
    benchmarking = BenchmarkingConfig(
        enabled=bool(benchmarking_raw.get("enabled", True)),
        reference_structure_map=_resolve_optional_path(config_path.parent, benchmarking_raw.get("reference_structure_map")),
        known_disruptive_variants_file=_resolve_optional_path(
            config_path.parent,
            benchmarking_raw.get("known_disruptive_variants_file"),
        ),
        expected_anchor_positions=_normalize_optional_positions(
            benchmarking_raw.get("expected_anchor_positions", structure_analysis.anchor_positions),
            "benchmarking.expected_anchor_positions",
        ),
    )
    panel_design = PanelDesignConfig(
        enabled=bool(panel_design_raw.get("enabled", True)),
        max_panel_size=int(panel_design_raw.get("max_panel_size", 12)),
        ranking_goal=str(panel_design_raw.get("ranking_goal") or "balanced_exploration_panel").strip(),
        require_min_evidence_coverage=float(panel_design_raw.get("require_min_evidence_coverage", 0.5)),
        penalize_high_uncertainty=bool(panel_design_raw.get("penalize_high_uncertainty", True)),
        diversity_constraints=DiversityConstraintsConfig(
            max_variants_per_position=int(
                panel_design_raw.get("diversity_constraints", {}).get("max_variants_per_position", 3)
            ),
            max_variants_per_allele=int(
                panel_design_raw.get("diversity_constraints", {}).get("max_variants_per_allele", 4)
            ),
            max_variants_per_substitution=int(
                panel_design_raw.get("diversity_constraints", {}).get("max_variants_per_substitution", 3)
            ),
        ),
        redundancy_features=_normalize_string_list(
            panel_design_raw.get("redundancy_features", ["allele_name", "mutated_position", "mut_residue"]),
            "panel_design.redundancy_features",
        ),
    )
    interactive_app = InteractiveAppConfig(
        enabled=bool(interactive_app_raw.get("enabled", True)),
        framework=str(interactive_app_raw.get("framework") or "streamlit").strip().lower(),
        default_project=_resolve_optional_path(config_path.parent, interactive_app_raw.get("default_project")),
        enable_demo_mode=bool(interactive_app_raw.get("enable_demo_mode", True)),
        enable_scenario_saving=bool(interactive_app_raw.get("enable_scenario_saving", True)),
        max_rows_preview=int(interactive_app_raw.get("max_rows_preview", 200)),
    )
    scenario_analysis = ScenarioAnalysisConfig(
        enabled=bool(scenario_analysis_raw.get("enabled", True)),
        default_evidence_coverage_threshold=float(
            scenario_analysis_raw.get("default_evidence_coverage_threshold", 0.5)
        ),
        default_uncertainty_levels_allowed=_normalize_string_list(
            scenario_analysis_raw.get("default_uncertainty_levels_allowed", ["low", "moderate"]),
            "scenario_analysis.default_uncertainty_levels_allowed",
        ),
        allow_custom_filters=bool(scenario_analysis_raw.get("allow_custom_filters", True)),
        allow_side_by_side_comparison=bool(scenario_analysis_raw.get("allow_side_by_side_comparison", True)),
    )
    demo_mode = DemoModeConfig(
        enabled=bool(demo_mode_raw.get("enabled", True)),
        default_demo_project=(
            str(demo_mode_raw.get("default_demo_project")).strip()
            if demo_mode_raw.get("default_demo_project") not in {None, ""}
            else None
        ),
    )
    scenario_templates = ScenarioTemplatesConfig(
        enabled=bool(scenario_templates_raw.get("enabled", True)),
        template_file=_resolve_optional_path(config_path.parent, scenario_templates_raw.get("template_file")),
    )
    case_studies_enabled, case_studies = _build_case_studies(case_studies_value, reporting.include_case_studies)

    _validate_project_config(
        project_name,
        alleles,
        peptides,
        analysis,
        structure_analysis,
        clustering,
        cross_allele_analysis,
        pocket_signature,
        multi_allele,
        reporting,
        hypothesis_generation,
        pocket_regions,
        publication_bundle,
        prioritization,
        uncertainty,
        robustness,
        benchmarking,
        panel_design,
        interactive_app,
        scenario_analysis,
        demo_mode,
        scenario_templates,
        case_studies,
    )

    return ProjectConfig(
        project_name=project_name,
        output_dir=output_dir,
        alleles=alleles,
        peptides=peptides,
        prediction_inputs=prediction_inputs,
        parsing=parsing,
        analysis=analysis,
        structure_analysis=structure_analysis,
        clustering=clustering,
        cross_allele_analysis=cross_allele_analysis,
        pocket_signature=pocket_signature,
        multi_allele=multi_allele,
        reporting=reporting,
        hypothesis_generation=hypothesis_generation,
        pocket_regions=pocket_regions,
        publication_bundle=publication_bundle,
        prioritization=prioritization,
        uncertainty=uncertainty,
        robustness=robustness,
        benchmarking=benchmarking,
        panel_design=panel_design,
        interactive_app=interactive_app,
        scenario_analysis=scenario_analysis,
        demo_mode=demo_mode,
        scenario_templates=scenario_templates,
        case_studies_enabled=case_studies_enabled,
        case_studies=case_studies,
        source_config_path=config_path,
    )


def _build_allele_spec(base_dir: Path, entry: Any, index: int) -> AlleleSpec:
    if not isinstance(entry, dict):
        raise ValueError(f"alleles[{index}] must be an object.")
    return AlleleSpec(
        allele_name=str(entry["allele_name"]).strip(),
        class_type=str(entry.get("class_type") or "I").strip().upper(),
        heavy_chain_sequence=_normalize_optional_sequence(entry.get("heavy_chain_sequence")),
        beta2m_sequence=_normalize_optional_sequence(entry.get("beta2m_sequence")),
        reference_file=_resolve_optional_path(base_dir, entry.get("reference_file")),
        allow_metadata_only_fallback=bool(entry.get("allow_metadata_only_fallback", False)),
    )


def _build_peptide_panel(peptide_raw: dict[str, Any]) -> PeptidePanelConfig:
    mode = str(peptide_raw.get("mode") or "shared_panel").strip()
    allele_specific_sequences: dict[str, list[str]] = {}
    wildtype_sequences: list[str] = []
    if mode == "shared_panel":
        wildtype_sequences = _normalize_sequence_list(
            peptide_raw.get("wildtype_sequences", []),
            "peptides.wildtype_sequences",
        )
    elif mode == "allele_specific":
        allele_specific_raw = peptide_raw.get("allele_specific_sequences")
        if not isinstance(allele_specific_raw, dict) or not allele_specific_raw:
            raise ValueError("peptides.allele_specific_sequences must be a non-empty mapping in allele_specific mode.")
        for allele_name, sequences in allele_specific_raw.items():
            allele_specific_sequences[str(allele_name)] = _normalize_sequence_list(
                sequences,
                f"peptides.allele_specific_sequences['{allele_name}']",
            )
    else:
        raise ValueError("peptides.mode must be 'shared_panel' or 'allele_specific'.")

    return PeptidePanelConfig(
        mode=mode,
        wildtype_sequences=wildtype_sequences,
        mutation_positions=_normalize_positions(peptide_raw["mutation_positions"], "peptides.mutation_positions"),
        allowed_substitutions=_normalize_amino_acid_list(peptide_raw["allowed_substitutions"]),
        allele_specific_sequences=allele_specific_sequences,
    )


def get_peptides_for_allele(config: ProjectConfig, allele_name: str) -> list[str]:
    if config.peptides.mode == "shared_panel":
        return config.peptides.wildtype_sequences
    return config.peptides.allele_specific_sequences.get(allele_name, [])


def _build_case_studies(values: Any, default_enabled: bool) -> tuple[bool, list[CaseStudySpec]]:
    if isinstance(values, dict):
        enabled = bool(values.get("enabled", default_enabled))
        entries = values.get("definitions", [])
    else:
        enabled = default_enabled
        entries = values

    if entries is None or entries == "":
        return enabled, []
    if not isinstance(entries, list):
        raise ValueError("case_studies must be a list or an object with 'definitions'.")

    case_studies: list[CaseStudySpec] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"case_studies[{index}] must be an object.")
        case_studies.append(
            CaseStudySpec(
                case_id=str(entry.get("case_id") or "").strip(),
                description=str(entry.get("description") or "").strip(),
                alleles=_normalize_optional_string_list(entry.get("alleles"), f"case_studies[{index}].alleles"),
                peptides=_normalize_optional_string_list(entry.get("peptides"), f"case_studies[{index}].peptides"),
                mutation_positions=_normalize_optional_positions(
                    entry.get("mutation_positions", []),
                    f"case_studies[{index}].mutation_positions",
                ),
                substitutions=_normalize_optional_string_list(
                    entry.get("substitutions"),
                    f"case_studies[{index}].substitutions",
                    uppercase=True,
                ),
                variants=_normalize_optional_string_list(entry.get("variants"), f"case_studies[{index}].variants"),
            )
        )
    return enabled, case_studies


def _require_mapping(data: dict[str, Any], key: str, optional: bool = False) -> dict[str, Any] | None:
    value = data.get(key)
    if value is None and optional:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"Config field '{key}' must be an object.")
    return value


def _resolve_path(base_dir: Path, path_value: str | Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def _resolve_optional_path(base_dir: Path, path_value: str | Path | None) -> Path | None:
    if path_value in {None, ""}:
        return None
    return _resolve_path(base_dir, path_value)


def _normalize_optional_sequence(value: Any) -> str | None:
    if value in {None, ""}:
        return None
    sequence = str(value).strip().upper()
    _validate_sequence_characters(sequence, field_name="sequence")
    return sequence


def _normalize_sequence_list(values: Any, field_name: str) -> list[str]:
    if not isinstance(values, list) or not values:
        raise ValueError(f"{field_name} must be a non-empty list.")
    sequences = [str(value).strip().upper() for value in values]
    for sequence in sequences:
        _validate_sequence_characters(sequence, field_name=field_name)
    return sequences


def _normalize_positions(values: Any, field_name: str) -> list[int]:
    if not isinstance(values, list) or not values:
        raise ValueError(f"{field_name} must be a non-empty list of 1-based positions.")
    positions = [int(value) for value in values]
    if len(set(positions)) != len(positions):
        raise ValueError(f"{field_name} must be unique.")
    return positions


def _normalize_optional_positions(values: Any, field_name: str) -> list[int]:
    if values is None:
        return []
    if isinstance(values, list) and len(values) == 0:
        return []
    if not isinstance(values, list):
        raise ValueError(f"{field_name} must be a list of positions.")
    positions = [int(value) for value in values]
    if len(set(positions)) != len(positions):
        raise ValueError(f"{field_name} must be unique.")
    return positions


def _normalize_amino_acid_list(values: Any) -> list[str]:
    if not isinstance(values, list) or not values:
        raise ValueError("peptides.allowed_substitutions must be a non-empty list.")
    normalized = [str(value).strip().upper() for value in values]
    invalid = sorted(set(normalized) - AMINO_ACIDS)
    if invalid:
        raise ValueError(f"peptides.allowed_substitutions contains invalid amino acids: {invalid}")
    return normalized


def _normalize_string_list(values: Any, field_name: str) -> list[str]:
    if not isinstance(values, list) or not values:
        raise ValueError(f"{field_name} must be a non-empty list.")
    normalized = [str(value).strip() for value in values]
    if any(not item for item in normalized):
        raise ValueError(f"{field_name} must not contain empty values.")
    return normalized


def _normalize_optional_float_list(values: Any, field_name: str) -> list[float]:
    if not isinstance(values, list) or not values:
        raise ValueError(f"{field_name} must be a non-empty list.")
    normalized = [float(value) for value in values]
    if any(value <= 0 for value in normalized):
        raise ValueError(f"{field_name} must contain only positive values.")
    return normalized


def _normalize_positive_integer_list(values: Any, field_name: str) -> list[int]:
    if not isinstance(values, list) or not values:
        raise ValueError(f"{field_name} must be a non-empty list.")
    normalized = [int(value) for value in values]
    if any(value < 1 for value in normalized):
        raise ValueError(f"{field_name} must contain only positive integers.")
    return normalized


def _build_ranking_modes(values: Any) -> dict[str, RankingModeConfig]:
    defaults: dict[str, dict[str, Any]] = {
        "disruptive_mutations": {
            "enabled": True,
            "normalize_features": True,
            "require_structural_support": False,
            "features": [
                {"name": "delta_total_contacts_vs_wt", "weight": -1.0},
                {"name": "delta_mean_min_distance_vs_wt", "weight": 0.75},
                {"name": "delta_confidence_vs_wt", "weight": -0.5},
                {"name": "anchor_disruption_flag", "weight": 1.0},
            ],
        },
        "tolerated_mutations": {
            "enabled": True,
            "normalize_features": True,
            "require_structural_support": False,
            "features": [
                {"name": "delta_total_contacts_vs_wt", "weight": 1.0},
                {"name": "delta_mean_min_distance_vs_wt", "weight": -0.75},
                {"name": "delta_confidence_vs_wt", "weight": 0.5},
            ],
        },
        "allele_discriminating_mutations": {
            "enabled": True,
            "normalize_features": True,
            "require_structural_support": False,
            "features": [
                {"name": "cross_allele_contact_divergence", "weight": 1.0},
                {"name": "cross_allele_rank_divergence", "weight": 0.75},
            ],
        },
        "anchor_sensitive_mutations": {
            "enabled": True,
            "normalize_features": True,
            "require_structural_support": False,
            "features": [
                {"name": "anchor_disruption_flag", "weight": 1.0},
                {"name": "delta_contacts_at_anchor_positions_vs_wt", "weight": -1.0},
                {"name": "delta_total_contacts_vs_wt", "weight": -0.5},
            ],
        },
        "exploratory_followup_candidates": {
            "enabled": True,
            "normalize_features": True,
            "require_structural_support": False,
            "features": [
                {"name": "absolute_contact_change", "weight": 1.0},
                {"name": "cross_allele_contact_divergence", "weight": 0.75},
                {"name": "evidence_coverage_proxy", "weight": 0.5},
            ],
        },
    }
    raw_modes = values if isinstance(values, dict) else {}
    built: dict[str, RankingModeConfig] = {}
    for mode_name, default in defaults.items():
        mode_raw = raw_modes.get(mode_name, {})
        if mode_raw is None:
            mode_raw = {}
        if not isinstance(mode_raw, dict):
            raise ValueError(f"prioritization.ranking_modes.{mode_name} must be an object.")
        feature_values = mode_raw.get("features", default["features"])
        if not isinstance(feature_values, list) or not feature_values:
            raise ValueError(f"prioritization.ranking_modes.{mode_name}.features must be a non-empty list.")
        features = []
        for index, feature in enumerate(feature_values):
            if not isinstance(feature, dict):
                raise ValueError(
                    f"prioritization.ranking_modes.{mode_name}.features[{index}] must be an object."
                )
            features.append(
                RankingFeatureConfig(
                    name=str(feature.get("name") or "").strip(),
                    weight=float(feature.get("weight", 0.0)),
                )
            )
        if any(not feature.name for feature in features):
            raise ValueError(f"prioritization.ranking_modes.{mode_name}.features must include non-empty names.")
        built[mode_name] = RankingModeConfig(
            enabled=bool(mode_raw.get("enabled", default["enabled"])),
            normalize_features=bool(mode_raw.get("normalize_features", default["normalize_features"])),
            require_structural_support=bool(
                mode_raw.get("require_structural_support", default["require_structural_support"])
            ),
            features=features,
        )
    return built


def _normalize_optional_string_list(
    values: Any,
    field_name: str,
    uppercase: bool = False,
) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise ValueError(f"{field_name} must be a list.")
    normalized = [str(value).strip() for value in values]
    if uppercase:
        normalized = [value.upper() for value in normalized]
    if any(not item for item in normalized):
        raise ValueError(f"{field_name} must not contain empty values.")
    return normalized


def _validate_project_config(
    project_name: str,
    alleles: list[AlleleSpec],
    peptides: PeptidePanelConfig,
    analysis: AnalysisConfig,
    structure_analysis: StructureAnalysisConfig,
    clustering: ClusteringConfig,
    cross_allele_analysis: CrossAlleleAnalysisConfig,
    pocket_signature: PocketSignatureConfig,
    multi_allele: MultiAlleleConfig,
    reporting: ReportingConfig,
    hypothesis_generation: HypothesisGenerationConfig,
    pocket_regions: PocketRegionsConfig,
    publication_bundle: PublicationBundleConfig,
    prioritization: PrioritizationConfig,
    uncertainty: UncertaintyConfig,
    robustness: RobustnessConfig,
    benchmarking: BenchmarkingConfig,
    panel_design: PanelDesignConfig,
    interactive_app: InteractiveAppConfig,
    scenario_analysis: ScenarioAnalysisConfig,
    demo_mode: DemoModeConfig,
    scenario_templates: ScenarioTemplatesConfig,
    case_studies: list[CaseStudySpec],
) -> None:
    if not project_name:
        raise ValueError("project_name must not be empty.")
    allele_names = [allele.allele_name for allele in alleles]
    if any(not name for name in allele_names):
        raise ValueError("Every allele entry must include allele_name.")
    if len(set(allele_names)) != len(allele_names):
        raise ValueError("alleles must have unique allele_name values.")
    for allele in alleles:
        if allele.class_type != "I":
            raise ValueError("Phase 4 currently supports only class I alleles.")

    all_peptides: list[str] = list(peptides.wildtype_sequences)
    for sequences in peptides.allele_specific_sequences.values():
        all_peptides.extend(sequences)
    if not all_peptides:
        raise ValueError("At least one peptide wild-type sequence must be configured.")
    for peptide in all_peptides:
        peptide_length = len(peptide)
        for position in peptides.mutation_positions:
            if position < 1 or position > peptide_length:
                raise ValueError(
                    f"peptides.mutation_positions must be within peptide length ({peptide_length}) for all sequences."
                )
    if peptides.mode == "allele_specific":
        missing = set(allele_names) - set(peptides.allele_specific_sequences)
        if missing:
            raise ValueError(
                f"peptides.allele_specific_sequences is missing allele entries for: {sorted(missing)}"
            )
    if analysis.baseline_variant_id == "":
        raise ValueError("analysis.baseline_variant_id must not be empty.")
    if structure_analysis.contact_distance_angstrom <= 0:
        raise ValueError("structure_analysis.contact_distance_angstrom must be > 0.")
    if clustering.min_variants_required < 2:
        raise ValueError("clustering.min_variants_required must be >= 2.")
    if cross_allele_analysis.require_min_alleles < 2:
        raise ValueError("cross_allele_analysis.require_min_alleles must be >= 2.")
    if cross_allele_analysis.numeric_metric not in {"euclidean"}:
        raise ValueError("cross_allele_analysis.similarity_metrics.numeric must currently be 'euclidean'.")
    if cross_allele_analysis.set_based_metric not in {"jaccard"}:
        raise ValueError("cross_allele_analysis.similarity_metrics.set_based must currently be 'jaccard'.")
    if pocket_signature.min_contact_frequency < 1:
        raise ValueError("pocket_signature.min_contact_frequency must be >= 1.")
    if multi_allele.allele_specific_reference_peptides and peptides.mode != "allele_specific":
        raise ValueError("multi_allele.allele_specific_reference_peptides requires peptides.mode='allele_specific'.")
    if reporting.core_figure_limit < 1:
        raise ValueError("reporting.core_figure_limit must be >= 1.")
    if reporting.core_table_limit < 1:
        raise ValueError("reporting.core_table_limit must be >= 1.")
    if hypothesis_generation.min_supporting_variants < 1:
        raise ValueError("hypothesis_generation.min_supporting_variants must be >= 1.")
    if hypothesis_generation.min_supporting_alleles < 1:
        raise ValueError("hypothesis_generation.min_supporting_alleles must be >= 1.")
    if pocket_regions.require_region_mapping_for_comparison and not pocket_regions.mapping_file:
        raise ValueError("pocket_regions.mapping_file is required when require_region_mapping_for_comparison is true.")
    if prioritization.default_top_k < 1:
        raise ValueError("prioritization.default_top_k must be >= 1.")
    if robustness.weight_perturbation_fraction < 0:
        raise ValueError("robustness.weight_perturbation_fraction must be >= 0.")
    if panel_design.max_panel_size < 1:
        raise ValueError("panel_design.max_panel_size must be >= 1.")
    if not (0.0 <= panel_design.require_min_evidence_coverage <= 1.0):
        raise ValueError("panel_design.require_min_evidence_coverage must be between 0 and 1.")
    if panel_design.diversity_constraints.max_variants_per_position < 1:
        raise ValueError("panel_design.diversity_constraints.max_variants_per_position must be >= 1.")
    if panel_design.diversity_constraints.max_variants_per_allele < 1:
        raise ValueError("panel_design.diversity_constraints.max_variants_per_allele must be >= 1.")
    if panel_design.diversity_constraints.max_variants_per_substitution < 1:
        raise ValueError("panel_design.diversity_constraints.max_variants_per_substitution must be >= 1.")
    if interactive_app.framework not in {"streamlit"}:
        raise ValueError("interactive_app.framework must currently be 'streamlit'.")
    if interactive_app.max_rows_preview < 1:
        raise ValueError("interactive_app.max_rows_preview must be >= 1.")
    if not (0.0 <= scenario_analysis.default_evidence_coverage_threshold <= 1.0):
        raise ValueError("scenario_analysis.default_evidence_coverage_threshold must be between 0 and 1.")
    if not scenario_analysis.default_uncertainty_levels_allowed:
        raise ValueError("scenario_analysis.default_uncertainty_levels_allowed must not be empty.")
    for index, case_study in enumerate(case_studies):
        if not case_study.case_id:
            raise ValueError(f"case_studies[{index}].case_id must not be empty.")
        if any(position < 1 for position in case_study.mutation_positions):
            raise ValueError(f"case_studies[{index}].mutation_positions must contain only 1-based positions.")
        invalid_substitutions = sorted(set(case_study.substitutions) - AMINO_ACIDS)
        if invalid_substitutions:
            raise ValueError(
                f"case_studies[{index}].substitutions contains invalid amino acids: {invalid_substitutions}"
            )


def _validate_sequence_characters(sequence: str, field_name: str) -> None:
    invalid = sorted(set(sequence) - AMINO_ACIDS)
    if invalid:
        raise ValueError(f"{field_name} contains invalid amino acids: {invalid}")
