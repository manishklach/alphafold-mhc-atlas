# AlphaFold Peptide-MHC Comparative Analysis Framework

This repository is a local-workspace-friendly Python framework for peptide-MHC perturbation studies built around AlphaFold or ColabFold outputs.

It is designed for researchers who want more than raw structure predictions: a reproducible way to generate peptide-MHC mutation panels, compare mutants to WT, aggregate effects across alleles, and produce report-ready structural summaries without collapsing everything into an opaque score.

## Why This Repo Exists

There is a recurring gap in peptide-MHC projects:

- one tool prepares FASTA files
- another tool runs AlphaFold or ColabFold
- a notebook parses a few structures
- a separate slide deck or figure folder captures the conclusions

This repository is meant to close that gap with one coherent workflow.

Its core idea is simple:

- treat peptide-MHC perturbation studies as a comparative analysis problem
- keep the outputs interpretable
- stay explicit about missing data and scientific limits
- make the results reusable in papers, talks, notebooks, and collaborator handoffs

It started as an input-preparation scaffold and now supports:

- allele-aware mutant panel generation
- class-I multichain input construction
- defensive AlphaFold or ColabFold output parsing
- within-allele structural contact analysis
- cross-allele tolerance and pocket-signature comparison
- reporting, publication-bundle export, case studies, and exploratory hypothesis generation
- transparent variant prioritization, robustness checks, benchmarking hooks, and compact mutation-panel design
- a local interactive analyst app with scenario analysis, evidence drilldown, demo projects, and scenario exports

The project is intentionally conservative. It does not claim binding affinity prediction, immunogenicity prediction, or experimental validation. Structural summaries are presented as transparent derived features from predicted models.

## Elevator Pitch

This is a reproducible peptide-MHC comparative structural analysis framework that turns mutation panels and AlphaFold or ColabFold outputs into interpretable WT-relative, cross-allele, and publication-oriented structural summaries.

## Documentation Map

- Overview and quick start: [README.md](README.md)
- Detailed project specification: [docs/SPEC.md](docs/SPEC.md)
- Current feature inventory: [docs/FEATURES.md](docs/FEATURES.md)
- Module and pipeline architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- What makes this repo distinct: [docs/UNIQUENESS.md](docs/UNIQUENESS.md)
- HTML dashboard guide: [docs/UI.md](docs/UI.md)
- Research-facing pitch language: [docs/PITCH.md](docs/PITCH.md)
- Abstract text: [docs/ABSTRACT.md](docs/ABSTRACT.md)
- Slide outline: [docs/SLIDES.md](docs/SLIDES.md)
- HTML pitch and vision page: [docs/project_story.html](docs/project_story.html)

## What This Repo Does

Given one or more class-I HLA alleles and one or more reference peptides, the pipeline can:

1. resolve heavy-chain and beta-2 microglobulin sequences from explicit config or local references
2. generate wild-type plus single-substitution peptide panels
3. write multimer FASTA inputs for external AlphaFold or ColabFold execution
4. parse available prediction folders without assuming one exact output version
5. extract simple peptide-heavy-chain structural contact features from PDB or mmCIF outputs
6. compare mutants to WT within each allele and peptide panel
7. aggregate variant-level effects into allele-level tolerance fingerprints
8. compare alleles by contact-derived pocket signatures and tolerance behavior
9. rank variants for disruptive, tolerated, discriminating, anchor-sensitive, or exploratory follow-up modes
10. quantify evidence coverage and uncertainty for each ranked result
11. test ranking robustness across alternative weighting and missing-feature settings
12. export compact mutation panels for different downstream goals
13. launch a local analyst app for browsing projects, rankings, panels, hypotheses, and cross-allele outputs
14. create and compare deterministic scenarios from existing artifacts without rerunning inference
15. export scenario-specific tables, markdown summaries, and evidence bundles
16. export reports, publication tables, figures, notebook-ready files, and case-study subsets

## What This Repo Does Not Do

- it does not run AlphaFold or ColabFold inference itself
- it does not claim binding affinity or immunogenicity prediction
- it does not treat AlphaFold confidence as biological ground truth
- it does not assume canonical residue comparability across alleles unless the user supplies a mapping layer
- it does not generate black-box overall scores and present them as truth

## Repository Structure

```text
alphafold_mhc_atlas/
  data/
    allele_reference.yaml
    pocket_regions.yaml
  examples/
    sample_input.yaml
  src/
    config.py
    mutation_generator.py
    sequence_resolver.py
    input_builder.py
    parse_predictions.py
    structure_utils.py
    contact_analysis.py
    fingerprint.py
    allele_fingerprint.py
    pocket_signature.py
    pocket_region_analysis.py
    cross_allele_analysis.py
    hypothesis_generation.py
    reporting.py
    publication_bundle.py
    provenance.py
    case_study.py
    main.py
  tests/
  outputs/
```

## Quick Start

