# v0.7.0 - Interactive Decision Support

This release moves the repository from a file-oriented phase-6 analysis framework into a phase-7 local decision-support application.

## Highlights

- Added a local Streamlit analyst app for browsing projects, rankings, panels, hypotheses, and cross-allele outputs.
- Added deterministic scenario analysis on top of existing outputs, including side-by-side scenario comparison.
- Added evidence drilldown so ranked variants remain linked to visible supporting rows.
- Added curated demo projects for collaborator-facing walkthroughs and app demos.
- Added project inventory and artifact indexing for partial-output projects.
- Preserved the existing pipeline and reporting workflow while layering the app on top.

## New capabilities

### Interactive app

- Launch with `python -m src.app --project outputs/mhc_phase6_demo`
- Or `python -m streamlit run src/app.py -- --project outputs/mhc_phase6_demo`
- Supports project overview, variant explorer, ranking explorer, panel designer, cross-allele comparison, scenarios, case studies, hypotheses, and reports.

### Scenario analysis

- Built-in scenario templates in `data/scenario_templates.yaml`
- Deterministic scenario filtering over existing prioritization and panel outputs
- Scenario export bundles with:
  - `scenario_summary.csv`
  - `scenario_ranked_variants.csv`
  - `scenario_panel.csv`
  - `scenario_evidence.csv`
  - `scenario_notes.md`
  - `evidence_bundle_<variant_id>.json`

### Scenario comparison

- Rank-diff and panel-diff outputs across two saved or in-memory scenarios
- Exported comparison markdown and CSV summaries

### Demo workflows

- `demo/small_project`
- `demo/cross_allele_demo`

These are lightweight, local, committed demo output trees intended for product demos and collaborator walkthroughs.

## Also included

### Phase 6 decision-support layer

- Transparent prioritization engine
- Evidence and uncertainty summaries
- Robustness / sensitivity summaries
- Conservative benchmarking hooks
- Compact panel-design outputs

## Scientific positioning

This release is still:

- not a binding-affinity predictor
- not an immunogenicity predictor
- not an AlphaFold inference engine
- not a black-box recommender

It remains a transparent, evidence-linked analysis and decision-support framework over predicted peptide-MHC structures and derived tables.

## Notes

- The interactive app is local-first and file-backed.
- Scenario outputs are filtered summaries from existing artifacts; they do not rerun structural modeling.
- The repository currently targets AlphaFold/ColabFold-style output ingestion in a version-tolerant way, not AlphaFold 3 specifically.
