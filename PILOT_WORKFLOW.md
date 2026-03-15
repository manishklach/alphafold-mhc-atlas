# Pilot Workflow

## Phase 12 extension

The pilot workflow now supports reusable workflow templates, program memory, optional downstream outcomes, and conservative workflow-learning summaries across recurring review cycles.

That means a team can:

- reuse the same weekly review pattern across projects
- compare current and previous review cycles
- compare multiple review cycles, not just current versus previous
- see what was carried forward, resolved, or dropped
- surface recurring open questions and recurring review issues across a workspace
- attach downstream outcome context without relabeling the model as right or wrong
- inspect whether a workflow template is associated with lower unresolved carry-forward or lower churn

## Core workflow

1. Load a project or workspace
2. Inspect coverage and artifact availability
3. Review what changed since the last review cycle
4. Inspect ranked variants and current shortlist
5. Review open questions and next actions
6. Generate a weekly review packet
7. Export a manager-facing decision packet if needed
8. Import downstream outcomes if follow-up happened
9. Inspect multi-cycle history, rationale carry-forward, and workflow-effectiveness summaries

## Why this workflow exists

This product is meant to replace a fragile mix of:
- notebooks
- screenshots
- loosely tracked slide conclusions
- ad hoc reviewer memory

with a more reproducible, evidence-linked decision process.

## Role split

- Scientist: evidence drilldown and structural interpretation
- Computational lead: prioritization logic, scenario review, change analysis
- Manager/reviewer: decision focus, caveats, shortlist status, next actions

## Golden demo path

```bash
mhc-atlas app --workspace demo/golden_weekly_review_demo/workspace.yaml
mhc-atlas review-packet generate --workspace demo/golden_weekly_review_demo/workspace.yaml --packet-id golden_demo
mhc-atlas decision-packet generate --workspace demo/golden_weekly_review_demo/workspace.yaml --packet-id golden_manager_demo
mhc-atlas outcomes summarize --workspace workspaces/demo_workspace.yaml
mhc-atlas template-effectiveness summarize --workspace workspaces/demo_workspace.yaml
```
