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

## Design Philosophy

This system separates:

1. Domain Logic
   - Structure parsing
   - Comparison
   - Scoring

2. Orchestration
   - Agent runner
   - Pipeline execution

3. Runtime (Pluggable)
   - Custom runner (default)
   - NemoClaw (planned)
   - LangGraph (optional)

This allows the system to remain runtime-agnostic and portable across different agent execution frameworks.

```text
User Input
   ↓
Runtime Layer (pluggable)
   ↓
Agent Orchestration
   ↓
Domain Logic (biology + scoring)
   ↓
Policy Engine
   ↓
Decision Output + Report + Memory
```

## Governed Runtime Mode

This project supports two execution modes:

- Local Runtime:
  direct orchestration for fast development and testing

- Nemo Runtime:
  governed execution mode with:
  - execution context
  - runtime policy gate
  - stage logging
  - warnings and traceability

This is a Nemo-style governed runtime architecture that prepares the system for future integration with NVIDIA NemoClaw / OpenShell style execution environments.

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

### End-to-End Demo Script

Run the scripted showcase:

```bash
python scripts/demo_showcase.py
```

What it demonstrates:
- single mutation analysis
- batch ranking shortlist
- decision history review
- governed runtime example

Demo talk track:

- “Here’s a wild-type and mutant structure”
- “This system explains why a mutation matters, not just scoring it”
- “Now instead of one mutation, I can evaluate 20 at once”
- “This gives me a shortlist of candidates to test experimentally”
- “And the system tracks past decisions, so we can compare over time”
- “The system is runtime-agnostic — I can run it locally or in a governed execution environment like Nemo-style systems with policy enforcement.”

## UI Preview

![UI](./docs/ui.png)

## Why This Matters

Most AlphaFold-based tools focus on structure prediction or visualization.

This system focuses on:
- decision-making
- prioritization
- explainability
- reproducibility

It is designed to assist in experimental planning, not replace it.

## Why This Project
MHC Atlas OS focuses on explainability and decision-making, not black-box prediction. The goal is to make structural evidence easier to inspect, compare, and communicate so prioritization decisions remain transparent and reviewable.
