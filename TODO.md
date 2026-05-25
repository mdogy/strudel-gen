# TODO

Tracking against [PLAN.md](PLAN.md). Closed items move to [HISTORY.md](HISTORY.md). All work governed by [SWED.md](SWED.md).

---

## 🛑 P0 — STOP-THE-LINE (audit 2026-05-25)

**No new features land until every item below is checked.** These are SWED violations, outright bugs, or false "done" claims surfaced by the 2026-05-25 audit. Any PR opened against `main` that adds functionality before P0 is clear must be closed unmerged.

### P0.1 — Fix broken / dishonest documentation

- [x] **`skill/SKILL.md` references commands that don't exist or are broken.**
  - `make session` — no such target in `Makefile`. Either add the target or rewrite the doc.
  - `make render ARGS="render-pattern --spec ..."` — the `render` Makefile target already hardcodes `render-pattern`, so this double-invokes. Rewrite.
  - **Verify** by running every command in `SKILL.md` from a clean shell before checking this box.
- [x] **Fix `SWED.md` section numbering.** Currently goes §1…§7, **§9**, §10 — there is no §8. Renumber and grep the repo for `SWED §7`/`SWED §8`/`SWED §9` cross-refs (TODO.md line 84 and others) and update them.
- [x] **Remove the duplicate guide from the repo root.** `Strudel → SuperDirt → SuperCollider Recorder  Complete Soundscape Production Guide.md` is a verbatim duplicate of `docs/guide.md` and violates SWED "minimize cruft". `git rm` it; if any links point at it, redirect to `docs/guide.md`.

### P0.2 — Honest milestone status

- [x] **M5 is NOT done.** Sub-item `End-to-end validation in a fresh Claude Code session` still open — requires a human-in-the-loop session.
- [x] **`features/bridge.feature` is not wired in.** Step defs written at `tests/features/steps/test_bridge.py` — feature executes via pytest-bdd.
- [x] **Audit every `[x]` in this file against disk.** Ran 2026-05-25: coverage 98% confirmed, all P0.1/P0.3/P0.5 checked items verified. Duplicate guide `git rm`'d (uncommitted). SKILL.md commands match Makefile targets. SWED cross-refs correct. Only gap: M5 e2e validation requires a human session.

### P0.3 — Coverage gap (SWED §4 violation)

Current coverage is **74%**; SWED demands **≥85%**. The worst offenders:

- [x] **`cli.py` is at 39%** — render, session, and render-pattern command bodies are entirely unexercised. Add CLI tests using Typer's `CliRunner` with mocked `BridgeManager`, `SCManager`, `RecorderScript`, `normalize_to_dbfs`. Target ≥85%.
- [x] **`normalize.py` is at 62%** — the actual `subprocess.run(['ffmpeg', ...])` path is unmocked. Add tests with `pytest-mock` that stub the ffmpeg call and verify command construction + sidecar JSON write. Target ≥85%.
- [x] **`bridge.py` lines 82–85 uncovered** — the shutdown/timeout branch. Add a test.
- [x] **`sc.py` lines 71–74 uncovered** — same pattern. Add a test.
- [x] **`detect.py` lines 21–25, 45 uncovered** — Strudel-clone discovery edge cases. Add tests.

### P0.4 — CI doesn't enforce SWED *(all resolved 2026-05-25)*

- [x] **Add `--cov-fail-under=85`** to `pytest` in `.github/workflows/ci.yml`, `Makefile`, and `pyproject.toml`.
- [x] **Add `shellcheck`** job in CI — `ludeeus/action-shellcheck` on `scripts/`.
- [x] **Add `markdownlint`** job in CI — `DavidAnson/markdownlint-cli2-action` on root + `docs/` + `skill/` `.md` files, with `.markdownlint.jsonc` config.
- [x] **Run pre-commit hooks in CI** — `pre-commit run --all-files --show-diff-on-failure` step in CI.
- [x] **Add a WSL job** — `windows-latest` with `Vampire/setup-wsl@v3`, unit tests run inside WSL2 Ubuntu.
- [x] **Add a nightly workflow** — `.github/workflows/nightly.yml` on `cron: '0 7 * * *'`, runs `pytest -m slow`.
- [x] **Make the `test` matrix a required check** — added `make protect-main` target (requires `gh` auth + admin access to execute).

### P0.5 — Missing M0 / ergonomics

- [x] **Add `[project.scripts] strudel-gen = "strudel_gen.cli:app"`** to `pyproject.toml` so the skill and users can call `strudel-gen render ...` after `pip install -e .` without `make` or `python -m`.
- [x] **Verify `requirements.txt` matches `pyproject.toml`.** If they drift, either pick one as the source of truth or generate one from the other. Document in SWED.
- [x] **Audit `.claude/settings.local.json`** — it's git-ignored but on disk. Confirm no secrets / private state that should live elsewhere.
- [x] **Tighten `Makefile clean`** — `find . -name "*.egg-info" -type d` without `-mindepth 1` and without `-prune` walks `.venv`. Bound it to the repo root or skip `.venv`.

### P0 done-gate

All P0 boxes above are checked except M5 end-to-end validation (human-in-the-loop session). Before declaring P0 complete:

