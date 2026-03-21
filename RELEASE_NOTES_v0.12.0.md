# v0.12.0 - MHC Atlas OS Monorepo and Decision Pipeline

## Summary

This release introduces `MHC Atlas OS`, a clean Python monorepo for structure-guided mutation review and decision support. It adds a modular backend and UI scaffold, transparent comparison and prioritization logic, policy-based decision controls, SQLite-backed decision persistence, markdown decision reports, and deterministic end-to-end tests.

## Highlights

- Added a monorepo layout centered on `apps`, `agents`, `biology`, `core`, `storage`, `scripts`, and `tests`
- Added Biopython structure parsing for PDB and mmCIF files
- Added WT-vs-mutant structural comparison with residue deltas, CA shift metrics, and confidence deltas
- Added a transparent prioritization engine with priority labels and concise natural-language explanations
- Added a policy engine to prevent unsupported `HIGH` decisions and attach uncertainty when confidence drops
- Added a FastAPI service with `/parse`, `/compare`, `/rank`, and `/pipeline`
- Added a Streamlit UI for interactive parsing, comparison, ranking, interpretation, and confidence review
- Added markdown decision report generation under `reports/{candidate_id}.md`
- Added SQLite decision persistence and candidate decision history tracking
- Added thin workflow agents that wrap existing logic instead of duplicating it
- Added demo structures, a seed script, and golden-path pipeline tests

## API Workflow

The main workflow is now:

1. Parse WT and mutant structure files
2. Compare structural differences
3. Rank the candidate with explicit rules
4. Apply policy checks
5. Save the decision
6. Generate a decision report

Primary endpoint:

- `POST /pipeline`

Example payload:

```json
{
  "wt_file": "data/demo_structures/wt_example.pdb",
  "mutant_file": "data/demo_structures/mutant_example_a.pdb",
  "candidate_id": "demo"
}
```

## UI Improvements

- Added a three-page Streamlit interface:
  - `Upload Structures`
  - `Compare WT vs Mutant`
  - `View Rankings`
- Added interpretation text, a one-line impact statement, and WT/mutant confidence summaries
- Added a UI preview image to the README for faster repo comprehension

## Testing

This release adds deterministic tests for:

- parser behavior
- comparison edge cases
- prioritization behavior
- golden end-to-end pipeline flow
- API contract checks
- decision reporting
- SQLite decision persistence
- thin agent wrappers

## Known Notes

- FastAPI currently emits a startup deprecation warning because the app still uses `@app.on_event("startup")`. The app works correctly; this is a cleanup item for the next pass.
- Existing legacy demo history files remain in the repo and were updated alongside this release.

## Why this matters

This release moves the repository from a legacy single-flow analysis codebase toward a clearer, more modular decision platform seed. The emphasis remains on explainability, readable outputs, deterministic tests, and decision support rather than black-box prediction.
