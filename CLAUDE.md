# CLAUDE.md

Guidance for Claude Code working in this repo.

## What this project does

A local pipeline: **Strudel (JS patterns) → SuperDirt (SC audio engine) → Recorder (.wav)**. The deliverable is a rendered ambient soundscape WAV for video backgrounds.

The full production guide lives in [docs/guide.md](docs/guide.md). Read it before editing infrastructure (startup file, bridge config, recording settings).

## Your job

Your primary task is **writing Strudel pattern code** in `src/patterns/*.js`. Everything else (SC startup, OSC bridge, recorder) is set-and-forget infrastructure.

When asked for a new soundscape:

1. Ask for, or infer from context: mood, duration, tempo (cpm), key/scale, what to include/avoid.
2. Write a single `.js` file in `src/patterns/` using `setcpm()` + `stack()`.
3. Every layer should use `.slow(>=4)` and `.room(>=0.7)`.
4. Use `.orbit(0|1|2)` to keep layers on separate buses (so multi-stem recording works).
5. Output only the pattern code in the file — no commentary inside the `.js`.

See [docs/guide.md](docs/guide.md) Part 5 for syntax reference and starter templates.

## Conventions

- Patterns are plain `.js` files, evaluated by pasting into the Strudel REPL.
- Filenames: `kebab-case-mood.js` (e.g. `cold-underwater.js`, `mossy-forest-dawn.js`).
- Don't edit `src/supercollider/startup.scd` casually — it controls SC boot for every session.
- Recording always happens in the **SuperCollider IDE** or via `scripts/record.sh`, never from Strudel.
- All recordings: WAV, int24, stereo (or 6ch for stems), 48 kHz preferred for video.

## What NOT to do

- Don't introduce build tooling, package.json, or frameworks. This repo holds patterns + shell scripts; Strudel itself lives in a separate clone.
- Don't add comments inside pattern files explaining what the code does — the patterns are short and the templates in the guide are the reference.
- Don't change OSC port 57120 without updating the SC startup file in lockstep.
