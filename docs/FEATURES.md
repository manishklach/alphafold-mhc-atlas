# Feature Inventory

This document lists the current repository features by area and marks what is implemented now versus intentionally left conservative.

## 1. Configuration and Compatibility

Implemented:

- YAML and JSON config loading
- legacy phase-1 and phase-2 config normalization
- multi-allele config support
- shared or allele-specific peptide panels
- path normalization relative to the config file
- explicit validation for common schema errors

Conservative limits:

- class-I focused
- no internet-backed allele resolution
- no dynamic external database sync

## 2. Allele and Sequence Handling

Implemented:

- explicit heavy-chain and beta-2 microglobulin sequences in config
- local allele reference file support
- metadata-only fallback mode when allowed
- deterministic sequence-aware input construction

Conservative limits:

- no fragile online downloaders
- no class-II workflow

## 3. Peptide Variant Generation

Implemented:

- WT preservation
- single-position substitution panel generation
- deterministic variant ids across alleles
- local variant labels for readable WT-relative interpretation

Conservative limits:

- no combinatorial higher-order mutants yet
- no insertions or deletions

## 4. AlphaFold or ColabFold Input Preparation

Implemented:

- multichain FASTA output per variant
- chain manifest with role, length, and sequence hash
- machine-readable variants table
- ColabFold-style concatenated query string from real sequences

Conservative limits:

- not an AlphaFold 3-specific pipeline contract
- no built-in remote inference submission
- no scheduler or job orchestration layer

## 5. Prediction Parsing

Implemented:

- ranking and confidence parsing from common AlphaFold artifacts
- PAE summary parsing from `npz` or JSON when present
- best-available structure file discovery
- permissive behavior when prediction folders are missing

Conservative limits:

- parser is defensive, not exhaustive across every release variant
- missing artifacts become `NA`, not inferred values

## 6. Structure Parsing and Chain Mapping

Implemented:

- PDB and mmCIF support
- chain listing and residue extraction
- chain-role mapping using generated input context
- confidence-aware chain mapping behavior
- safe skipping on ambiguous mappings

Conservative limits:

- no unsafe hardcoded chain-id assumptions
- ambiguous mappings suppress structural metrics rather than guessing

## 7. Structural Contact Analysis

Implemented:

- peptide-position contact counts
- peptide-position minimum distance to heavy chain
- heavy-chain residue contact tables
- total peptide-heavy-chain contact summaries
- WT-relative structural deltas
- optional simple geometry metrics

Conservative limits:

- no claim of pocket occupancy or energetic consequence
- no full superposition-heavy analysis

## 8. Variant and Allele Fingerprints

Implemented:

- variant-level tolerance fingerprints
- aggregation by mutated position
- aggregation by substitution
- allele-level tolerance fingerprints
- allele position and substitution fingerprints

Conservative limits:

## 15. Pilot Workflows and Reviewability

Implemented:

- file-backed review queues
- shortlist and rejection artifacts
- structured feedback capture and summaries
- local annotations and markdown notes
- checklist templates and checklist-run exports
- collaborator handoff bundles
- local session and action logging
- descriptive review analytics

Conservative limits:

- no cloud collaboration backend
- no hidden database state
- reviewer input is not treated as scientific validation

## 16. Weekly Decision Review Workflows

Implemented:

- multi-project workspace configs and inventory exports
- project history snapshots and change summaries
- weekly review packets for projects and workspaces
- scientist, comp-lead, and manager role views
- next-action and open-question tables
- meeting-ready decision packets

Conservative limits:

- no cloud PM or enterprise workflow stack
- role views are summaries, not different scientific truths
- meeting packets are not validation artifacts

- no opaque learned composite score
- no ranking presented as biological truth

## 9. Pocket Signatures and Cross-Allele Comparison

Implemented:

- residue-level pocket signatures from contacting heavy-chain residues
- pocket signature summary tables
- allele similarity matrices
- pocket residue Jaccard overlap
- raw shared and allele-unique contact residue tables

Conservative limits:

- raw residue identifiers are not treated as canonical cross-allele equivalence
- pocket signatures are contact-derived summaries, not definitive biochemical definitions

## 10. Pocket-Region Hooks

Implemented:

- user-defined region mapping file
- region-level contact aggregation
- allele region signatures
- region overlap summary

Conservative limits:

- no built-in canonical ontology
- region comparison quality depends entirely on the supplied mapping

## 11. Reporting and Publication Support

Implemented:

- markdown report generation
- report summary JSON
- analysis snapshot JSON
- figure manifest
- table manifest
- publication bundle with figures, tables, manifests, and notebook exports

Conservative limits:

- no automatic prose generation beyond factual templates
- no giant report engine

## 12. Case Studies

Implemented:

- named case studies in config
- filtered variants, fingerprints, contacts, and summaries
- per-case markdown and JSON summary
- per-case manifests

Conservative limits:

- case studies filter existing outputs only
- no separate per-case recomputation or reranking

## 13. Hypothesis Generation

Implemented:

- structured exploratory hypothesis table
- markdown hypothesis summary
- supporting evidence JSON
- category-based hypothesis generation

Conservative limits:

- no conclusions stated as facts
- no hypothesis without cited supporting outputs

## 14. Provenance and Reproducibility

Implemented:

- config digest
- requirements digest
- timestamp
- pipeline version string
- git commit hash if available

Conservative limits:

- no full experiment tracking database
- no artifact store

## 15. Testing

Implemented:

- unit and lightweight integration tests across config, parsing, structure analysis, reporting, and provenance
- toy fixtures for structure parsing and contact analysis

Conservative limits:

- no large benchmark dataset included
- no heavy end-to-end inference tests

## 17. Execution and Follow-up (Phase 13)

Implemented:

- execution plans derived directly from shortlists, next actions, and open questions
- execution bundles to package selected variants and tasks for downstream follow-up
- ownership and status tracking for follow-up tasks
- action-to-outcome traceability, connecting execution tasks to downstream outcomes
- operational templates and follow-up checklists
- conservative operational metrics that track task completion rather than biological validation

Conservative limits:

- not a generic task-management or PM tool
- no automatic structural ranking updates based on task completion
- metrics remain descriptive, not predictive

## 18. Retrospective Reporting and Pattern Synthesis (Phase 14)

Implemented:

- retrospective program reporting across multiple review cycles and projects
- conservative pattern synthesis from review, execution, and outcome traces
- role-specific retrospective views (scientist, comp-lead, manager)
- reusable retrospective templates (monthly, quarterly, workflow-specific)
- structured meeting and slide outlines grounded in actual outputs
- deterministic artifact selection for evidence-linked summaries

Conservative limits:

- no auto-generation of marketing slides or fluff
- no causal claims from purely associational pattern synthesis
- no predictive modeling of program success

## 19. Pilot Deployment and Evaluation (Phase 15)

Implemented:

- automated pilot readiness checks
- portable setup pack creation
- reusable role-based operating workflows
- commercial evaluation guides and success criteria
- workspace evaluation sequence generation (Day 1, 3, 7 plans)

Conservative limits:

- no SaaS hosting or multi-tenant infrastructure
- no user auth systems
- evaluation guides remain grounded in operational usefulness, not biological guarantees

## 20. Planned Next-Step Areas

Most likely future directions:

- stronger residue correspondence across alleles
- class-II extension if needed
- richer case-study figure selection
- notebook or Quarto templates using the analysis snapshot
- publication-grade comparative panel assembly
