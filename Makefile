.PHONY: setup clean test lint typecheck format doctor render render-pattern session dr-who smoke-render install-skill

# === Python ===
VENV = .venv
PYTHON = $(VENV)/bin/python3

# Make sure sclang is findable: ~/.local/bin is often not in make's PATH.
# detect.py also probes the macOS app bundle directly, so this is a belt-and-
# suspenders fallback for systems that do have a symlink there.
export PATH := $(HOME)/.local/bin:/usr/local/bin:$(PATH)
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
	find . -path "./$(VENV)" -prune -o -name "*.pyc" -delete
	find . -path "./$(VENV)" -prune -o -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true

test: $(VENV)/bin/activate
	$(PYTEST) tests/ -v --tb=short --cov --cov-fail-under=85

lint: $(VENV)/bin/activate
	$(RUFF) check src/ tests/
	pre-commit run --all-files --show-diff-on-failure 2>/dev/null || true

typecheck: $(VENV)/bin/activate
	$(MYPY) src/ tests/

format: $(VENV)/bin/activate
	$(RUFF) format src/

doctor: $(VENV)/bin/activate
	$(PYTHON) -m strudel_gen.cli doctor $(ARGS)

render: $(VENV)/bin/activate
	$(PYTHON) -m strudel_gen.cli render $(ARGS)

render-pattern: $(VENV)/bin/activate
	$(PYTHON) -m strudel_gen.cli render-pattern $(ARGS)

session: $(VENV)/bin/activate
	$(PYTHON) -m strudel_gen.cli session $(ARGS)

dr-who: $(VENV)/bin/activate
	$(PYTHON) -m strudel_gen.cli render \
	  --pattern src/supercollider/dr-who-render.scd \
	  --duration 120 \
	  --out ~/Desktop/dr-who-soundscape.wav

# Generic Tidal-engine pipeline smoke test — renders sample.tidal for 30 s.
# Use this to verify ghci + SuperDirt + recorder are all working.
smoke-render: $(VENV)/bin/activate
	$(PYTHON) -m strudel_gen.cli render \
	  --engine tidal \
	  --pattern src/tidal/sample.tidal \
	  --duration 30 \
	  --out /tmp/smoke-render.wav
	@echo "smoke-render complete → /tmp/smoke-render.wav"

# === Skill ===
SKILL_DIR = $(HOME)/.claude/skills/ambient-render

install-skill:
	mkdir -p $(SKILL_DIR)
	ln -sf $(CURDIR)/skill/SKILL.md $(SKILL_DIR)/SKILL.md
	@echo "Skill symlinked: $(SKILL_DIR)/SKILL.md -> $(CURDIR)/skill/SKILL.md"

# === Branch protection (admin needed) ===
# Run once after initial CI green to lock main. Requires `gh` auth + admin access.
protect-main:
	gh api -X PUT repos/mdogy/strudel-gen/branches/main/protection \
	  --input - <<< '{"required_status_checks":{"checks":[{"context":"Lint + typecheck"},{"context":"ShellCheck"},{"context":"Markdown lint"},{"context":"Pre-commit hooks"},{"context":"Test (ubuntu-latest)"},{"context":"Test (macos-latest)"},{"context":"Test (windows-latest)"},{"context":"Test (WSL2 / Ubuntu)"}],"strict":true},"enforce_admins":true,"required_pull_request_reviews":null,"restrictions":null}'
