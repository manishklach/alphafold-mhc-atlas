from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
class PilotWorkflowConfig:
    enabled: bool
    save_sessions: bool
    enable_review_queue: bool
    enable_annotations: bool
    enable_feedback: bool
    enable_handoff_bundles: bool


@dataclass(frozen=True)
class FeedbackConfig:
    enabled: bool
    require_reviewer_name: bool
    allowed_concern_types: list[str]


@dataclass(frozen=True)
class ChecklistsConfig:
    enabled: bool
    template_file: Path | None


@dataclass(frozen=True)
class HandoffConfig:
    enabled: bool
    include_annotations: bool
    include_feedback_snapshot: bool
    include_scope_statement: bool


@dataclass(frozen=True)
class SessionLoggingConfig:
    enabled: bool
    redact_paths: bool


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
    pilot_workflow: PilotWorkflowConfig
    feedback: FeedbackConfig
    checklists: ChecklistsConfig
    handoff: HandoffConfig
    session_logging: SessionLoggingConfig
    case_studies_enabled: bool
    case_studies: list[CaseStudySpec]
    source_config_path: Path
