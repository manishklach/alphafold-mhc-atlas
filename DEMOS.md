# Demos

## Start here

Recommended first demo:

- `golden_weekly_review_demo`

It is the single best end-to-end story for the current product wedge: recurring structure-guided weekly decision review.

## Available demos

- `golden_weekly_review_demo`
- `small_project`
- `cross_allele_demo`
- `pilot_review_demo`
- `workspace_demo` (workspace README and config)
- `weekly_review_demo` (workflow README)
- `role_views_demo` (role-view README)

List demos:

```bash
mhc-atlas list-demos
mhc-atlas demo-walkthrough golden_weekly_review_demo
```

Launch app with demo:

```bash
mhc-atlas app --demo golden_weekly_review_demo
mhc-atlas app --workspace workspaces/demo_workspace.yaml
```

Validate a demo:

```bash
mhc-atlas validate-demo small_project
mhc-atlas validate-demo golden_weekly_review_demo
```

Golden demo packet flow:

```bash
mhc-atlas workspace inventory --workspace demo/golden_weekly_review_demo/workspace.yaml
mhc-atlas review-packet generate --workspace demo/golden_weekly_review_demo/workspace.yaml --packet-id golden_demo
mhc-atlas decision-packet generate --workspace demo/golden_weekly_review_demo/workspace.yaml --packet-id golden_manager_demo
mhc-atlas role-view export --project demo/pilot_review_demo/project --role manager
```
