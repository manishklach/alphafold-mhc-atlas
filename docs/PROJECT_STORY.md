# MHC Atlas OS: Project Story

## Research Pitch

# Peptide-MHC comparative structural analysis without the usual notebook sprawl

MHC Atlas OS is a reproducible peptide-MHC decision platform for turning mutation panels and AlphaFold or ColabFold outputs into interpretable WT-relative, cross-allele, and publication-oriented structural summaries.

## Core Pitch

> This framework takes one or more class-I alleles and peptide mutation panels, prepares allele-aware multichain modeling inputs, parses predicted peptide-MHC complexes, extracts transparent peptide-pocket contact features, compares mutants to WT, aggregates effects across alleles, and exports reports, figures, case studies, and exploratory hypotheses.

Key themes:

- WT-relative analysis
- Cross-allele comparison
- Pocket signatures
- Publication bundle

## What It Is Not

- Not a binding affinity predictor.
- Not an immunogenicity predictor.
- Not proof of biological mechanism.
- Not a black-box ranking model.

### Positioning

It is a comparative structural analysis framework for hypothesis generation and reproducible reporting.

## Vision

Build a rigorous peptide-MHC comparative analysis foundation that can grow into multi-allele structural tolerance atlases, better residue correspondence layers, richer pocket-region comparisons, and stronger publication workflows.

## Why It Matters

Many projects can generate structures, but far fewer provide a clean path from predicted complexes to reproducible comparative interpretation across mutants and across alleles.

## Who It Serves

Computational immunology, structural bioinformatics, peptide-MHC method development, and labs that need cleaner report-ready structural comparison.

## How It Is Different

### End-to-end rather than fragmentary

It covers sequence resolution, mutation-panel generation, chain-aware modeling inputs, prediction parsing, structural feature extraction, allele aggregation, and reporting in one workflow.

### Peptide-MHC specific rather than generic

The architecture is organized around heavy chain, beta-2 microglobulin, peptide, WT-relative perturbations, and cross-allele comparison.

### Interpretable rather than opaque

The primary outputs are contact counts, minimum distances, WT-relative deltas, tolerance fingerprints, and pocket-signature summaries.

### Conservative rather than hype-driven

The framework repeatedly treats its outputs as descriptive and exploratory, with explicit caveats about coverage, prediction quality, and residue comparability.

## What Researchers Can Ask

- Which peptide positions appear structurally sensitive within an allele panel?
- Which substitutions repeatedly reduce peptide-heavy-chain contacts relative to WT?
- Which alleles show similar tolerance fingerprints under the same perturbation panel?
- Which heavy-chain residues recur across many peptide-contact patterns?
- Which observations are strong enough to write down as explicit exploratory hypotheses?

### Communication Outputs

- Markdown report
- Analysis snapshot
- Publication bundle
- Notebook-ready exports
- Case-study subsets

## One-Minute Summary

Most peptide-MHC structural workflows break down after prediction generation. This framework is built to bridge that gap. It organizes mutation panels, prepares real multichain inputs, ingests AlphaFold or ColabFold outputs, extracts interpretable structural features, compares mutants to WT, aggregates effects across alleles, and writes report-ready outputs. The main contribution is not a single score. It is a structured way to convert peptide-MHC prediction panels into reproducible comparative structural evidence.

## Related Files

- HTML version: [project_story.html](project_story.html)
- Spoken/research pitch: [PITCH.md](PITCH.md)
- Abstract text: [ABSTRACT.md](ABSTRACT.md)
- Slide outline: [SLIDES.md](SLIDES.md)
