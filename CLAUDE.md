# CLAUDE.md

Guidance for Claude Code working in this repo.

## What this project does

A local pipeline: **Strudel (JS patterns) → Tidal Cycles → SuperDirt (SC audio engine) → WAV/MP3**.
The deliverable is a rendered ambient soundscape audio file for video backgrounds.

The full architecture is in [docs/redesign-tidal.md](docs/redesign-tidal.md). The legacy
sc-native fast path is documented in [docs/guide.md](docs/guide.md).

## Your job

Your primary task is **writing Strudel pattern code** in `src/patterns/*.js`. The pattern
will be transpiled to Tidal `.tidal` and rendered headlessly via `ghci`. You can also
write `.tidal` directly for the Tidal engine.

When asked for a new soundscape:

1. Ask for, or infer from context: mood, duration, tempo (cpm), key/scale, what to include/avoid.
2. Write a single `.js` file in `src/patterns/` using `setcpm()` + `stack()`.
3. Every layer should use `.slow(>=4)` and `.room(>=0.7)`.
4. Use `.orbit(0|1|2)` to keep layers on separate buses.
5. Use only the Strudel functions listed in [docs/redesign-tidal.md §4.1](docs/redesign-tidal.md#41-the-complete-mapping-table).
6. Output only the pattern code in the file — no commentary inside the `.js`.

See [docs/redesign-tidal.md §6](docs/redesign-tidal.md#6-llm-author-cheat-sheet) for mood-family templates.

## Conventions

- Patterns are `.js` files that get transpiled to `.tidal` and rendered headlessly.
- Filenames: `kebab-case-mood.js` (e.g. `cold-underwater.js`, `mossy-forest-dawn.js`).
- Don't edit `src/supercollider/startup.scd` casually — it controls SC boot for every session.
- Use `strudel-gen render --engine tidal --pattern <file> --duration <s> --out <path>` to render.
- All recordings: WAV, int24, stereo (or 6ch for stems), 48 kHz preferred for video.

## Repo size discipline

This repo must stay lean — no large or generated files committed:

- **Build artifacts, virtual environments, audio output, and logs** go in `.gitignore`-covered directories (`_build/`, `_output/`, `.venv/`, `out/`, etc.).
- **Use the Makefile** for all build/clean operations: `make setup`, `make test`, `make clean`.
- **Python deps**: managed via `pyproject.toml` + `requirements.txt`; `.venv/` is ignored.
- **Node deps**: `.nvmrc` pins the Node version; `node_modules/` is ignored.

## What NOT to do

- Don't introduce build tooling, package.json, or frameworks beyond what `Makefile` handles.
  This repo holds patterns + Python orchestration; Strudel itself lives in a separate clone.
- Don't add comments inside pattern files explaining what the code does — the patterns are short and the templates in the guide are the reference.
- Don't change OSC port 57120 without updating the SC startup file in lockstep.
- Don't commit generated files, audio output, virtual environments, or build artifacts.
