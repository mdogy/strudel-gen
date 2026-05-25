# HISTORY

Session log. Newest first. One line per meaningful change.

## 2026-05-25

- Resolved blocking decisions: MIT license, skill name `ambient-render`, pin Strudel to `8a8ae9ac9659`, allow Dirt-Samples with license doc.
- Added lean-repo section to SWED §7 (no generated artifacts committed).
- Added lean-repo discipline to CLAUDE.md and AGENTS.md.
- M0: `pyproject.toml` with ruff+mypy+pytest config; `requirements.txt`; `.nvmrc`; `.pre-commit-config.yaml`; `.github/workflows/ci.yml` (matrix: ubuntu/macos/windows); `Makefile` with setup/test/lint/typecheck/clean targets.
- M1: `src/strudel_gen/` package with `detect.py` (SC/node/pnpm/Strudel detection + WSL), `cli.py` (Typer app with `doctor` + `render-pattern`), `logging_setup.py` (rotating file logs via platformdirs).
- M2: `patterns/model.py` (Pydantic `PatternSpec`, `Layer`, `Effect` with SWED validators), `patterns/render.py` (Jinja2 template renderer), `patterns/templates/default.j2`.
- Tests: 22 unit tests covering detect, logging, model validation, and render output — all passing.
- Lint: `ruff check` clean, `ruff format` clean, `mypy --strict` passes.

## 2026-05-24

- Initialized repo layout: `README.md`, `CLAUDE.md`, `AGENTS.md`, `TODO.md`, `HISTORY.md`, `docs/`, `src/patterns/`, `src/supercollider/`, `scripts/`.
- Imported the master production guide as `docs/guide.md`.
- Added SC startup file (`src/supercollider/startup.scd`) per guide Part 2.1.
- Added CLI wrappers: `scripts/bridge.sh`, `scripts/repl.sh`, `scripts/record.sh`, `scripts/env.sh`.
- Wrote `SWED.md` — binding engineering rules (git/GitHub, Python+mypy+ruff, pydantic, pytest+pytest-bdd, structlog-style file logging, cross-platform incl. WSL, doc-in-PR).
- Wrote `PLAN.md` — 8-milestone roadmap (M0 hygiene → M6 cross-platform validation, M7/M8 stretch) to evolve the scaffold into a Claude Code Skill called `soundscape-gen`. Recorded architectural decisions (Python 3.11, Typer, platformdirs, reuse Strudel's OSC bridge in v1).
- Refactored `TODO.md` to mirror `PLAN.md` milestones; surfaced 4 blocking decisions (license, skill name, Strudel pin, sample-pack policy).
