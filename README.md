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

The project is intentionally conservative. It does not claim binding affinity prediction, immunogenicity prediction, or experimental validation. Structural summaries are presented as transparent derived features from predicted models.

## Elevator Pitch

This is a reproducible peptide-MHC comparative structural analysis framework that turns mutation panels and AlphaFold or ColabFold outputs into interpretable WT-relative, cross-allele, and publication-oriented structural summaries.

## Documentation Map

- Overview and quick start: [README.md](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/README.md)
- Detailed project specification: [docs/SPEC.md](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/docs/SPEC.md)
- Current feature inventory: [docs/FEATURES.md](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/docs/FEATURES.md)
- Module and pipeline architecture: [docs/ARCHITECTURE.md](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/docs/ARCHITECTURE.md)
- What makes this repo distinct: [docs/UNIQUENESS.md](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/docs/UNIQUENESS.md)
- HTML dashboard guide: [docs/UI.md](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/docs/UI.md)
- Research-facing pitch language: [docs/PITCH.md](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/docs/PITCH.md)
- Abstract text: [docs/ABSTRACT.md](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/docs/ABSTRACT.md)
- Slide outline: [docs/SLIDES.md](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/docs/SLIDES.md)
- HTML pitch and vision page: [docs/project_story.html](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/docs/project_story.html)

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
9. export reports, publication tables, figures, notebook-ready files, and case-study subsets

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

## Minimal Example Config

```yaml
project_name: "mhc_phase5_demo"
output_dir: "../outputs/mhc_phase5_demo"

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
  prediction_root: "../outputs/mhc_phase5_demo/predictions"

structure_analysis:
  enabled: true
  contact_distance_angstrom: 4.5
  anchor_positions: [2, 9]

reporting:
  enabled: true
```

For a full example including cross-allele reporting, case studies, and pocket-region hooks, see [examples/sample_input.yaml](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/examples/sample_input.yaml).

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

Phase-5 reporting outputs:

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

If you need implementation detail, start with [docs/SPEC.md](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/docs/SPEC.md).
If you need a concise inventory of current capabilities and boundaries, use [docs/FEATURES.md](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/docs/FEATURES.md).
