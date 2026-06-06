.PHONY: install clean dev test

# Requires Python 3.11+ and a Unix-like environment (macOS, Linux, WSL).
# Windows (PowerShell) equivalents:
#   make install  →  pip install -e .
#   make dev      →  pip install -e ".[dev]"
#   make test     →  python -m pytest tests/ -v -x --tb=short

install:
	pip install -e .

clean:
	rm -rf *.egg-info src/*.egg-info __pycache__ .pytest_cache

dev:
	pip install -e ".[dev]"

test:
	python -m pytest tests/ -v -x --tb=short