```bash
cd C:\Users\ManishKL\Documents\Playground\alphafold_mhc_atlas
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m src.main --config examples/sample_input.yaml
.\.venv\Scripts\python -m pytest -q
```

Primary CLI:

```bash
python -m src.main --config examples/sample_input.yaml
```

Local HTML UI:

```bash
python -m src.webapp
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000).

Interactive analyst app:

```bash
python -m src.app --project outputs/mhc_phase6_demo
```

Canonical Streamlit launch:

```bash
python -m streamlit run src/app.py -- --project outputs/mhc_phase6_demo
```

Demo mode:

```bash
python -m src.app --demo cross_allele_demo
python -m src.app --list-demos
python -m src.app --list-project-artifacts outputs/mhc_phase6_demo
```

## Minimal Example Config

```yaml
project_name: "mhc_phase6_demo"
output_dir: "../outputs/mhc_phase6_demo"

alleles:
  - allele_name: "HLA-A*02:01"
    class_type: "I"
    heavy_chain_sequence: "ACDEFGHIKLMNPQRSTVWYACDEFGHIKLMNPQRSTVWY"
    beta2m_sequence: "MNPQRSTVWYACDEFGHIKL"
    allow_metadata_only_fallback: false

peptides:
  mode: "shared_panel"
  wildtype_sequences: ["GILGFVFTL"]
  mutation_positions: [2, 9]
  allowed_substitutions: ["A", "V", "L", "I", "F", "Y"]

parsing:
  prediction_root: "../outputs/mhc_phase6_demo/predictions"

structure_analysis:
  enabled: true
  contact_distance_angstrom: 4.5
  anchor_positions: [2, 9]

prioritization:
  enabled: true

panel_design:
  enabled: true
  max_panel_size: 12
  ranking_goal: "balanced_exploration_panel"

interactive_app:
  enabled: true
  framework: "streamlit"

scenario_analysis:
  enabled: true
  default_evidence_coverage_threshold: 0.5

reporting:
  enabled: true
```

For a full example including cross-allele reporting, case studies, and pocket-region hooks, see [examples/sample_input.yaml](examples/sample_input.yaml).

## Key Outputs

Core analysis outputs:

- `manifests/manifest.csv`
- `colabfold_inputs/variants.csv`
- `colabfold_inputs/chain_manifest.csv`
- `analysis/summary.csv`
- `analysis/structural_contacts.csv`
- `analysis/tolerance_fingerprint.csv`
- `analysis/allele_tolerance_fingerprint.csv`
- `analysis/pocket_signature_residues.csv`
- `analysis/cross_allele_summary.csv`

Phase-6 decision-support outputs:

- `analysis/variant_priority_table.csv`
- `analysis/priority_evidence_table.csv`
- `analysis/priority_uncertainty_table.csv`
- `analysis/robustness_summary.csv`
- `analysis/ranking_stability.csv`
- `analysis/benchmark_summary.csv`
- `analysis/optimized_mutation_panel.csv`
- `analysis/panel_coverage_summary.csv`
- `analysis/prioritization/`
- `analysis/robustness/`
- `analysis/benchmarking/`
- `analysis/panel_design/`

Phase-7 interactive assets and exports:

- `data/scenario_templates.yaml`
- `demo/`
- `scenario_exports/<scenario_id>/`
- `saved_scenarios/<scenario_id>.json`
- `analysis/project_inventory.json` when written from the app or CLI

Phase-5 reporting outputs still remain:

- `analysis/report.md`
- `analysis/report_summary.json`
- `analysis/analysis_snapshot.json`
- `analysis/hypotheses.csv`
- `analysis/hypotheses.md`
- `publication_bundle/`
- `case_studies/<case_id>/`

## Scientific Positioning

This repo is best used as a comparative structural-analysis scaffold for:

- peptide substitution panels within one allele
- cross-allele comparison of contact-derived tolerance patterns
- report generation for exploratory structural case studies
- reproducible export bundles for notebooks, posters, or slides

It should not be used to make strong biological claims without additional validation.

## Phase 6: Prioritization And Panel Design

Phase 6 turns the repository into a transparent decision-support layer.

What prioritization means here:

- it is a rule-based ranking built from visible structural and confidence-derived features
- every ranking row includes a decomposable evidence trail
- missing features lower support quality rather than being hidden
- uncertainty reflects evidence completeness, not statistical confidence

Supported ranking modes:

- `disruptive_mutations`
- `tolerated_mutations`
- `allele_discriminating_mutations`
- `anchor_sensitive_mutations`
- `exploratory_followup_candidates`

Robustness and benchmarking:

- robustness reruns the ranking under alternate weighting and feature-drop settings
- benchmarking performs internal sanity checks and optional reference hooks when the user supplies them
- neither mode should be interpreted as experimental validation

Panel design:

- uses greedy score-plus-diversity heuristics
- enforces explicit quotas across alleles, positions, and substitutions
- favors compact, evidence-backed follow-up sets without claiming biological optimality

Example interpretation:

`A02_pep1_pos2_ItoF` can rank highly in `disruptive_mutations` because it loses peptide-heavy-chain contacts, increases mean minimum distance to the heavy chain, and triggers an anchor-disruption flag. If its evidence coverage is partial and WT-relative metrics are missing for some features, the row remains visible but should be interpreted as exploratory rather than definitive.

Example output tree:

```text
outputs/mhc_phase6_demo/
  manifests/
  colabfold_inputs/
  predictions/
  analysis/
    summary.csv
    variant_priority_table.csv
    priority_evidence_table.csv
    priority_uncertainty_table.csv
    robustness_summary.csv
    benchmark_summary.csv
    optimized_mutation_panel.csv
    prioritization/
    robustness/
    benchmarking/
    panel_design/
    report.md
    analysis_snapshot.json
  plots/
    top_disruptive_variants.png
    priority_score_vs_coverage.png
    ranking_stability.png
    panel_composition.png
  case_studies/
  publication_bundle/
