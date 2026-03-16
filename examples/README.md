# Example Configs

This folder now contains two kinds of examples:

- `sample_input.yaml`: the full feature-rich reference config used across the repo
- public-data-oriented workflow templates: narrower examples organized by use case

## Important note

The public-data examples are intentionally conservative:

- they use real allele names and public-facing peptide examples
- they point to the local reference file for allele sequences
- they do not ship fabricated biological sequences

To generate true multichain FASTA inputs from the public-data templates, populate:

- [../data/allele_reference.yaml](../data/allele_reference.yaml)

using trusted public sequences, preferably from IPD-IMGT/HLA.

## Included examples

- `sample_input.yaml`
- `researcher_project_template.yaml`
- `researcher_conservative_weights.yaml`
- `researcher_cross_allele_weights.yaml`
- `minimal_single_allele_template.yaml`
- `public_a0101_mage_panel.yaml`
- `public_a0201_cmv_panel.yaml`
- `public_a0301_multipeptide_review.yaml`
- `public_a1101_epstein_barr_panel.yaml`
- `public_a2402_hiv_panel.yaml`
- `public_b0801_hiv_panel.yaml`
- `public_cross_allele_influenza_panel.yaml`
- `public_cross_allele_cmv_panel.yaml`
- `public_b0702_anchor_review.yaml`
- `public_anchor_scan_template.yaml`
- `public_conservative_review_template.yaml`
- `public_decision_meeting_template.yaml`
- `iedb_large_binding_panel.yaml`
- `viral_escape_sars_cov2.yaml`
- `cancer_neoantigen_screen.yaml`

## Recommended starting points

- first-time evaluator: `sample_input.yaml`
- first real researcher project: `researcher_project_template.yaml`
- conservative weighting variant: `researcher_conservative_weights.yaml`
- cross-allele weighting variant: `researcher_cross_allele_weights.yaml`
- simpler single-allele template: `minimal_single_allele_template.yaml`
- public-data-style multi-allele setup: `public_cross_allele_influenza_panel.yaml`
- reviewer-friendly narrow meeting template: `public_decision_meeting_template.yaml`
- conservative shortlist workflow: `public_conservative_review_template.yaml`
