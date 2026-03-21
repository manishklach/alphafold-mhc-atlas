# MHC Atlas OS

## Overview
A structure-guided decision system for prioritizing peptide mutations using AlphaFold-derived structures.

MHC Atlas OS is designed for interpretable review workflows. It parses structure files, compares WT and mutant states, ranks candidates with explicit rules, applies policy checks, and generates readable decision outputs through both an API and a lightweight UI.

## Features
- Structure parsing (PDB/mmCIF)
- WT vs mutant comparison
- Interpretable prioritization engine
- Policy-based decision rules
- API + UI interface
- Decision reports
- Memory tracking

## Architecture
- Biology layer: parsing and structural comparison
- Core layer: scoring, policies, and reporting
- Agent layer: thin wrappers around reusable workflow steps
- API layer: FastAPI endpoints for parse, compare, rank, and pipeline
- UI layer: Streamlit interface for interactive review

## Quickstart
1. `pip install -r requirements.txt`
2. `uvicorn apps.api.main:app --reload`
3. `streamlit run apps/ui/app.py`

Open:
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8501`

## Example
Run the full pipeline with the demo structures:

```bash
curl -X POST "http://127.0.0.1:8000/pipeline" ^
  -H "Content-Type: application/json" ^
  -d "{\"wt_file\":\"data/demo_structures/wt_example.pdb\",\"mutant_file\":\"data/demo_structures/mutant_example_a.pdb\",\"candidate_id\":\"demo\"}"
```

Or use the same payload in the FastAPI docs page at `http://127.0.0.1:8000/docs`.

The `/pipeline` endpoint:
- parses the WT structure
- parses the mutant structure
- compares both structures
- ranks the candidate
- applies policy checks
- saves a decision record
- writes a markdown decision report under `reports/`

## Demo Workflow
1. Input WT and mutant structures
2. Run analysis
3. System outputs:
   - structural comparison
   - prioritization score
   - explanation
   - flags
4. Generate decision report

## UI Preview

![UI](./docs/ui.png)

## Why This Project
MHC Atlas OS focuses on explainability and decision-making, not black-box prediction. The goal is to make structural evidence easier to inspect, compare, and communicate so prioritization decisions remain transparent and reviewable.
