# HTML UI

## Purpose

The HTML UI is a thin local dashboard on top of the existing pipeline.

It is designed to:

- launch the current CLI using a selected config
- browse generated projects under `outputs/`
- inspect analysis tables
- view generated plots
- read markdown reports
- open case-study subsets

It is not a second implementation of the analysis logic.

## Design

The UI keeps all core scientific logic in the existing pipeline modules and only adds a lightweight presentation layer.

Implementation:

- backend: Flask
- frontend: server-rendered HTML templates plus CSS
- data source: existing CSV, JSON, PNG, and Markdown files under `outputs/`

This keeps the UI local, simple, and easy to maintain.

## Entry Point

Run:

```bash
python -m src.webapp
```

Optional flags:

```bash
python -m src.webapp --host 127.0.0.1 --port 5000 --debug
```

Then open:

[http://127.0.0.1:5000](http://127.0.0.1:5000)

## Current Screens

### Home

Shows:

- detected projects under `outputs/`
- quick project metrics from `analysis_snapshot.json`
- a form to run the pipeline with a config path

### Project View

Shows:

- project-level summary cards
- available analysis tables
- case studies
- plot gallery
- report preview

### Table View

Shows a CSV preview for a selected analysis table.

### Report View

Shows the generated markdown report in a simple HTML-rendered form.

### Case Study View

Shows summary information and links to filtered case-study artifacts.

## Routes

Implemented routes:

- `/`
- `/run`
- `/project/<project_name>`
- `/project/<project_name>/table/<table_name>`
- `/project/<project_name>/report`
- `/project/<project_name>/plot/<plot_name>`
- `/project/<project_name>/artifact`
- `/project/<project_name>/case-study/<case_id>`

## What The UI Does Not Yet Do

- background job tracking
- async progress streaming
- live table filtering in the browser
- authenticated multi-user usage
- in-browser config editing with validation
- notebook or slide generation from the browser

The current UI is intentionally a single-user local dashboard.

## Why This Approach

This repository already writes stable file-based outputs. That makes a thin dashboard much safer than building a heavier client application.

Benefits:

- no duplication of analysis code
- minimal new dependencies
- straightforward debugging
- good fit for local exploratory work

## Possible Next UI Steps

- add project creation and config editing forms
- show run history under `outputs/`
- add richer table browsing with sorting and search
- add direct links to publication-bundle artifacts
- add report and hypothesis drill-down views
