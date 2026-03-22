# Research Pitch

Product name: **MHC Atlas OS**

Subtitle: **Peptide-MHC Decision Platform for Structure-Guided Experimental Prioritization**

## One-Sentence Pitch

MHC Atlas OS is a reproducible peptide-MHC decision platform that turns mutation panels and AlphaFold or ColabFold outputs into interpretable WT-relative, cross-allele, and report-ready structural summaries.

## 30-Second Pitch

We built a peptide-MHC structural perturbation framework that sits on top of AlphaFold or ColabFold outputs. It generates allele-aware mutant panels, prepares real multichain inputs, ingests predicted complexes, extracts transparent peptide-pocket contact features, compares mutants to WT, and aggregates those effects across alleles into tolerance fingerprints and pocket-signature summaries. The goal is reproducible comparative structural analysis and hypothesis generation, not black-box binding prediction.

## 1-Minute Spoken Pitch

Most peptide-MHC projects have a gap between running structure prediction and doing careful comparative analysis. People often end up with a collection of FASTA files, structure files, and one-off notebooks, but not a reproducible framework for asking comparative questions across mutants and across alleles.

This repository is designed to fill that gap. It takes one or more class-I alleles and peptide panels, generates allele-aware multichain inputs for AlphaFold or ColabFold, parses the resulting predicted complexes, extracts interpretable peptide-heavy-chain contact features, computes WT-relative structural deltas, and aggregates those effects into variant-level and allele-level tolerance fingerprints. It also supports cross-allele pocket-signature summaries, user-defined region comparisons, publication-oriented reports, case studies, and exploratory hypothesis outputs.

The important point is that it stays conservative. It does not claim binding affinity prediction or immunogenicity prediction. Instead, it gives researchers a structured way to turn predicted peptide-MHC models into transparent comparative structural evidence.

## Positioning

## What it is

- a peptide-MHC perturbation analysis framework
- a comparative structural analysis pipeline
- a report-ready scaffold for WT-versus-mutant and cross-allele studies
- a hypothesis-generation tool grounded in explicit computed outputs

## What it is not

- a binding affinity predictor
- an immunogenicity predictor
- an experimental validation substitute
- a black-box ranking model

## Why Researchers May Care

- it connects model preparation, structural parsing, comparative analysis, and reporting in one workflow
- it supports cross-allele analysis as a first-class concept
- it remains useful even when prediction coverage is incomplete
- it emphasizes interpretable outputs instead of opaque scores
- it reduces notebook sprawl by writing stable tables, plots, reports, and export bundles

## Main Differentiators

- peptide-MHC specific rather than generic protein structure tooling
- allele-resolved multichain inputs rather than allele-name-only metadata
- WT-relative structural perturbation analysis built into the core workflow
- cross-allele tolerance and pocket-signature comparison
- publication-oriented reporting and export bundle generation
- explicit scientific caveats throughout the pipeline

## Example Questions It Helps Address

- which peptide positions appear structurally sensitive within an allele panel?
- which substitutions most often reduce peptide-heavy-chain contacts relative to WT?
- do two alleles show similar tolerance fingerprints across the same perturbation panel?
- which heavy-chain residues or user-defined pocket regions recur across many variants?
- which comparative observations are strong enough to elevate into explicit exploratory hypotheses?

## Suggested Lab-Meeting Framing

### Slide 1: Problem

- peptide-MHC structure prediction is easier than consistent comparative analysis
- outputs often end up fragmented across FASTA files, structure folders, and notebooks
- cross-allele comparisons are especially hard to organize reproducibly

### Slide 2: What this framework does

- builds allele-aware mutant panels
- prepares AlphaFold or ColabFold-ready multichain inputs
- parses predicted complexes
- extracts WT-relative structural features
- aggregates effects across variants and alleles

### Slide 3: What comes out

- contact summaries
- WT-relative deltas
- tolerance fingerprints
- pocket-signature summaries
- cross-allele similarity tables
- reports, figures, and case-study bundles

### Slide 4: What it does not claim

- not a binding predictor
- not an immunogenicity predictor
- not proof of mechanism
- exploratory and coverage-dependent

### Slide 5: Why it is useful

- reproducible
- interpretable
- modular
- ready for comparative studies and publication workflows

## Poster Or Abstract Language

This framework provides a reproducible pipeline for comparative peptide-MHC structural perturbation analysis using AlphaFold or ColabFold-derived models. It supports allele-resolved multichain input generation, defensive prediction parsing, peptide-heavy-chain contact extraction, WT-relative structural comparison, allele-level tolerance fingerprinting, pocket-signature analysis, and publication-oriented reporting. The design emphasizes transparent structural summaries and exploratory hypothesis generation rather than black-box biological prediction.

## Short Email / DM Intro

I’ve been building a peptide-MHC comparative structural analysis framework that sits on top of AlphaFold or ColabFold outputs. It generates allele-aware mutant panels, extracts WT-relative peptide-pocket contact changes, aggregates them across alleles, and produces report-ready tables and figures. The emphasis is on reproducible, interpretable structural comparison rather than binding prediction.
