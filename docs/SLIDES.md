# Slide Outline

## Goal

Use this outline for a lab meeting, internal demo, collaborator intro, or conference-style methods presentation.

## Slide 1: Problem

Title:

`From peptide-MHC structure prediction to comparative analysis`

Key points:

- generating AlphaFold or ColabFold models is only part of the workflow
- comparative WT-versus-mutant analysis is often handled through fragmented scripts or notebooks
- cross-allele comparison is especially hard to organize reproducibly
- report and figure generation are usually disconnected from the analysis layer

Takeaway:

There is a tooling gap between model generation and structured comparative interpretation.

## Slide 2: What This Framework Does

Title:

`A reproducible peptide-MHC structural perturbation framework`

Key points:

- resolves allele inputs into real chain sequences
- builds allele-aware mutation panels
- writes multichain AlphaFold or ColabFold-ready inputs
- parses predicted complexes defensively
- extracts peptide-pocket contact features
- compares mutants to WT
- aggregates effects across alleles

Takeaway:

The framework covers the path from input preparation to comparative outputs.

## Slide 3: Core Analysis Outputs

Title:

`Transparent structural summaries rather than black-box scores`

Key points:

- peptide-heavy-chain contact counts
- minimum distances
- WT-relative contact deltas
- tolerance fingerprints
- pocket-signature summaries
- cross-allele similarity tables

Takeaway:

The outputs are interpretable and inspectable.

## Slide 4: What Makes It Different

Title:

`Why this is more than another AlphaFold helper repo`

Key points:

- peptide-MHC specific rather than generic protein structure tooling
- allele-resolved multichain modeling inputs
- robust to missing predictions and partial runs
- cross-allele comparison built into the workflow
- reporting, publication bundle, and case-study support
- explicit scientific caveats throughout

Takeaway:

The differentiator is the combination of comparative scope, interpretability, and reproducibility.

## Slide 5: What It Does Not Claim

Title:

`Conservative by design`

Key points:

- not a binding affinity predictor
- not an immunogenicity predictor
- not proof of mechanism
- not a substitute for experimental validation
- residue overlap is not treated as canonical equivalence without explicit mapping

Takeaway:

The framework is intended for exploratory structural analysis and hypothesis generation.

## Slide 6: Reporting And Reuse

Title:

`Designed for papers, notebooks, and iterative case studies`

Key points:

- markdown report generation
- analysis snapshot for reproducibility
- publication bundle with figures and tables
- notebook-ready exports
- case-study filtering
- local HTML dashboard

Takeaway:

The outputs are structured for downstream communication, not just internal debugging.

## Slide 7: Vision

Title:

`Toward comparative peptide-MHC structural tolerance atlases`

Key points:

- stronger residue correspondence across alleles
- richer pocket-region comparisons
- broader multi-allele panels
- higher-quality comparative figures and reports
- reusable comparative structural datasets for downstream methods work

Takeaway:

The long-term vision is a rigorous comparative framework for structural tolerance studies, not a hype-driven scoring engine.

## Closing Slide

Title:

`Summary`

Key points:

- reproducible peptide-MHC structural perturbation workflow
- interpretable WT-relative and cross-allele outputs
- built for comparative research and hypothesis generation
- conservative about biological claims

Suggested close:

`The main contribution is not a single score. It is a structured way to turn peptide-MHC prediction panels into reproducible comparative structural evidence.`
