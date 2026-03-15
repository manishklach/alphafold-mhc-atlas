# Installation

## Python version

- Recommended: Python 3.11
- Supported minimum: Python 3.10

## Editable developer install

```bash
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[app,dev]
```

## Minimal local install

```bash
python -m venv .venv
.\.venv\Scripts\python -m pip install .
```

## App install

```bash
.\.venv\Scripts\python -m pip install .[app]
```

## Test install

```bash
.\.venv\Scripts\python -m pip install .[test]
```

## Requirements-based fallback

```bash
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pip install -r requirements-app.txt
```
