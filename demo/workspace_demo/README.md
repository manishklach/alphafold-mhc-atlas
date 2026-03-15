# Workspace Demo

This demo shows the phase-10 multi-project workspace workflow.

Use it to inspect:

- a workspace inventory across multiple demo projects
- weekly review packet generation at the workspace level
- project history and change summaries per project
- role-oriented exports without losing the conservative scope statement

Recommended commands:

```bash
mhc-atlas workspace inventory --workspace workspaces/demo_workspace.yaml
mhc-atlas review-packet generate --workspace workspaces/demo_workspace.yaml
mhc-atlas decision-packet generate --workspace workspaces/demo_workspace.yaml
mhc-atlas app --workspace workspaces/demo_workspace.yaml
```
