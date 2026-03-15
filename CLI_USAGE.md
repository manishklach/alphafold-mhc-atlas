# CLI Usage

## Phase 12 additions

Program-memory, outcome-integration, and reusable workflow commands:

```bash
mhc-atlas workflow-template list
mhc-atlas workflow-template show --name weekly_mutation_review
mhc-atlas history summarize --workspace workspaces/demo_workspace.yaml
mhc-atlas review-cycle compare --workspace workspaces/demo_workspace.yaml --current week_2 --previous week_1
mhc-atlas decision-history build --workspace workspaces/demo_workspace.yaml
mhc-atlas outcomes import --workspace workspaces/demo_workspace.yaml --file data/outcome_templates.csv
mhc-atlas outcomes summarize --workspace workspaces/demo_workspace.yaml
mhc-atlas multicycle summarize --workspace workspaces/demo_workspace.yaml
mhc-atlas rationale summarize --workspace workspaces/demo_workspace.yaml
mhc-atlas workflow-metrics summarize --workspace workspaces/demo_workspace.yaml
mhc-atlas template-effectiveness summarize --workspace workspaces/demo_workspace.yaml
```

## First evaluator workflow

```bash
mhc-atlas list-demos
mhc-atlas demo-walkthrough golden_weekly_review_demo
mhc-atlas workspace inventory --workspace demo/golden_weekly_review_demo/workspace.yaml
mhc-atlas app --demo golden_weekly_review_demo
```

## Main commands

```bash
mhc-atlas run --config examples/sample_input.yaml
mhc-atlas app --project outputs/mhc_phase6_demo
mhc-atlas list-demos
mhc-atlas demo-walkthrough golden_weekly_review_demo
mhc-atlas inventory outputs/mhc_phase6_demo
mhc-atlas scenario --project outputs/mhc_phase6_demo --template disruptive_shortlist
mhc-atlas export --project outputs/mhc_phase6_demo --scenario outputs/mhc_phase6_demo/saved_scenarios/a_disruptive_shortlist.json
mhc-atlas report --project outputs/mhc_phase6_demo
mhc-atlas validate-config examples/sample_input.yaml
mhc-atlas check-environment
mhc-atlas version
```

## Pilot workflow commands

```bash
mhc-atlas review init --project demo/cross_allele_demo/project --scenario disruptive_shortlist
mhc-atlas review shortlist --project demo/cross_allele_demo/project
mhc-atlas feedback add --project demo/cross_allele_demo/project --entity-type variant --entity-id demoA_pos2_A --comment "Needs more evidence review"
mhc-atlas checklist run --project demo/cross_allele_demo/project --template pilot_handoff_review
mhc-atlas handoff create --project demo/cross_allele_demo/project --bundle-id pilot_bundle --scenario disruptive_shortlist
```

## Workspace and decision-review commands

```bash
mhc-atlas workspace inventory --workspace demo/golden_weekly_review_demo/workspace.yaml
mhc-atlas review-packet generate --workspace demo/golden_weekly_review_demo/workspace.yaml --packet-id golden_demo
mhc-atlas decision-packet generate --workspace demo/golden_weekly_review_demo/workspace.yaml --packet-id golden_manager_demo
mhc-atlas workspace init --config workspaces/demo_workspace.yaml
mhc-atlas workspace inventory --workspace workspaces/demo_workspace.yaml
mhc-atlas review-packet generate --workspace workspaces/demo_workspace.yaml
mhc-atlas decision-packet generate --workspace workspaces/demo_workspace.yaml
mhc-atlas role-view export --project demo/pilot_review_demo/project --role manager
mhc-atlas changes summarize --project demo/pilot_review_demo/project
mhc-atlas next-actions build --project demo/pilot_review_demo/project
```

## Conservative outcome-integration notes

- Outcome imports are contextual evidence, not relabeling of model truth.
- Template-effectiveness summaries are operational associations, not causal proof.
- Multi-cycle churn and closure metrics should be read as workflow signals, not biological validation.
