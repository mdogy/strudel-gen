# Software Engineering Guidelines (SWED)

These are **non-negotiable** rules for this project. Any agent or human contributor must follow them. Deviations require an entry in [HISTORY.md](HISTORY.md) with justification.

---

## 1. Version control

- **Git, always.** Every change lives in a commit. No "scratch" edits.
- **Frequent, small commits.** One logical change per commit. Aim for commits that could be reverted independently. If a session produces more than ~50 lines of new code with zero commits, that's a smell.
- **Conventional Commits** style messages: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`, `ci:`. Subject ≤72 chars, body explains *why*.
- **Public GitHub repo**, created and managed via the `gh` CLI:
  ```bash
  gh repo create strudel-gen --public --source=. --remote=origin --push
  ```
- **Branching**: `main` is always green. Feature work on short-lived branches; PRs merged via `gh pr create` → `gh pr merge --squash`.
- **No force pushes to `main`.** Ever.
- **`.gitignore` covers**: `out/`, `*.wav`, `node_modules/`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `dist/`, `.DS_Store`, local secrets/env overrides.

## 2. Language & typing

- **Primary orchestration language: Python ≥3.11** (chosen — see [PLAN.md](PLAN.md) §3). Strudel pattern files remain `.js` (Strudel runtime); SC startup remains `.scd`.
- **Python**:
  - **Type hints everywhere.** Public functions fully annotated.
  - **`mypy --strict`** must pass. No `# type: ignore` without an inline reason.
  - **Pydantic** for all external data shapes (CLI args parsed into models, config files, OSC payloads, skill inputs). No raw dicts crossing module boundaries.
- **If TypeScript/JS is later added** (e.g. a Strudel pattern generator running in Node):
  - **TypeScript, not plain JS.** `strict: true` in `tsconfig.json`.
  - **Zod** for runtime validation at boundaries (the TS equivalent of Pydantic).
  - Plain `.js` is reserved for **Strudel pattern files only** — they are evaluated by Strudel, not by us.

## 3. Linting & formatting

- **Python**: `ruff check` + `ruff format` (replaces flake8/black/isort). Config in `pyproject.toml`. CI fails on any lint error.
- **TypeScript** (if introduced): `eslint` + `prettier`, or `biome` (preferred — single tool).
- **Shell scripts**: `shellcheck` clean.
- **Markdown**: `markdownlint` clean for docs in `docs/`.
- **Pre-commit hook** runs lint+format+type-check before every commit. Install via `pre-commit install`. Hook is mandatory; bypassing with `--no-verify` requires a HISTORY.md note.

## 4. Testing

- **TDD by default.** Red → green → refactor. Write the failing test first; commit it; then write the code that makes it pass.
- **BDD for user-facing behavior.** Use **`pytest-bdd`** (Python) or **Cucumber.js** (TS) with `.feature` files in `tests/features/`. Each skill capability has a feature file written in Gherkin (`Given/When/Then`) before implementation.
- **Three test layers**, all required:
  1. **Unit tests** — pure, fast, isolated. Mock `subprocess`, filesystem, network, time. Use `pytest` + `pytest-mock` (or `unittest.mock`).
  2. **Integration tests** — exercise real subprocesses where safe (e.g. invoking `sclang -h`), real temp files. Skipped automatically if external binaries are missing, with a clear skip reason.
  3. **Acceptance tests** — end-to-end via the BDD features. May be marked `@slow` and gated behind a CI label, but must run in nightly CI.
- **Coverage**: ≥85% line coverage on the orchestration package. `pytest --cov` enforced in CI.
- **No test is allowed to depend on network access** unless explicitly marked `@pytest.mark.network` and skipped by default.
- **Fixtures over setup boilerplate.** Shared fixtures in `tests/conftest.py`.

## 5. Logging

- **Structured logging to files**, never `print()` / `console.log`. Use Python's `logging` module configured via `logging.config.dictConfig` (or `structlog` if structured JSON output is needed).
- **Log levels are meaningful**:
  - `DEBUG` — verbose tracing, off by default.
  - `INFO` — lifecycle events (session start, recording start/stop, pattern evaluated).
  - `WARNING` — recoverable oddities (port in use, retrying).
  - `ERROR` — operation failed but process continues.
  - `CRITICAL` — process is going down.
