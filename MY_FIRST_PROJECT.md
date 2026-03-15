# My First Project

This guide is the shortest path for a researcher who wants to use this repo on a real peptide-MHC project.

## What you need

- one or more allele names
- trusted heavy-chain and beta-2 microglobulin sequences for those alleles
- one or more WT peptide sequences
- a mutation plan: positions and allowed substitutions
- AlphaFold or ColabFold outputs later, if you want structure-aware analysis

## Step 1: copy the researcher template

Start from:

- [examples/researcher_project_template.yaml](examples/researcher_project_template.yaml)

It also appears in the local HTML dashboard example dropdown so you can launch the first run without memorizing the path.

## Step 2: provide real allele sequences

Use one of these approaches:

1. Put sequences directly in the config under:
   - `heavy_chain_sequence`
   - `beta2m_sequence`
2. Or populate:
   - [data/allele_reference.yaml](data/allele_reference.yaml)
   - [data/public_allele_reference_template.yaml](data/public_allele_reference_template.yaml)

Preferred public source:
- IPD-IMGT/HLA

Important:
- this repo does not ship copied allele sequences by default
- metadata-only fallback is allowed for setup and review, but true multichain FASTA generation requires real sequences

## Step 3: edit the project definition

Set:

- `project_name`
- `output_dir`
- `alleles`
- `wildtype_sequences`
- `mutation_positions`
- `allowed_substitutions`

## Step 4: generate inputs

```bash
mhc-atlas run --config examples/researcher_project_template.yaml
```

This creates:
- manifests
- chain manifests
- multichain FASTA inputs when allele sequences are available
- a project analysis directory and summary scaffolding

## Step 5: run structure prediction outside this repo

Run AlphaFold or ColabFold using the generated FASTA inputs, then place outputs in:

- `outputs/<project>/predictions/`

## Step 6: rerun analysis

```bash
mhc-atlas run --config examples/researcher_project_template.yaml
```

Now the repo can parse structures, compute deltas, build fingerprints, rankings, and review artifacts.

## Step 7: inspect the project

```bash
mhc-atlas app --project outputs/<your_project_name>
```

Use this order:
1. `Project Overview`
2. `Ranking Explorer`
3. `Variant Explorer`
4. `Panel Designer`
5. `Reports / Exports`

## If you want recurring review workflows

Once one project is working, you can:
- generate review packets
- generate decision packets
- create review queues and shortlists
- add feedback and notes
- group projects into a workspace

## What this does not mean

This is still conservative by design:
- not a binding affinity predictor
- not an immunogenicity predictor
- not proof of mechanism
- not a substitute for experimental validation

Use it to support interpretation, prioritization, and planning, not to replace biological validation.
