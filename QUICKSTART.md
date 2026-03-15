# Quickstart

## 5-minute path

1. Create an environment and install:

```bash
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[app,dev]
```

2. Run the sample pipeline:

```bash
mhc-atlas run --config examples/sample_input.yaml
```

3. Launch the app with a demo:

```bash
mhc-atlas app --demo pilot_review_demo
```

4. Or launch the app on your own output directory:

```bash
mhc-atlas app --project outputs/mhc_phase6_demo
```

5. Inspect rankings, panels, scenarios, evidence drilldown, the pilot review queue, and the manager role view.

## Pilot workflow in 2 more commands

```bash
mhc-atlas review init --project demo/cross_allele_demo/project --scenario disruptive_shortlist
mhc-atlas handoff create --project demo/cross_allele_demo/project --bundle-id pilot_bundle --scenario disruptive_shortlist
```

## Workspace path

```bash
mhc-atlas workspace inventory --workspace workspaces/demo_workspace.yaml
mhc-atlas review-packet generate --workspace workspaces/demo_workspace.yaml
mhc-atlas decision-packet generate --workspace workspaces/demo_workspace.yaml
mhc-atlas app --workspace workspaces/demo_workspace.yaml
```
