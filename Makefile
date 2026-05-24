.PHONY: install run lint format test clean

install:
	uv sync --all-groups
	uv run python -m spacy download en_core_web_lg

run:
	PYTHONPATH=src uv run python src/app.py

lint:
	PYTHONPATH=src uv run ruff check src/ tests/

format:
	PYTHONPATH=src uv run ruff format src/ tests/

test:
	PYTHONPATH=src uv run pytest -v

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null; \
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null; \
	true
