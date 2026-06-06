# Contributing

Thanks for your interest in cummand!

## Setup

```bash
git clone https://github.com/divyanshudhruv/cummand.git
cd cummand
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
make dev                    # or: pip install -e ".[dev]"
```

## Development

```bash
# Single terminal: relay server + tunnel
cummand serve --tunnel http://localhost:3000

# Or two terminals:
# Terminal 1: cummand serve
# Terminal 2: cummand tunnel http://localhost:3000
```

## Tests

```bash
make test
# or: python -m pytest tests/ -v
```

On Windows (PowerShell): `python -m pytest tests/ -v -x --tb=short`

## Before Submitting

- Run the full test suite (`make test` or `python -m pytest tests/ -v`)
- Add tests for new functionality
- Update docs if you change CLI commands or config

## Code Style

- Follow existing patterns and conventions
- No comments in code (keep it self-documenting)
- Type hints on all function signatures
