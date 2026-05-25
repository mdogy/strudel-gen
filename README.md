# strudel-gen

[![CI](https://github.com/mdogy/strudel-gen/actions/workflows/ci.yml/badge.svg)](https://github.com/mdogy/strudel-gen/actions/workflows/ci.yml)

Local, code-driven pipeline for generating ambient soundscape audio files (WAV) suitable for video backgrounds.

## Architecture

Three layers:

1. **Strudel** — JavaScript live-coding environment that emits OSC pattern messages.
2. **SuperDirt** — audio engine inside SuperCollider that receives the OSC and synthesizes/plays back sound.
3. **SuperCollider Recorder** — writes the final mix to disk as `.wav`.

```
Strudel pattern (JS)  ──OSC──▶  SuperDirt (SC)  ──audio──▶  Recorder → .wav
```

## Layout

```
strudel-gen/
├── README.md           — this file
├── CLAUDE.md           — instructions for Claude Code
├── AGENTS.md           — agent roles & responsibilities
├── SWED.md             — binding software engineering rules
├── PLAN.md             — roadmap to the soundscape-gen skill
├── TODO.md             — open work (mirrors PLAN milestones)
├── HISTORY.md          — changelog / session log
├── docs/               — the full production guide & reference material
├── src/
│   ├── patterns/       — Strudel `.js` soundscape patterns
│   └── supercollider/  — SC startup file + recording snippets
└── scripts/            — CLI helpers (bridge, REPL, record, render)
```

## Quick start

1. Install SuperCollider, sc3-plugins, SuperDirt, Node.js, pnpm. See [docs/guide.md](docs/guide.md) Part 1.
2. Copy [src/supercollider/startup.scd](src/supercollider/startup.scd) to your SC startup file.
3. `scripts/bridge.sh` — start the Strudel OSC bridge.
4. `scripts/repl.sh` — open the Strudel REPL at http://localhost:4321.
5. `scripts/record.sh <pattern.js> <out.wav> <seconds>` — record a take.

See [docs/guide.md](docs/guide.md) for the full workflow.
