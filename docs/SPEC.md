# Project Specification

## Purpose

This repository provides a conservative, modular framework for peptide-MHC structural perturbation analysis centered on AlphaFold or ColabFold outputs.

The design goals are:

- local reproducibility
- modular extension points
- graceful handling of missing predictions
- transparent derived metrics
- report-ready outputs without overstating biological interpretation

## Scope

### In scope

- one or more class-I alleles in a single run
- one shared peptide panel or allele-specific peptide panels
- WT plus single-substitution mutant generation
- explicit or local-reference MHC sequence resolution
- multichain FASTA generation for heavy chain, beta-2 microglobulin, and peptide
- defensive parsing of common AlphaFold or ColabFold output artifacts
- simple peptide-heavy-chain contact extraction from structures
- WT-relative mutant comparison
- allele-level aggregation and cross-allele comparison
- reporting, publication bundle export, case studies, and exploratory hypotheses

### Out of scope

- direct AlphaFold or ColabFold execution
- experimental validation
- binding affinity prediction
- immunogenicity prediction
- definitive biochemical pocket annotation
- opaque machine-learned ranking models

## Input Specification

Primary entrypoint:

```bash
python -m src.main --config <path-to-yaml-or-json>
```

Accepted config styles:

- legacy phase-1 style
- phase-2 single-allele nested style
- phase-4 or phase-5 multi-allele style

The loader normalizes older schemas into the current internal shape.

## Config Sections

### `project_name`

Human-readable run name used in reports and output folder naming.

### `output_dir`

Base output directory. The pipeline creates subdirectories as needed.

### `alleles`

List of class-I allele definitions.

Each allele supports:

- `allele_name`
- `class_type`
- `heavy_chain_sequence`
- `beta2m_sequence`
- `reference_file`
- `allow_metadata_only_fallback`

Resolution priority:

1. explicit sequences in config
2. local reference mapping file
3. metadata-only fallback if allowed

### `peptides`

Defines the peptide panel.

Supported modes:

- `shared_panel`
- `allele_specific`

Shared-panel fields:

- `wildtype_sequences`
- `mutation_positions`
- `allowed_substitutions`

Allele-specific mode uses `allele_specific_sequences`.

### `prediction_inputs`

Controls whether the pipeline writes:

- multimer FASTA files
- chain manifest
- ColabFold variants CSV

### `parsing`

Important field:

- `prediction_root`

If omitted, the default predictions directory under the output root is scanned.

### `analysis`

Important field:

- `baseline_variant_id`

Used for WT-relative comparison inside each allele and peptide group.

### `structure_analysis`

Controls contact extraction and WT-relative structural deltas.

Important fields:

- `enabled`
- `contact_distance_angstrom`
- `use_all_atom_contacts`
- `fallback_to_ca_distance`
- `compute_wt_deltas`
- `compute_optional_geometry_metrics`
- `anchor_positions`
- `require_confident_chain_mapping`

### `clustering`

Controls variant-level fingerprint clustering when enough data exists.

### `cross_allele_analysis`

Controls allele-level similarity and overlap outputs.

### `pocket_signature`

Controls residue-level pocket-signature aggregation from heavy-chain contacts.

### `pocket_regions`

Optional user-defined region aggregation layer.

Fields:

- `enabled`
- `mapping_file`
- `require_region_mapping_for_comparison`

### `reporting`

Controls markdown report and manifest generation.

### `publication_bundle`

Controls whether selected figures and tables are copied into a notebook or paper-friendly bundle.

### `hypothesis_generation`

Controls exploratory hypothesis extraction from existing outputs.

### `case_studies`

Optional named filtered views over existing outputs.

Each case study can filter by:

- allele
- peptide
- mutation position
- substitution
- variant id

## Internal Pipeline Specification

### 1. Config loading

Implemented in [src/config.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/config.py).

Responsibilities:

- load YAML or JSON
- normalize legacy schemas
- validate fields
- resolve relative paths

### 2. Sequence resolution

Implemented in [src/sequence_resolver.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/sequence_resolver.py).

Responsibilities:

- prefer explicit heavy-chain and beta-2 microglobulin sequences
- support local reference files
- preserve metadata-only fallback behavior when configured

### 3. Mutant generation

Implemented in [src/mutation_generator.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/mutation_generator.py).

Responsibilities:

- preserve WT row
- generate single substitutions at requested positions
- assign deterministic `variant_id`, `local_variant_id`, and `peptide_id`

### 4. Prediction input generation

Implemented in [src/input_builder.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/input_builder.py).

Responsibilities:

- assign chain roles
- write multimer FASTA text
- build chain manifest rows
- build ColabFold-style query strings from real sequences

