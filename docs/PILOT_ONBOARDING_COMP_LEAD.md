# Pilot Onboarding: Computational Lead

Welcome to the structural decision platform evaluation.

## Your Role in the Pilot
Your main goal is to ensure the pipeline runs cleanly, the workflow effectiveness is visible, and bottlenecks are tracked.

## What to Do First
1. **Check Pilot Readiness:** Run `mhc-atlas pilot-readiness check --workspace <your_workspace.yaml>`
2. **Generate Weekly Packets:** Ensure the `Weekly Review Packet` generation runs without error and role views are exported.
3. **Inspect Execution Metrics:** Go to `Execution Metrics` to see if tasks assigned in the review meeting are actually being closed out.

## What to Trust vs Ignore
- **Trust:** The pipeline determinism, the file-backed tracking, and the operational closure metrics.
- **Ignore:** Treating high execution throughput as proof that the underlying AlphaFold models were "correct".

## Common Mistakes
- **Over-engineering the data:** Do not try to attach generic LIMS tracking here. Keep it lightweight and focused on review handoffs.
