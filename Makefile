.PHONY: setup clean test lint typecheck format doctor render

# === Python ===
VENV = .venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip
RUFF = $(VENV)/bin/ruff
MYPY = $(VENV)/bin/mypy
PYTEST = $(VENV)/bin/pytest

setup: $(VENV)/bin/activate

$(VENV)/bin/activate: pyproject.toml requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	touch $(VENV)/bin/activate

clean:
	rm -rf $(VENV) _build/ _output/ out/ .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf __pycache__ */__pycache__ */*/__pycache__
	rm -f .coverage
	find . -name "*.pyc" -delete
	find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true

test: $(VENV)/bin/activate
	$(PYTEST) tests/ -v --tb=short

lint: $(VENV)/bin/activate
	$(RUFF) check src/

typecheck: $(VENV)/bin/activate
	$(MYPY) src/

format: $(VENV)/bin/activate
	$(RUFF) format src/

doctor: $(VENV)/bin/activate
	$(PYTHON) -m strudel_gen.cli doctor

render: $(VENV)/bin/activate
	$(PYTHON) -m strudel_gen.cli render-pattern $(ARGS)
