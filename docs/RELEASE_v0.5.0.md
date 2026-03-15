# v0.5.0 - Peptide-MHC Comparative Analysis Framework

## Summary

This release establishes the first complete private distribution of the peptide-MHC comparative structural analysis framework.

The project now supports:

- peptide-MHC mutation-panel generation
- allele-resolved multichain AlphaFold or ColabFold-ready inputs
- defensive parsing of predicted complex outputs
- WT-relative structural contact analysis
- variant-level and allele-level tolerance fingerprints
- cross-allele pocket-signature and similarity analysis
- user-defined pocket-region aggregation hooks
- markdown reporting and publication-bundle exports
- case-study filtering
- exploratory hypothesis generation
- a local HTML dashboard for browsing runs, tables, plots, reports, and upload guidance

## Included In This Release

### Core analysis pipeline

- YAML or JSON config loading with backward-compatible schema normalization
- explicit or local-reference MHC sequence resolution
- deterministic mutant-panel generation
- multimer FASTA generation for class-I peptide-MHC complexes
- chain manifests and ColabFold-oriented input tables
- permissive prediction ingestion for common AlphaFold or ColabFold artifact layouts

### Structure-aware analysis

- PDB and mmCIF parsing
- chain-role mapping with confidence-aware fallbacks
- peptide-heavy-chain contact extraction
- minimum-distance summaries
- WT-relative structural delta calculations
- optional geometry metrics where possible

### Comparative outputs

- variant-level tolerance fingerprints
- aggregation by peptide position and substitution
- allele-level tolerance fingerprints
- residue-level pocket-signature summaries
- cross-allele similarity matrices
- raw contacting-residue overlap tables
- region-level aggregation via user-defined pocket mappings

### Reporting and publication support

- markdown report generation
- report summary JSON
- analysis snapshot JSON
- publication bundle with selected figures and tables
- notebook-ready exports
- case-study output folders
- structured exploratory hypotheses with evidence references

### Local HTML dashboard

- project browser for `outputs/`
- config-based pipeline launcher
- table viewer
- plot gallery
- report preview
- case-study browser
- prediction upload guidance
- fallback metadata derivation for older runs

## Scientific Positioning

This framework is designed for comparative structural analysis and hypothesis generation.

It does **not** claim:

- binding affinity prediction
- immunogenicity prediction
- experimental validation
- causal biological mechanism from predicted structural changes alone

The emphasis is on reproducible, interpretable, and coverage-aware structural summaries.

## Notes

- This release is intentionally conservative and local-workspace friendly.
- Prediction folders are expected to be generated externally and copied into the appropriate `outputs/<project>/predictions/<variant_id>/` directories.
- Cross-allele residue comparisons remain raw-identifier based unless a user-defined mapping layer is supplied.
