# strudel-gen

[![CI](https://github.com/mdogy/strudel-gen/actions/workflows/ci.yml/badge.svg)](https://github.com/mdogy/strudel-gen/actions/workflows/ci.yml)

Local, prompt-driven pipeline for generating ambient background music (WAV/MP3) from a mood description.
Designed for video soundscapes — arbitrarily long, loopable, no human interaction required after the prompt.

## How it works

1. You (or the `ambient-render` Claude Code skill) describe a mood.
2. Claude writes a Strudel `.js` pattern file matching that mood.
3. The Python transpiler converts it to a Tidal `.tidal` file.
4. `ghci` + Tidal Cycles plays the pattern headlessly, streaming OSC to SuperDirt.
5. SuperDirt (inside SuperCollider) synthesizes audio and records a WAV.

```text
mood prompt
    │
    ▼
Claude writes src/patterns/<slug>.js   (Strudel JS)
    │
    ▼
strudel-gen transpile                   (Python transpiler)
    │
    ▼
src/tidal/<slug>.tidal
    │
    ▼
ghci + BootTidal.hs  ──OSC :57120──▶  SuperDirt (sclang)
                                            │
                                            ▼
                                    ~/Desktop/<slug>.wav
```

## Prerequisites

| Tool | Install |
|------|---------|
| SuperCollider ≥ 3.13 + sc3-plugins + SuperDirt | [supercollider.github.io](https://supercollider.github.io) |
| GHC + Stack or GHCup | [haskell.org/ghcup](https://www.haskell.org/ghcup/) |
| Tidal Cycles 1.9.x | `cabal install tidal` or Stack (see `src/tidal/stack.yaml`) |
| Python 3.11+ | system or pyenv |
| ffmpeg | `brew install ffmpeg` / `apt install ffmpeg` |

Run `make doctor` after setup to verify all dependencies are found.

## Quick start

```bash
git clone https://github.com/mdogy/strudel-gen
cd strudel-gen
make setup          # create .venv, install Python deps
make doctor         # check sclang / ghci / tidal / ffmpeg
make install-skill  # symlink skill into ~/.claude/skills/ambient-render/
```

Then in a Claude Code session:

> "Make me 90 seconds of slow dark forest rain ambience for a video background."

The `ambient-render` skill kicks in, writes a pattern, transpiles, and renders — no follow-up needed.

To render manually:

```bash
strudel-gen render \
  --engine tidal \
  --pattern src/patterns/my-mood.js \
  --duration 120 \
  --out ~/Desktop/my-mood.wav
```

To verify the pipeline works end-to-end:

```bash
make smoke-render   # renders src/tidal/sample.tidal → /tmp/smoke-render.wav
```

## Layout

```text
strudel-gen/
├── CLAUDE.md              — instructions for Claude Code
├── PLAN.md                — architecture + milestone roadmap
├── TODO.md                — open work queue
├── HISTORY.md             — session log
├── skill/SKILL.md         — ambient-render skill definition
├── docs/
│   ├── redesign-tidal.md  — full implementation recipe (authoritative)
│   └── quick-start.md     — setup guide
├── src/
│   ├── patterns/          — Strudel .js source patterns
│   ├── tidal/             — Tidal .tidal files + BootTidal.hs
│   └── supercollider/     — SC startup file + sc-native render scripts
├── src/strudel_gen/       — Python package (CLI, transpiler, orchestrator)
├── scripts/               — shell helpers
└── tests/                 — unit + integration tests (195 tests, 87% coverage)
```

## Development

```bash
make test       # pytest with coverage gate (≥ 85%)
make lint       # ruff + pre-commit
make typecheck  # mypy --strict
```

See [docs/redesign-tidal.md](docs/redesign-tidal.md) for the full architecture, transpiler rules, and synth registry.
