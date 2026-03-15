# First Run

## What this product is

`mhc-atlas` is an interpretable decision platform for structure-guided experimental prioritization.

Initial wedge:
- peptide-MHC perturbation analysis

What it is meant to improve:
- recurring scientific review workflows
- evidence-linked shortlist and panel discussion
- decision memory across weekly meetings
- cleaner handoff between scientist, computational lead, and reviewer

## Best first demo

Use the golden weekly-review demo.

```bash
mhc-atlas app --workspace demo/golden_weekly_review_demo/workspace.yaml
```

## 5-minute evaluator path

```bash
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[app,dev]
mhc-atlas list-demos
mhc-atlas workspace inventory --workspace demo/golden_weekly_review_demo/workspace.yaml
mhc-atlas app --workspace demo/golden_weekly_review_demo/workspace.yaml
```

## What to click first

1. `Workspace Overview`
2. `Changes Since Last Review`
3. `Weekly Review Packet`
4. `Role Views`
5. `Next Actions`

## Scientific scope

The product is conservative by design. It is intended for exploratory structural analysis, prioritization support, and review workflows. It does not claim binding prediction, immunogenicity prediction, mechanistic proof, or experimental validation.
