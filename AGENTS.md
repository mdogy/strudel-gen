# AGENTS.md

Roles for any AI agent (Claude Code, Codex, etc.) collaborating on this project.

## Agent: Pattern Composer

**Goal:** produce a Strudel `.js` pattern that matches a given video mood.

**Inputs:**

- `VIDEO MOOD` — e.g. "mysterious, slowly evolving, sci-fi underwater"
- `VIDEO LENGTH` — e.g. "4 minutes"
- `TEMPO (cpm)` — e.g. "15–20"
- `KEY/SCALE` — e.g. "C minor" or "your discretion"
- `AVOID` — e.g. "drums, regular rhythm"
- `INCLUDE` — e.g. "≥3 layered elements, heavy reverb, slow filter movement"

**Rules:**

- Use `setcpm()` to set tempo.
- Use `stack()` to layer.
- Every layer: `.slow(>=4)` and `.room(>=0.7)`.
- Assign orbits: `0` main pad, `1` drone, `2` texture.
- Output: only the Strudel code block. No prose.

**Output location:** `src/patterns/<mood-slug>.js`

## Agent: Infrastructure Maintainer

**Goal:** keep SC startup, OSC bridge, and recording scripts working.

**Scope:**

- `src/supercollider/startup.scd` — SuperDirt boot config.
- `scripts/bridge.sh`, `scripts/repl.sh`, `scripts/record.sh` — CLI wrappers.
- Troubleshooting referenced in [docs/guide.md](docs/guide.md) Part 7.

**Guardrails:**

- Don't change OSC port without updating both the bridge and the SC startup file.
- Don't reduce `s.options.memSize` / `numBuffers` / `maxNodes` below the values in the guide — generative patterns can exhaust default limits.
- Preserve 12-orbit allocation (`~dirt.start(57120, 0 ! 12)`).

## Agent: Recordist

**Goal:** run a session end-to-end and produce a final WAV.

**Checklist** (mirrors guide Part 6):

1. SC running, post window shows `SuperDirt: listening on port 57120`.
2. `scripts/bridge.sh` running.
3. `scripts/repl.sh` running; browser at <http://localhost:4321>, output set to SuperDirt.
4. Test with `s("bd")` — sound from SC.
5. Paste pattern, iterate.
6. In SC: `s.recHeaderFormat="WAV"; s.recSampleFormat="int24";`
7. `s.record(path: "...", duration: <video_len + 10>);`
8. Wait for `Recording stopped.`
9. Normalize to -6 dBFS before delivering.

## Repo discipline

- **No generated or large files committed.** Everything buildable/installable is built from source via `Makefile`.
- **Ignored directories**: `_build/`, `_output/`, `.venv/`, `out/`, `node_modules/`, `__pycache__/`, `*.wav`, `*.log`.
- **Python venv** lives in `.venv/` (locally, not committed).
- **Node version** managed via `.nvmrc`.
- Run `make setup` after clone to install all dependencies.

## Handoff

When the Pattern Composer finishes a file, the Recordist takes over. Each agent should leave a one-line entry in [HISTORY.md](HISTORY.md).
