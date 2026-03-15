# Golden Weekly Review Demo

This is the canonical end-to-end demo for the product wedge:

interpretable decision support for structure-guided experimental prioritization.

## What this demo shows

- a workspace-centered weekly review workflow
- changes since last review
- review packet generation
- scientist, computational lead, and manager views
- shortlist, next actions, and open questions
- a meeting-ready decision packet

## Recommended command

```bash
mhc-atlas app --workspace demo/golden_weekly_review_demo/workspace.yaml
```

If you want to move from this demo into a real project setup, continue with:

- [../../docs/NEW_RESEARCHER_GUIDE.md](../../docs/NEW_RESEARCHER_GUIDE.md)

## Fast path

```bash
mhc-atlas workspace inventory --workspace demo/golden_weekly_review_demo/workspace.yaml
mhc-atlas review-packet generate --workspace demo/golden_weekly_review_demo/workspace.yaml --packet-id golden_demo
mhc-atlas decision-packet generate --workspace demo/golden_weekly_review_demo/workspace.yaml --packet-id golden_manager_demo
mhc-atlas role-view export --project demo/pilot_review_demo/project --role manager
mhc-atlas next-actions build --project demo/pilot_review_demo/project
```

## What to focus on

1. `Workspace Overview`
2. `Changes Since Last Review`
3. `Weekly Review Packet`
4. `Role Views`
5. `Next Actions`
6. `Review Queues / Shortlists`
7. `Decision Packet`

## Conservative by design

This demo is meant to show review workflow quality, evidence linkage, and product wedge clarity.
It is not a claim of binding prediction, immunogenicity prediction, or experimental validation.
