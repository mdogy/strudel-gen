# TODO

Tracking against [PLAN.md](PLAN.md). Closed items move to [HISTORY.md](HISTORY.md). All work governed by [SWED.md](SWED.md).

## Blocking decisions (resolve before M0 / M5)

- [ ] Pick a license (MIT recommended) — blocks `gh repo create`.
- [ ] Pick the skill's official name + trigger description — blocks M5.
- [ ] Pin a Strudel commit SHA to develop against — blocks M3.
- [ ] Decide sample-pack policy for default renders (synth-only vs bundled Dirt-Samples) — blocks M4.

## M0 — Repo hygiene

- [ ] `git init` + initial commit of current scaffold
- [ ] `gh repo create strudel-gen --public --source=. --push`
- [ ] `pyproject.toml` with ruff + mypy + pytest config
- [ ] `.pre-commit-config.yaml` + `pre-commit install`
- [ ] `.github/workflows/ci.yml` — matrix: ubuntu-latest, macos-latest, windows-latest
- [ ] `.gitignore`, `.gitattributes`
- [ ] CI badge in README

## M1 — Python skeleton + detection

- [ ] `src/strudel_gen/` package scaffold
- [ ] `detect.py`: locate `sclang`, `node`, `pnpm`, Strudel clone; detect WSL
- [ ] `cli.py`: Typer app with `doctor` subcommand
- [ ] `logging_setup.py`: rotating file logs via `platformdirs`
- [ ] Unit tests with mocked `shutil.which` for 4 OS targets
- [ ] `features/doctor.feature` BDD

## M2 — Pattern model + renderer

- [ ] `patterns/model.py` Pydantic models
- [ ] `patterns/render.py` + Jinja templates (drone / sci-fi / nature)
- [ ] Snapshot tests against golden `.js` outputs
- [ ] Structural validator: every layer `.slow(>=4)`, `.room(>=0.7)`
- [ ] CLI: `render-pattern --spec ... --out ...`

## M3 — Bridge + SC lifecycle

- [ ] `bridge.py`: spawn `pnpm run osc`, detect ready line, context manager
- [ ] `sc.py`: spawn `sclang`, evaluate startup, detect SuperDirt ready
- [ ] Integration tests (skipped if binaries missing)
- [ ] `features/bridge.feature` BDD
- [ ] CLI: `session --dry-run`

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
