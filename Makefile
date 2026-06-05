.PHONY: install clean dev

install:
	pip install -e .

clean:
	rm -rf public tests
	rm -rf *.egg-info __pycache__ .pytest_cache

dev:
	pip install -e ".[dev]"
