# v0.12.1 - Detailed Release Notes for MHC Atlas OS

## Summary

`v0.12.1` is a documentation and packaging follow-up release for the new `MHC Atlas OS` monorepo foundation introduced in `v0.12.0`. This patch release does not change the decision logic or API surface. Instead, it packages the current monorepo flow more cleanly with refreshed demo history snapshots and a fuller written release narrative for evaluators, collaborators, and pilot users.

## What MHC Atlas OS now provides

The current repository supports a complete local-first decision workflow for structure-guided mutation review:

1. Parse WT and mutant structures from PDB or mmCIF files
2. Compare residue presence, CA-coordinate shifts, and confidence summaries
3. Rank mutation candidates with explicit, deterministic prioritization rules
4. Apply conservative policy checks before promoting decisions
5. Generate markdown decision reports
6. Persist decisions in SQLite for review history
7. Review results through both FastAPI and Streamlit interfaces

This remains an interpretable workflow. It is not an ML training loop, not a black-box scorer, and not a claim of biological ground truth.

## Included in this release

### 1. Refreshed demo history artifacts

Bundled demo projects now carry refreshed history snapshots so the shipped examples reflect recent runs of the current workflow. This makes the demo state more coherent when a user browses historical review artifacts directly in the repository.

Updated areas:

- `demo/cross_allele_demo/project/history/`
- `demo/pilot_review_demo/project/history/`
- `demo/small_project/project/history/`

### 2. Detailed release documentation

This release adds a dedicated detailed release note for the `MHC Atlas OS` monorepo stage so that the current system is easier to understand from GitHub without needing to reconstruct the feature set from commit history alone.

### 3. No change to core scoring or policy behavior

The current decision pipeline remains the same as in `v0.12.0`:

- structure parsing is unchanged
- structural comparison logic is unchanged
- prioritization remains rule-based and deterministic
- policy checks remain conservative and post-ranking
- decision reports and persistence remain unchanged

## Current architecture

The repository is now organized around five clean layers:

- `biology/`
  - structure parsing and WT-vs-mutant comparison
- `core/`
  - prioritization, policies, and reporting
- `agents/`
  - thin wrappers around core workflows
- `apps/api/`
  - FastAPI service exposing parse, compare, rank, and pipeline endpoints
- `apps/ui/`
  - Streamlit interface for interactive use

Supporting layers:

- `storage/`
  - SQLite persistence and simple schema helpers
- `scripts/`
  - local dev and demo utilities
- `tests/`
  - deterministic unit, API, and golden-path coverage

## Main workflow

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

Pipeline stages:

1. Parse WT structure
2. Parse mutant structure
3. Compare structural changes
4. Rank candidate
5. Apply conservative policies
6. Save decision
7. Generate markdown report

## Outputs

The monorepo currently produces:

- parsed structure summaries
- residue-level change summaries
- structural shift metrics
- confidence summaries and deltas
- ranked candidate outputs with:
  - `priority_score`
  - `priority_label`
  - concise interpretation text
  - explicit flags
- markdown decision reports under `reports/{candidate_id}.md`
- SQLite decision records for history lookup

## UI and demo experience

The Streamlit UI currently provides three simple views:

- `Upload Structures`
- `Compare WT vs Mutant`
- `View Rankings`

The ranking view includes:

- interpretation text
- a short “Why this matters” statement
- WT and mutant confidence summaries
- flags and priority label

The repository README also includes a UI preview image so evaluators can understand the workflow quickly from GitHub.

## Scope and restraint

What this release does not claim:

- not a binding affinity predictor
- not an immunogenicity predictor
- not proof of mechanism
- not a replacement for experimental validation
- not a validated biological truth system

The current system is intended for conservative, structure-guided decision support and review. Downstream interpretation still requires scientific judgment and experimental follow-up.

## Known notes

- FastAPI still uses `@app.on_event("startup")`, which emits a deprecation warning but remains functional
- SQLite persistence is intentionally simple and local-first
- The current UI is intentionally lightweight and functional rather than heavily styled

## Why this release matters

`v0.12.1` makes the current `MHC Atlas OS` milestone easier to evaluate and present. It gives the repository a cleaner release narrative, refreshed example state, and a clearer packaging story without changing the underlying conservative decision workflow.
