# HISTORY

Session log. Newest first. One line per meaningful change.

## 2026-05-24

- Initialized repo layout: `README.md`, `CLAUDE.md`, `AGENTS.md`, `TODO.md`, `HISTORY.md`, `docs/`, `src/patterns/`, `src/supercollider/`, `scripts/`.
- Imported the master production guide as `docs/guide.md`.
- Added SC startup file (`src/supercollider/startup.scd`) per guide Part 2.1.
- Added CLI wrappers: `scripts/bridge.sh`, `scripts/repl.sh`, `scripts/record.sh`, `scripts/env.sh`.
- Wrote `SWED.md` — binding engineering rules (git/GitHub, Python+mypy+ruff, pydantic, pytest+pytest-bdd, structlog-style file logging, cross-platform incl. WSL, doc-in-PR).
- Wrote `PLAN.md` — 8-milestone roadmap (M0 hygiene → M6 cross-platform validation, M7/M8 stretch) to evolve the scaffold into a Claude Code Skill called `soundscape-gen`. Recorded architectural decisions (Python 3.11, Typer, platformdirs, reuse Strudel's OSC bridge in v1).
- Refactored `TODO.md` to mirror `PLAN.md` milestones; surfaced 4 blocking decisions (license, skill name, Strudel pin, sample-pack policy).