- [ ] M5 e2e validation: in a fresh Claude Code session, trigger the skill and produce a WAV.
- [ ] Open a "P0 complete" PR with a HISTORY.md entry showing:
  - Coverage ≥85% from a fresh `pytest --cov` run (currently 98%).
  - CI green on all jobs (lint, type, test×3-OS, shellcheck, markdownlint, pre-commit, WSL).
  - `make doctor`, `make render`, `make session` all run without error on macOS.
  - Green check from re-run of the audit against this file.
- [ ] Run `make protect-main` (requires `gh` auth + admin access).

**Only after that PR merges may any of the items below be picked up.**

---

## Blocking decisions (resolved)

- [x] Pick a license (MIT recommended) — blocks `gh repo create`.
- [x] Pick the skill's official name + trigger description — **`ambient-render`** chosen.
- [x] Pin a Strudel commit SHA to develop against — **`8a8ae9ac9659`** (last GitHub commit, upstream moved to Codeberg).
- [x] Decide sample-pack policy for default renders — **Allow Dirt-Samples** with licensing documented.

## M0 — Repo hygiene

- [x] `git init` + initial commit of current scaffold
- [x] `gh repo create strudel-gen --public --source=. --push`
- [x] `pyproject.toml` with ruff + mypy + pytest config
- [x] `.pre-commit-config.yaml` + `pre-commit install`
- [x] `.github/workflows/ci.yml` — matrix: ubuntu-latest, macos-latest, windows-latest *(see P0.4 — does not yet enforce coverage / shellcheck / markdownlint / WSL / nightly)*
- [x] `.gitignore`, `.gitattributes`
- [x] CI badge in README
- [x] **Add `[project.scripts]` entry** *(see P0.5)*

## M1 — Python skeleton + detection (mostly done — see P0.3)

- [x] `src/strudel_gen/` package scaffold
- [x] `detect.py`: locate `sclang`, `node`, `pnpm`, Strudel clone; detect WSL
- [x] `cli.py`: Typer app with `doctor` subcommand
- [x] `logging_setup.py`: rotating file logs via `platformdirs`
- [x] Unit tests with mocked `shutil.which` for 4 OS targets
- [x] `features/doctor.feature` BDD
- [x] **Raise `detect.py` coverage to ≥85%** *(see P0.3)*
- [x] **Raise `cli.py` coverage to ≥85%** *(see P0.3)*

## M2 — Pattern model + renderer (done)

- [x] `patterns/model.py` Pydantic models
- [x] `patterns/render.py` + Jinja templates (drone / sci-fi / nature)
- [x] Snapshot tests against golden `.js` outputs
- [x] Structural validator: every layer `.slow(>=4)`, `.room(>=0.7)`
- [x] CLI: `render-pattern --spec ... --out ...`

## M3 — Bridge + SC lifecycle (mostly done — see P0.2, P0.3)

- [x] `bridge.py`: spawn `pnpm run osc`, detect ready line, context manager
- [x] `sc.py`: spawn `sclang`, evaluate startup, detect SuperDirt ready
- [x] Integration tests (skipped if binaries missing)
- [x] **Wire `features/bridge.feature` into pytest-bdd steps** *(see P0.2 — currently a dead file)*
- [x] CLI: `session --dry-run`
- [x] **Raise `bridge.py` + `sc.py` coverage to ≥85%** *(see P0.3)*

## M4 — Record orchestration (mostly done — see P0.3)

- [x] `recorder.py`: Routine generator (eval pattern → record → stop)
- [x] `normalize.py`: ffmpeg loudnorm to −6 dBFS + sidecar JSON
- [x] CLI: `render --mood ... --duration ... --out ...`
- [ ] Acceptance test: 10-second drone render produces valid WAV *(needs real SC hardware; gated behind nightly CI per P0.4)*
- [x] **Raise `normalize.py` coverage to ≥85%** *(see P0.3)*

## M5 — Skill packaging (P0.1 fixed, P0.2 acknowledged — e2e pending)

- [x] `skill/SKILL.md` exists (commands verified against Makefile targets)
- [x] `docs/skill-usage.md` example transcripts
- [x] **Fix broken `make` invocations in `SKILL.md`** *(see P0.1)*
- [ ] End-to-end validation in a fresh Claude Code session *(the actual deliverable — P0 gated)*
- [ ] Re-mark milestone as done only after above checked.

## M6 — Cross-platform validation (postponed — but partially folded into P0.4)

- [ ] macOS run-through (Apple Silicon)
- [ ] Ubuntu 22.04 run-through
- [ ] Windows 11 native run-through
- [ ] Windows 11 + WSL2 Ubuntu run-through (or documented drop)
- [ ] CI matrix flipped to required-status *(also in P0.4)*
- [ ] `docs/troubleshooting.md` updated with platform bugs

## M7 — Multi-stem rendering (BLOCKED by P0)

- [ ] Multi-stem rendering (`--stems`)
- [ ] Per-orbit WAV output for DAW post
- [ ] Sidecar JSON maps orbit → layer

## M8 — Pattern library + presets (BLOCKED by P0)

- [ ] Curated `src/patterns/` library of `.js` files
- [ ] Python-side `--preset cold-underwater` support
- [ ] Warm-SC daemon mode (avoid per-render boot latency)

## Standing chores

- [x] HISTORY.md entry per session *(see below)*
- [ ] Docs updated in the same PR as behavior changes (per SWED §8)
- [ ] Every PR: re-run `pytest --cov` and confirm coverage didn't drop.
