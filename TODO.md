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

---

## 🛑 P0.6 — CI IS RED (audit #2, 2026-05-25)

Local quality is excellent (97.72% coverage, all linters clean). **But the latest commit `22fd265` left CI red.** The P0 done-gate explicitly requires CI green on all jobs — it is not. Fix in this order, smallest blast radius first.

### F1 — Markdownlint: 23 MD013 line-length violations

The newly-rewritten P0 block in `TODO.md` is the single biggest source (17 of 23). `SWED.md` contributes 5 more.

- [ ] Reflow long lines to ≤120 chars in `SWED.md` (lines 90, 93, 97, 107, 117) and `TODO.md` (lines 3, 9, 15, 17, 18, 22, 23, 24, 30, 31, 40, 44, 48, 49, 50, 51, 55, 82, 120).
- [ ] OR raise the limit in `.markdownlint.jsonc` with a HISTORY note justifying the deviation from SWED §3.
- [ ] Run `npx markdownlint-cli2 "**/*.md"` locally before committing to prevent recurrence.

### F2 — Pre-commit ruff drift (local green, CI red)

Pre-commit's pinned `ruff v0.4.9` flags isort I001 violations in three test files; the locally-installed `ruff` does not. CI's pre-commit hook auto-rewrites the files and exits 1.

- [ ] Apply the auto-fixes to `tests/unit/test_model.py`, `tests/unit/test_normalize.py`, `tests/unit/test_sc.py` (remove blank lines between `import pytest` and the next import).
- [ ] **Pin a single ruff version** across the repo: `pyproject.toml` dev deps, `.pre-commit-config.yaml` `rev:`, and any CI install step. Currently three different pin floors → silent drift.
- [ ] Add `pre-commit run --all-files` to the local `make lint` target so the same hook runs locally and in CI.
- [ ] Document the version-pin policy in SWED §3.

### F3 — WSL2 job: bullseye-backports apt repo is dead

`Vampire/setup-wsl@v3` defaults to Debian Bullseye (despite the job being named "Ubuntu"). One repo (`bullseye-backports`) has no Release file → `apt-get update` exits 100 → Python deps never install → unit tests never run.

- [ ] Specify `distribution: Ubuntu-22.04` in the `setup-wsl` action inputs (recommended — matches SWED §6 wording "WSL2 / Ubuntu").
- [ ] OR strip `bullseye-backports` from `/etc/apt/sources.list` before `apt update`.
- [ ] Verify with a re-run that `pytest tests/unit/` actually executes inside WSL.

### F4 — Branch protection not enforced

`make protect-main` exists but has not been executed. Nothing prevents a direct push that bypasses CI.

- [ ] Run `make protect-main` (requires admin on the GitHub repo).
- [ ] Confirm via `gh api repos/mdogy/strudel-gen/branches/main/protection` that required-status-checks includes every CI job listed in the done-gate.
- [ ] Record completion in HISTORY.md.

### F5 — `tests/` not type-checked

`mypy --strict` is scoped to `src/` only (both `Makefile`/`pyproject.toml` and the pre-commit hook). SWED §2 requires "type hints everywhere".

- [ ] Extend mypy scope to `src/ tests/` in `Makefile`, `pyproject.toml`, and `.pre-commit-config.yaml`.
- [ ] Add any annotations needed to make the test suite pass strict mode.

### Smaller / cleanup (audit #2)

- [ ] **Node 20 deprecation**: bump `actions/checkout@v4` and `actions/setup-python@v5` to current latest to silence runner warnings (cosmetic until Sept 2026).
- [ ] **`BridgeContext` singleton** in `tests/features/steps/test_bridge.py` is module-level; convert to a pytest fixture to prevent state leakage between scenarios.
- [ ] **`requirements.txt` vs `pyproject.toml` drift policy**: pick one as canonical and document. Currently both list dependencies independently — they happen to match today, they won't tomorrow.

### Recommended commit order

1. `docs: reflow SWED.md + TODO.md long lines (markdownlint MD013)` — fixes F1.
2. `chore: pin ruff to a single version + apply fixes to tests/` — fixes F2.
3. `ci: pin setup-wsl to Ubuntu-22.04` — fixes F3.
4. `feat: extend mypy --strict to tests/` — fixes F5.
5. `chore: bump GitHub Actions to current versions` — silences Node 20 warnings.
6. *(human)* `make protect-main` + HISTORY entry — fixes F4.
7. *(human)* M5 e2e validation session, see P0.7 below — fixes the original M5 gap.
8. Only then: open the "P0 complete" PR.

