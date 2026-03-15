# Quickstart

## What to run first

Use the golden weekly-review demo. It is the clearest product walkthrough for a new evaluator.

## 5-minute path

1. Create an environment and install:

```bash
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[app,dev]
```

2. List demos and inspect the canonical one:

```bash
mhc-atlas list-demos
mhc-atlas demo-walkthrough golden_weekly_review_demo
```

3. Launch the app on the golden workspace:

```bash
mhc-atlas app --demo golden_weekly_review_demo
```

4. Generate the key meeting artifacts:

```bash
mhc-atlas review-packet generate --workspace demo/golden_weekly_review_demo/workspace.yaml --packet-id golden_demo
mhc-atlas decision-packet generate --workspace demo/golden_weekly_review_demo/workspace.yaml --packet-id golden_manager_demo
```

5. Inspect `Workspace Overview`, `Changes Since Last Review`, `Weekly Review Packet`, `Role Views`, and `Next Actions`.

## Pilot workflow in 2 more commands

```bash
mhc-atlas review init --project demo/cross_allele_demo/project --scenario disruptive_shortlist
mhc-atlas handoff create --project demo/cross_allele_demo/project --bundle-id pilot_bundle --scenario disruptive_shortlist
```

## Start your own project

If you are evaluating the repo for a real study, do this after the demo:

1. Copy [examples/researcher_project_template.yaml](examples/researcher_project_template.yaml).
2. Fill in your allele names, trusted sequences, WT peptide(s), mutation positions, and substitutions.
3. Run:

```bash
mhc-atlas run --config examples/researcher_project_template.yaml
```

4. Add AlphaFold or ColabFold outputs under `outputs/<project>/predictions/`.
5. Rerun the same command.
6. Open the project:

```bash
mhc-atlas app --project outputs/my_peptide_mhc_project
```

Detailed guide:
- [MY_FIRST_PROJECT.md](MY_FIRST_PROJECT.md)

## Workspace path

```bash
mhc-atlas workspace inventory --workspace workspaces/demo_workspace.yaml
mhc-atlas review-packet generate --workspace workspaces/demo_workspace.yaml
mhc-atlas decision-packet generate --workspace workspaces/demo_workspace.yaml
mhc-atlas app --workspace workspaces/demo_workspace.yaml
```

## Scientific caveat

This product is conservative by design. It supports exploratory structural analysis, prioritization, and review workflows. It does not claim binding prediction, immunogenicity prediction, mechanistic proof, or replacement of experimental validation.