```

## Phase 7: Interactive App And Scenarios

Phase 7 adds a local-first analyst interface on top of the existing file-backed outputs.

What the app does:

- load a local project output directory or a curated demo project
- browse variant summaries, rankings, panels, cross-allele outputs, hypotheses, and reports
- inspect evidence for any ranked or selected variant
- configure two scenarios side by side from templates or custom filters
- compare changed ranks and changed panel membership
- export scenario summaries, filtered tables, and evidence bundles

What scenario analysis means here:

- it filters and recombines existing analysis artifacts
- it does not rerun AlphaFold or ColabFold
- it remains deterministic because the exact scenario state is serialized
- it is only as informative as the underlying outputs available in the loaded project

Evidence drilldown:

- every ranked variant remains linked to priority evidence rows, uncertainty rows, summary rows, and panel rows
- if supporting fields are missing, the app shows that explicitly instead of inventing summaries

Built-in scenario templates:

- Most disruptive mutants
- Most tolerated mutants
- Anchor-focused disruptive panel
- Low-uncertainty high-support shortlist
- Best allele-discriminating panel
- Aromatic substitution exploration

Scenario template structure:

```yaml
templates:
  - scenario_id: disruptive_shortlist
    label: Most disruptive mutants
    ranking_mode: disruptive_mutations
    evidence_coverage_threshold: 0.5
    allowed_uncertainty: [low, moderate]
    require_structural_support: false
    anchor_only: false
    panel_size: 10
```

Saved scenario example:

```json
{
  "scenario_id": "a_disruptive_shortlist",
  "label": "Most disruptive mutants",
  "ranking_mode": "disruptive_mutations",
  "alleles": ["HLA-A*02:01"],
  "mutation_positions": [2, 9],
  "substitutions": ["A", "F"],
  "evidence_coverage_threshold": 0.6,
  "allowed_uncertainty": ["low", "moderate"],
  "require_structural_support": true,
  "anchor_only": false,
  "panel_size": 8
}
```

Scenario export tree:

```text
outputs/mhc_phase6_demo/
  scenario_exports/
    a_disruptive_shortlist/
      scenario_summary.csv
      scenario_summary.json
      scenario_ranked_variants.csv
      scenario_panel.csv
      scenario_evidence.csv
      scenario_notes.md
      evidence_manifest.csv
      evidence_bundle_<variant_id>.json
    a_disruptive_shortlist_vs_b_anchor_focus/
      scenario_comparison.csv
      scenario_rank_diff.csv
      scenario_panel_diff.csv
      scenario_comparison_summary.md
      comparison_summary.json
```

Demo project structure:

```text
demo/
  small_project/
    README.md
    project/
      analysis/
  cross_allele_demo/
    README.md
    project/
      analysis/
```

Example workflow:

1. Run `python -m src.app --project outputs/mhc_phase6_demo`.
2. Open the `Scenario Analysis` page.
3. Choose `Most disruptive mutants`.
4. Set evidence coverage to `0.6` and optionally restrict alleles or positions.
5. Inspect the top ranked rows and open evidence drilldown in `Variant Explorer` or `Ranking Explorer`.
6. Export the scenario bundle and hand off the markdown/CSV/JSON outputs to collaborators.

App limitations:

- the app only visualizes what already exists on disk
- missing tables or plots are shown as unavailable rather than inferred
- scenario outputs are analyst filters, not new structural computations
- selected variants and panels are still exploratory and evidence-linked, not validated biological truths

## Testing

The repository includes lightweight tests for:

- config normalization and sequence resolution
- mutant generation and input writing
- AlphaFold output parsing
- structure parsing and contact extraction
- tolerance fingerprinting and cross-allele comparison
- reporting, pocket-region aggregation, provenance, and case-study filtering

Run:

```bash
.\.venv\Scripts\python -m pytest -q
```

## Next Reading

If you need implementation detail, start with [docs/SPEC.md](docs/SPEC.md).
If you need a concise inventory of current capabilities and boundaries, use [docs/FEATURES.md](docs/FEATURES.md).