---

## 🛑 P0.7 — Skill is not actually runnable end-to-end yet

The Dr. Who test exposed two gaps that block any real e2e validation, regardless of what the milestone checkboxes say.

### Gap A — Host machine is missing 3 of 4 prerequisites

`make doctor` on this machine (2026-05-25) reports:

```
sclang (SuperCollider)  ✗ NOT FOUND
node                    ✓ /opt/homebrew/bin/node
pnpm                    ✗ NOT FOUND
Strudel clone           ✗ NOT FOUND
```

Until these are installed locally, no render can run. None of this is the skill's fault — they are user-machine prerequisites — but it blocks the M5 validation step.

- [ ] `brew install supercollider` (or download from supercollider.github.io).
- [ ] Install sc3-plugins per `docs/guide.md` §1.2.
- [ ] Install SuperDirt quark per `docs/guide.md` §1.3 (`Quarks.install("SuperDirt", "v1.7.2")` from the SC IDE).
- [ ] Copy `src/supercollider/startup.scd` into the SC startup file location.
- [ ] `npm install -g pnpm`.
- [ ] `git clone https://github.com/tidalcycles/strudel.git ~/devel/strudel && cd ~/devel/strudel && git checkout 8a8ae9ac9659 && pnpm install`.
- [ ] Re-run `make doctor` until all four rows show ✓.

### Gap B — The skill is not installed in Claude Code

`skill/SKILL.md` is a file in the repo. **It is not registered with the user's Claude Code installation.** Saying "produce a Dr. Who soundscape" in a Claude Code session today does not fire the `ambient-render` skill — it just gets a generic response.

- [ ] Document the install path in `docs/skill-usage.md`: copy `skill/SKILL.md` into `~/.claude/skills/ambient-render/SKILL.md` (or equivalent per current Claude Code skill conventions).
- [ ] Verify the description-triggering by running `claude` with a fresh session and asking for "background music for a video" — confirm the skill fires.
- [ ] Add a `make install-skill` target that does the copy idempotently.

### Gap C — Mood prompts don't actually shape the output

Critical honesty: the `render` command takes `--mood "..."` but the renderer **does not use it to generate a Dr. Who-flavoured pattern**. The current flow is:

```
PatternSpec (defaults) → Jinja template (default.j2) → generic ambient .js
```

The `--mood` string is logged but not fed into pattern generation. Asking for "Dr. Who theme music" today produces the same WAV as asking for "underwater ambience" — a generic drone from the default template.

To make mood prompts meaningful, exactly one of these has to land:

- [ ] **Option 1 — LLM-authored Strudel**: add an `--llm` mode where the mood prompt is sent to a Claude API call that returns Strudel `.js` matching the SWED conventions (slow≥4, room≥0.7, orbit assigned). The validator already exists.
- [ ] **Option 2 — Preset library**: ship hand-written `.js` patterns under `src/patterns/` keyed by mood family (drone, sci-fi, organic, sci-fi-theme-tune, etc.) and have `render` pick the nearest match. Add `dr-who-inspired.js` as the first concrete example.
- [ ] **Option 3 — Parametric templates**: extend the Pydantic `PatternSpec` so mood maps to oscillator choice, filter sweep params, delay/feedback amounts. Templated, no LLM.

Recommended: ship **Option 2** for M5 (it's deterministic and testable), then add Option 1 later.

### Gap D — No reference Dr. Who pattern to render

Even with Option 2 above, there's no `dr-who-inspired.js` file yet. The Dr. Who theme has very specific signature elements (sine-wave bassline that sweeps, theremin-like lead, no drums in the original Delia Derbyshire 1963 cut) that the current `example-drone.js` does not evoke.

- [ ] Write `src/patterns/dr-who-inspired.js` per [CLAUDE.md](CLAUDE.md) conventions: `setcpm()` + `stack()`, every layer `.slow(≥4)`, `.room(≥0.7)`, orbits assigned. Capture the sweeping bass + spooky lead + reverb tail aesthetic.
- [ ] Use it as the fixture for the M5 acceptance test.

### Until P0.7 is closed

The honest answer to *"can I get a Dr. Who WAV today?"* is **no**. After P0.6 + P0.7 are both closed, the answer becomes **yes, by running**:

```bash
strudel-gen render \
  --pattern src/patterns/dr-who-inspired.js \
  --duration 240 \
  --out ~/Desktop/dr-who.wav
```

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
