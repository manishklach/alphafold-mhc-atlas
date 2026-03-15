# New Researcher Guide

This is the best single document for a new researcher, lab member, collaborator, or pilot evaluator using this repo for the first time.

## What this project is

This platform is a local-first, interpretable decision system for structure-guided experimental prioritization, with an initial wedge in peptide-MHC perturbation analysis.

It is best for:

- generating peptide-MHC mutation panels
- preparing AlphaFold or ColabFold-ready multichain inputs
- analyzing WT-versus-mutant structural perturbations from predicted complexes
- ranking variants and compact panels with visible evidence
- generating review packets, role views, next actions, and decision materials for recurring team workflows

## What it does not claim

What It Does Not Claim

Conservative by design

Key points:
- not a binding affinity predictor
- not an immunogenicity predictor
- not proof of mechanism
- not a substitute for experimental validation
- residue overlap is not treated as canonical equivalence without explicit mapping

Takeaway:
The framework is intended for exploratory structural analysis and hypothesis generation.

## Prerequisites

- Python 3.11 or newer
- a local clone of the repo
- optional: Streamlit app extras if you want the interactive UI
- real allele sequences if you want true multichain FASTA generation
- AlphaFold or ColabFold outputs later if you want structure-aware analysis

Install:

```bash
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[app,dev]
```

Expected repo-level folders you will interact with:

- `examples/`
- `data/`
- `outputs/`
- `demo/`

## First 10-minute workflow

Use the canonical demo first.

```bash
mhc-atlas list-demos
mhc-atlas demo-walkthrough golden_weekly_review_demo
mhc-atlas app --demo golden_weekly_review_demo
```

In the app, inspect this order:

1. `Workspace Overview`
2. `Changes Since Last Review`
3. `Weekly Review Packet`
4. `Role Views`
5. `Next Actions`
6. `Open Questions`

Optional packet commands:

```bash
mhc-atlas review-packet generate --workspace demo/golden_weekly_review_demo/workspace.yaml --packet-id golden_demo
mhc-atlas decision-packet generate --workspace demo/golden_weekly_review_demo/workspace.yaml --packet-id golden_manager_demo
```

## How to run a new project

Start from:

- [../examples/researcher_project_template.yaml](../examples/researcher_project_template.yaml)

### 1. Define allele(s)

For each allele, provide:

- `allele_name`
- `class_type`
- `heavy_chain_sequence`
- `beta2m_sequence`

You can also use a local reference mapping in:

- [../data/allele_reference.yaml](../data/allele_reference.yaml)

Preferred public source for official HLA allele sequences:

- IPD-IMGT/HLA

### 2. Define peptide(s)

In the config, set:

- `wildtype_sequences`
- `mutation_positions`
- `allowed_substitutions`

### 3. Generate inputs

```bash
mhc-atlas run --config examples/researcher_project_template.yaml
```

This creates:

- manifests
- chain manifests
- AlphaFold or ColabFold-ready multichain FASTA inputs when sequences are present
- initial output scaffolding

### 4. Place prediction outputs

Run AlphaFold or ColabFold outside this repo, then place prediction outputs under:

- `outputs/<project>/predictions/`

### 5. Run analysis again

```bash
mhc-atlas run --config examples/researcher_project_template.yaml
```

### 6. Open the project

```bash
mhc-atlas app --project outputs/my_peptide_mhc_project
```

## What the outputs mean

### Summary tables

These are the main CSV outputs for variant-level and project-level analysis. They are the fastest way to inspect rankings, evidence coverage, uncertainty, and panel membership.

### Weekly review packets

These are concise review-meeting summaries. They focus on what changed, what is currently prioritized, what caveats remain, and what should be discussed next.

### Decision packets

These are meeting-ready exports for team review. They are shorter than full reports and emphasize shortlist, caveats, open questions, and next actions.

### Shortlists

These are reviewer-maintained subsets of ranked outputs. They are useful for narrowing discussion, not for declaring biological truth.

### Role views

These tailor emphasis by audience:

- scientist: more evidence and structural detail
- computational lead: more robustness, logic, and change analysis
- manager/reviewer: fewer low-level details, but still caveat-aware

### Next actions

These are structured suggestions derived from current artifacts. They help move from analysis to decision workflow, but they are not authoritative biology recommendations.

### Open questions

These capture unresolved issues such as unstable rankings, missing evidence, or conflicting scenario outputs that should be discussed explicitly.

## What not to overinterpret

Do not treat any of this as:

- binding affinity prediction
- immunogenicity prediction
- proof of biological mechanism
- replacement for wet-lab validation
- certainty just because a ranking exists

Also avoid:

- overreading rankings without checking uncertainty
- comparing variants without confirming structural support exists
- treating residue overlap across alleles as canonical equivalence without explicit mapping

## Recommended workflow for a researcher

1. start with the golden demo
2. run one real project with the researcher template
3. inspect ranking outputs and evidence drilldown
4. compare scenarios if conclusions look sensitive
5. build a shortlist
6. generate a weekly review packet
7. discuss with the computational lead or manager/reviewer
8. export next actions and decision materials

## Common pitfalls

- missing prediction outputs in `predictions/`
- weak structural support being treated as strong evidence
- incomplete or low-confidence chain mapping
- overinterpreting rank position without looking at evidence components
- comparing projects or scenarios without checking uncertainty and coverage
- using placeholder allele metadata when true sequence-resolved FASTA generation is required

## Suggested documentation stack

- [../README.md](../README.md): product overview
- [../QUICKSTART.md](../QUICKSTART.md): 5-minute start
- [NEW_RESEARCHER_GUIDE.md](NEW_RESEARCHER_GUIDE.md): onboarding and real-project use
- [../DEMOS.md](../DEMOS.md): demo paths
- [../PILOT_WORKFLOW.md](../PILOT_WORKFLOW.md): recurring team-review workflow