- **Log everything** that crosses a boundary: every subprocess invocation (command + exit code + duration), every OSC message sent/received (at DEBUG), every file written.
- **Log location**: `~/.local/state/strudel-gen/logs/strudel-gen.log` (Linux/Mac, per XDG); `%LOCALAPPDATA%\strudel-gen\logs\` on Windows. **Rotated**: `RotatingFileHandler`, 10 MB × 5 files.
- **Console output** is for human-facing CLI feedback only (progress, prompts, errors) — it is *not* the log. Use `rich` for console.
- **No secrets in logs.** No file paths containing user PII at INFO level (paths go to DEBUG).

## 6. Cross-platform support

The project **must run identically** on:

- **macOS** (Apple Silicon and Intel)
- **Linux** (Ubuntu 22.04+ as reference)
- **Windows 10/11 native** (PowerShell)
- **Windows via WSL2 / Ubuntu** (this is a first-class target, not "Linux on Windows")

Rules:

- **No hardcoded paths.** Use `pathlib.Path`, `os.path.expanduser`, `appdirs`/`platformdirs` for state/cache/log directories.
- **No shell-specific syntax** in Python code. Cross-platform subprocess invocation: pass `list[str]` to `subprocess.run`, not shell strings. `shell=False` always.
- **Path separators**: never hardcode `/` or `\`. Use `Path` joins.
- **Line endings**: `.gitattributes` enforces `* text=auto eol=lf` plus `*.bat text eol=crlf`.
- **External tool discovery**: locate `sclang`, `pnpm`, `node` via `shutil.which`; fail with an actionable error message if missing, naming the platform-specific install path (e.g. `/Applications/SuperCollider.app/Contents/MacOS/sclang` on macOS).
- **WSL specifics**: detect with `/proc/version` containing `microsoft`. When detected, audio/OSC must route through the Windows host (document this clearly — SuperCollider does not run usefully inside WSL for audio).
- **CI matrix**: GitHub Actions runs the full suite on `ubuntu-latest`, `macos-latest`, `windows-latest`. WSL is exercised via `windows-latest` + `wsl-bash` action.

## 7. Documentation

- **Kept current.** A PR that changes behavior must update the relevant doc in the same commit. Reviewers reject doc-stale PRs.
- **What lives where**:
  - [README.md](README.md) — what this is, quick start, links.
  - [CLAUDE.md](CLAUDE.md) — instructions for Claude Code in this repo.
  - [AGENTS.md](AGENTS.md) — agent role definitions.
  - [SWED.md](SWED.md) — this file. Engineering rules.
  - [PLAN.md](PLAN.md) — current roadmap. Updated as milestones land.
  - [TODO.md](TODO.md) — open work. Closed items move to HISTORY.md.
  - [HISTORY.md](HISTORY.md) — chronological session/change log.
  - `docs/` — user-facing guides (`guide.md`, `troubleshooting.md`, `architecture.md`).
- **Docstrings**: every public function/class in Python has a docstring (one-line summary minimum; full Google-style for non-trivial APIs).
- **API docs auto-generated** via `mkdocs` + `mkdocstrings` published to GitHub Pages on every `main` push.

## 8. Minimize cruft

- **No dead code.** Delete it; git remembers.
- **No commented-out code.** Delete it; git remembers.
- **No `TODO` without an owner and an issue.** Either fix it now or `gh issue create` and reference the number.
- **No speculative abstractions.** Build the second use case before extracting the helper.
- **No backward-compat shims** until there's an actual external consumer.
- **Dependency budget**: every new dependency needs a line in PR description explaining why a stdlib option doesn't suffice.

## 9. Definition of Done

A change is "done" only when **all** of the below are true:

- [ ] Tests written first, now passing.
- [ ] `ruff check`, `ruff format --check`, `mypy --strict` pass.
- [ ] Coverage did not decrease.
- [ ] Docs updated in the same commit/PR.
- [ ] Logging added for any new boundary crossing.
- [ ] Verified on at least 2 of {macOS, Linux, Windows native, WSL}.
- [ ] HISTORY.md has a one-line entry.
- [ ] Committed and pushed to a branch; PR opened or merged.