### 5. Prediction parsing

Implemented in [src/parse_predictions.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/parse_predictions.py).

Supported artifacts:

- `ranking_debug.json`
- `result_*.pkl`
- `result_*.pkl.gz`
- `*.npz`
- `ranked_*.pdb`
- `*.pdb`
- `*.cif`
- `*.mmcif`

Parser behavior is permissive. Missing files do not fail the pipeline.

### 6. Structure parsing and chain mapping

Implemented in [src/structure_utils.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/structure_utils.py).

Responsibilities:

- load PDB or mmCIF structures
- list chains and residues
- map chain ids to semantic roles
- provide distance and geometry helpers

Chain mapping order:

1. generated input context when available
2. approximate sequence length or sequence matching
3. explicit ambiguity handling

If mapping is ambiguous and confidence is required, structural metrics are skipped.

### 7. Contact analysis

Implemented in [src/contact_analysis.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/contact_analysis.py).

Current contact definition:

- peptide residue and heavy-chain residue are considered in contact if any atom pair is within `contact_distance_angstrom`
- if atom completeness is insufficient, C-alpha fallback can be used when enabled

Current outputs:

- per-variant structural summary
- per-peptide-position contact rows
- per-heavy-chain-contact residue rows
- WT-relative structural delta rows

### 8. Fingerprints and cross-allele comparison

Implemented in:

- [src/fingerprint.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/fingerprint.py)
- [src/allele_fingerprint.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/allele_fingerprint.py)
- [src/pocket_signature.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/pocket_signature.py)
- [src/cross_allele_analysis.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/cross_allele_analysis.py)

Responsibilities:

- variant-level tolerance fingerprints
- allele-level aggregate fingerprints
- residue-level pocket signatures
- cross-allele similarity matrices
- residue overlap tables

## Phase-5 Reporting Specification

### Reporting outputs

Generated by [src/reporting.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/reporting.py).

Required outputs:

- `report.md`
- `report_summary.json`
- `figures_manifest.csv`
- `tables_manifest.csv`
- `analysis_snapshot.json`

The report must:

- stay grounded in computed outputs
- state when data are missing
- keep prose concise and factual
- include caveats explicitly

### Publication bundle

Generated by [src/publication_bundle.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/publication_bundle.py).

Required structure:

```text
publication_bundle/
  report.md
  report_summary.json
  figures/
  tables/
  manifests/
  notebook_exports/
```

### Case studies

Generated by [src/case_study.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/case_study.py).

Case studies are filtered output subsets, not separate analyses.

### Pocket regions

Generated by [src/pocket_region_analysis.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/pocket_region_analysis.py).

This layer depends on user-defined residue-to-region mapping.

### Hypotheses

Generated by [src/hypothesis_generation.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/hypothesis_generation.py).

Hypothesis rows must:

- cite supporting metrics
- cite supporting tables or figures
- include caveats
- use descriptive or exploratory confidence labels

### Provenance

Generated by [src/provenance.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/provenance.py).

Fields currently include:

- pipeline version
- UTC timestamp
- config digest
- requirements digest
- git commit hash if available

## Output Contract

### Core manifests

- `manifests/manifest.csv`
- `colabfold_inputs/variants.csv`
- `colabfold_inputs/chain_manifest.csv`

### Core analysis tables

- `analysis/summary.csv`
- `analysis/position_summary.csv`
- `analysis/structural_contacts.csv`
- `analysis/peptide_position_contacts.csv`
- `analysis/heavy_chain_contact_residues.csv`
- `analysis/structural_deltas.csv`

### Fingerprints and comparisons

- `analysis/tolerance_fingerprint.csv`
- `analysis/allele_tolerance_fingerprint.csv`
- `analysis/pocket_signature_residues.csv`
- `analysis/cross_allele_summary.csv`
- `analysis/allele_similarity_matrix.csv`

### Phase-5 outputs

- `analysis/report.md`
- `analysis/hypotheses.csv`
- `analysis/analysis_snapshot.json`
- `publication_bundle/*`
- `case_studies/*`

## Testing Contract

Tests cover:

- config compatibility
- sequence resolution
- input generation
- parser behavior
- structure parsing and contact extraction
- fingerprint aggregation
- reporting and hypothesis generation
- provenance and pocket-region aggregation

Run:

```bash
python -m pytest -q
```

## Scientific Constraints

- predicted structure quality varies
- contact counts are heuristic summaries
- raw residue overlap is not equivalent to functional equivalence
- user-defined pocket regions are only as reliable as the supplied mapping
- exploratory hypotheses are not conclusions

That conservatism is part of the intended behavior, not a missing feature.
