.PHONY: check test build

check:
	uv run ruff check src scripts
	uv run ruff format --check src scripts
	uv run python -m compileall -q src scripts
	uv build

test:
	uv run python scripts/live.py

build:
	uv build
