# MHC Atlas OS Architecture

Peptide-MHC Decision Platform for Structure-Guided Experimental Prioritization

## High-Level Flow

```text
config
  -> sequence resolution
  -> peptide mutant generation
  -> multichain input writing
  -> prediction parsing
  -> structure parsing and chain mapping
  -> contact extraction and WT-relative deltas
  -> variant fingerprints
  -> allele fingerprints and pocket signatures
  -> cross-allele comparison
  -> reporting, publication bundle, case studies, hypotheses
```

## Module Map

### Configuration and orchestration

- [src/config.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/config.py)
- [src/main.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/main.py)

### Input construction

- [src/mutation_generator.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/mutation_generator.py)
- [src/sequence_resolver.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/sequence_resolver.py)
- [src/input_builder.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/input_builder.py)
- [src/io_utils.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/io_utils.py)

### Prediction parsing

- [src/parse_predictions.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/parse_predictions.py)

### Structure and contact analysis

- [src/structure_utils.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/structure_utils.py)
- [src/contact_analysis.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/contact_analysis.py)
- [src/metrics.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/metrics.py)
- [src/visualize.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/visualize.py)

### Fingerprints and comparison

- [src/fingerprint.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/fingerprint.py)
- [src/allele_fingerprint.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/allele_fingerprint.py)
- [src/pocket_signature.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/pocket_signature.py)
- [src/pocket_region_analysis.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/pocket_region_analysis.py)
- [src/cross_allele_analysis.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/cross_allele_analysis.py)
- [src/cluster_analysis.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/cluster_analysis.py)

### Reporting and downstream outputs

- [src/reporting.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/reporting.py)
- [src/publication_bundle.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/publication_bundle.py)
- [src/hypothesis_generation.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/hypothesis_generation.py)
- [src/case_study.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/case_study.py)
- [src/provenance.py](/C:/Users/ManishKL/Documents/Playground/alphafold_mhc_atlas/src/provenance.py)

## Data Products

### Inputs

- config YAML or JSON
- optional allele reference file
- optional pocket-region mapping file
- optional prediction folders produced elsewhere

### Intermediate products

- mutant manifest
- ColabFold variant table
- chain manifest
- parsed prediction records
- structural contact rows

### Final products

- summary tables
- fingerprint tables
- cross-allele comparison tables
- plots
- reports
- publication bundle
- case-study subsets
- hypothesis outputs

## Design Principles

### 1. Missing data should not crash the pipeline

If predictions or structures are missing, the pipeline should still emit manifests, summaries, and explicit coverage signals.

### 2. Biological claims stay conservative

The framework computes descriptive structural features. It does not convert them into unjustified claims.

### 3. Extension points should stay visible

Pocket regions, case studies, reporting, and hypotheses are separate modules so future work can deepen them without rewriting the core pipeline.

### 4. Output paths should remain stable

The project uses stable filenames and directories so notebooks, slides, or future report tools can consume outputs consistently.

## Current Extension Hooks

Good places for future work:

- `structure_utils.py` for stronger residue mapping and alignment-aware parsing
- `contact_analysis.py` for richer contact definitions
- `pocket_region_analysis.py` for better region libraries
- `cross_allele_analysis.py` for stronger comparative representations
- `reporting.py` for richer figure and table selection
- `publication_bundle.py` for downstream notebook or slide integrations
