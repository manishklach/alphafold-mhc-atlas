# v0.10.0 - Weekly Decision Review Platform

Phase 10 turns the repo from a packaged single-project analyst tool into a local-first weekly decision-review platform for recurring scientific team workflows.

## Highlights

- Added multi-project workspace support with YAML/JSON workspace definitions and workspace inventory outputs.
- Added project history and program memory utilities to summarize what changed since prior review cycles.
- Added weekly review packet generation for projects and workspaces.
- Added meeting-oriented decision packet exports for internal review workflows.
- Added role-oriented views for scientist, computational lead, and manager/reviewer audiences.
- Added next-action and open-question generation grounded in current artifacts and review state.
- Extended the Streamlit app and CLI to support workspace mode and weekly review workflows.
- Added recurring review cadence templates and workspace/demo assets for pilot-customer walkthroughs.

## New workflow surfaces

- `mhc-atlas workspace inventory --workspace workspaces/demo_workspace.yaml`
- `mhc-atlas review-packet generate --workspace workspaces/demo_workspace.yaml --packet-id weekly_demo`
- `mhc-atlas decision-packet generate --workspace workspaces/demo_workspace.yaml --packet-id meeting_demo`
- `mhc-atlas role-view export --project demo/pilot_review_demo/project --role manager`
- `mhc-atlas next-actions build --project demo/pilot_review_demo/project`
- `mhc-atlas app --workspace workspaces/demo_workspace.yaml`

## Scope and guardrails

This release preserves the repo's conservative framing:

- not a binding affinity predictor
- not an immunogenicity predictor
- not proof of mechanism
- not a substitute for experimental validation
- residue overlap is not treated as canonical equivalence without explicit mapping

The platform remains intended for exploratory structural analysis, prioritization support, review workflows, and experimental planning with explicit caveats.

## Verification

- `python -m pytest -q`
- `python -m build`
- `python -m src.cli workspace inventory --workspace workspaces/demo_workspace.yaml`
- `python -m src.cli review-packet generate --workspace workspaces/demo_workspace.yaml --packet-id weekly_demo`
- `python -m src.cli decision-packet generate --workspace workspaces/demo_workspace.yaml --packet-id meeting_demo`
