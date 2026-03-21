# MHC Atlas OS

MHC Atlas OS – structure-guided decision system.

This repository provides a clean Python monorepo for parsing structures, comparing WT and mutant states, ranking candidates with transparent rules, and exposing the workflow through a small API and UI.

## Setup

```bash
pip install -r requirements.txt
uvicorn apps.api.main:app --reload
```

The API will be available at:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

## Folder Structure

```text
alphafold-mhc-atlas/
  apps/
    api/
    ui/
  agents/
  biology/
  core/
  data/
  scripts/
  storage/
  tests/
```

- `apps/api` contains the FastAPI backend.
- `apps/ui` contains the Streamlit frontend.
- `agents` contains lightweight wrappers around core workflow steps.
- `biology` contains structure parsing and comparison logic.
- `core` contains shared configuration, scoring, and reporting.
- `data` contains small demo assets and supporting files.
- `storage` contains the SQLite and SQLAlchemy layer.
- `scripts` contains developer and demo entry points.
- `tests` contains unit tests.
