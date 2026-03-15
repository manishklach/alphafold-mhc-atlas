# Contributing

## Local setup

```bash
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[app,dev]
```

## Common tasks

```bash
mhc-atlas check-environment
mhc-atlas validate-config examples/sample_input.yaml
python -m pytest -q
```

## Scope guidance

- keep the project local-first
- keep rankings evidence-linked and decomposable
- avoid overclaiming biological interpretation
- prefer small, tested utilities over large abstractions
