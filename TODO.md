# TODO

Tracking against [PLAN.md](PLAN.md). Closed items move to [HISTORY.md](HISTORY.md). All work governed by [SWED.md](SWED.md).

## Blocking decisions (resolved)

- [x] Pick a license (MIT recommended) — blocks `gh repo create`.
- [x] Pick the skill's official name + trigger description — **`ambient-render`** chosen.
- [x] Pin a Strudel commit SHA to develop against — **`8a8ae9ac9659`** (last GitHub commit, upstream moved to Codeberg).
- [x] Decide sample-pack policy for default renders — **Allow Dirt-Samples** with licensing documented.

## M0 — Repo hygiene

- [x] `git init` + initial commit of current scaffold *(was done)*
- [x] `gh repo create strudel-gen --public --source=. --push` *(was done)*
- [x] `pyproject.toml` with ruff + mypy + pytest config
- [x] `.pre-commit-config.yaml` + `pre-commit install`
- [x] `.github/workflows/ci.yml` — matrix: ubuntu-latest, macos-latest, windows-latest
- [x] `.gitignore`, `.gitattributes`
- [x] CI badge in README

## M1 — Python skeleton + detection (done)

- [x] `src/strudel_gen/` package scaffold
- [x] `detect.py`: locate `sclang`, `node`, `pnpm`, Strudel clone; detect WSL
- [x] `cli.py`: Typer app with `doctor` subcommand
- [x] `logging_setup.py`: rotating file logs via `platformdirs`
- [x] Unit tests with mocked `shutil.which` for 4 OS targets
- [x] `features/doctor.feature` BDD

## M2 — Pattern model + renderer (done)

- [x] `patterns/model.py` Pydantic models
- [x] `patterns/render.py` + Jinja templates (drone / sci-fi / nature)
- [x] Snapshot tests against golden `.js` outputs
- [x] Structural validator: every layer `.slow(>=4)`, `.room(>=0.7)`
- [x] CLI: `render-pattern --spec ... --out ...`

## M3 — Bridge + SC lifecycle (done)

- [x] `bridge.py`: spawn `pnpm run osc`, detect ready line, context manager
- [x] `sc.py`: spawn `sclang`, evaluate startup, detect SuperDirt ready
- [x] Integration tests (skipped if binaries missing)
- [ ] `features/bridge.feature` BDD *(written, needs real binaries)*
- [x] CLI: `session --dry-run`

## M4 — Record orchestration

- [ ] `recorder.py`: Routine generator (eval pattern → record → stop)
- [ ] `normalize.py`: ffmpeg loudnorm to −6 dBFS + sidecar JSON
- [ ] CLI: `render --mood ... --duration ... --out ...`
- [ ] Acceptance test: 10-second drone render produces valid WAV

## M5 — Skill packaging

- [ ] `skill/SKILL.md` with tuned description (the trigger)
- [ ] `docs/skill-usage.md` example transcripts
- [ ] End-to-end validation in a fresh Claude Code session

## M6 — Cross-platform validation

- [ ] macOS run-through (Apple Silicon)
- [ ] Ubuntu 22.04 run-through
- [ ] Windows 11 native run-through
- [ ] Windows 11 + WSL2 Ubuntu run-through (or documented drop)
- [ ] CI matrix flipped to required-status
- [ ] `docs/troubleshooting.md` updated with platform bugs

## Stretch (M7 / M8)

- [ ] Multi-stem rendering (`--stems`)
- [ ] Curated preset library (`--preset cold-underwater` etc.)
- [ ] Warm-SC daemon mode (avoid per-render boot latency)

## Standing chores

- [ ] HISTORY.md entry per session
- [ ] Docs updated in the same PR as behavior changes (per SWED §7)
