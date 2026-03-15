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
- `minimal_single_allele_template.yaml`
- `public_a0201_cmv_panel.yaml`
- `public_cross_allele_influenza_panel.yaml`
- `public_b0702_anchor_review.yaml`
- `public_a1101_epstein_barr_panel.yaml`

## Recommended starting points

- first-time evaluator: `sample_input.yaml`
- simpler single-allele template: `minimal_single_allele_template.yaml`
- public-data-style multi-allele setup: `public_cross_allele_influenza_panel.yaml`
