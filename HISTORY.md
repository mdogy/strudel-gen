# HISTORY

Session log. Newest first.

---

## 2026-05-26 — R1–R8 all closed; skill can fire end-to-end

### R1 — TidalManager process cleanup
- Added `psutil` dependency; `TidalManager.stop()` now walks the child process tree via `_kill_process_tree()` before force-killing the parent. This prevents orphan `ghc` grandchildren from running at 100% CPU.
- 7 new unit tests covering graceful quit, child-tree kill, force-kill, double-stop safety, `NoSuchProcess` handling.

### R2 — `strudel-gen render --engine tidal`
- Created `render_orchestrator.py` with `render_tidal()` using the filesystem-flag synchronization pattern.
- Moved `scripts/render_tidal.py` to a thin wrapper.
- Added `--engine {tidal,sc-native,auto}` to the `render` CLI command; extension auto-detection (`.tidal` → tidal, `.scd` → sc-native, `.js` → strudel-bridge).
- 6 new CLI tests covering tidal pattern render, failure propagation, and engine inference.

### R3 — Skill registration
- Rewrote `skill/SKILL.md` with Phase-2 pipeline description, ISO trigger phrases, and Strudel `.js` authoring → tidal render workflow.
- Added `make install-skill` target to `Makefile` that symlinks `skill/SKILL.md` → `~/.claude/skills/ambient-render/SKILL.md`.

### R4 — Validator pre-flight synth check
- Added all 28 SuperDirt synth names to `_KNOWN_SYNTHS` frozenset in validator.
- `s("supersine")` etc. now rejected at transpile time with "closest match" hint via `difflib.get_close_matches`.
- 6 new validator tests.

### R5 — Transpiler scope expansion (Grimes torture test passes)
- Added lexer tokens: `=`, `[`, `]`, `;`, backtick strings, `{`, `}`, `:`, `+`, `*`, `/`, leading-dot floats.
- Rewrote parser: `let` declarations, `stack()`/`cat()`/`arrange()` expressions, variable references with chain calls, arithmetic expressions, all new methods.
- Validator whitelist expanded from ~15 to ~30 methods.
- Emitter handles symbol table resolution, `delay("l:t:fb")` expansion, `slowcat` for `arrange()`.
- `src/patterns/grimes-music4machines.js` now transpiles to valid Tidal.
- 61 new tests (18 parser, 12 lexer, 14 validator, 9 golden fixtures, 8 integration).

### R6 — DIAG_SYNTH capture
- Added `_sc_stdout_drainer()` daemon thread in `render_orchestrator.py` that drains sclang's stdout after SuperDirt ready is detected.
- Prevents pipe-buffer deadlock and captures DIAG lines that fire after "SuperDirt: listening".

### R7 — normalize.py loudnorm parse fix
- Added fallback `key: value` line parser for ffmpeg output formats where JSON block is absent.
- 3 new parse tests covering summary format and empty/noise input.

### R8 — Sample-name mapping bridge
- Added `resolve_synth()` in validator: maps GM synth names (`gm_synth_bass_1`, `gm_pad_poly`, `gm_pad_metallic`) to closest SuperDirt equivalents.
- Emitter resolves synth names at emit time.
- 3 new tests for synth resolution.

### Summary
- **195 tests** passing (was 107 before session), **87% coverage** (was 81%).
- All R1–R8 items from TODO.md closed.
- Skill now theoretically fireable: `make install-skill` + `strudel-gen render --engine tidal --pattern <file>.tidal --duration N --out <file>.wav` is the canonical pipeline.
- Next: T7 (MP3 sidecar), T8 (doctor extensions), T9 (doc pass), T10 (E2E acceptance).

---

## 2026-05-25 — Phase-2 pivot, Tidal pipeline shipped end-to-end

A long day. Five separate working sessions condensed into one entry for sanity.
Order is chronological. The session ends in a **clean, audible state** — see
[TODO.md "RESUME HERE"](TODO.md) for what to do next.

### A. Pivot decision — Strudel→Tidal→SuperDirt

- Discovered the Phase 1 "Strudel browser REPL → SuperDirt" path is not
  automatable; the Strudel REPL needs a human to paste code and press
  Ctrl-Enter. No headless mode.
- Decided new architecture:
  `skill+prompt → Strudel .js → Python transpiler → Tidal .tidal → ghci+BootTidal.hs → OSC :57120 → SuperDirt → WAV/MP3`.
- Tidal Cycles is Strudel's parent project — same mini-notation, same OSC,
  same orbits, but runs in `ghci` which IS scriptable over stdin.
- Wrote the binding plan: [docs/redesign-tidal.md](docs/redesign-tidal.md).
  Rewrote it as an implementer's recipe with skeletons + verification
  commands per milestone after first pass was judged too abstract.
- Re-marked Phase 1's M5/M6/M7/M8 as SUPERSEDED in TODO.md.

### B. Phase 2 implementation — T1 through T6 baseline

- **T1 architectural lock-in** — docs + TODO + PLAN cross-linked. Done.
- **T2 Strudel→Tidal transpiler** (T2.1 lexer, T2.2 parser, T2.3 validator,
  T2.4 emitter) — 27 unit tests + 12 golden fixtures, all mypy --strict
  clean. Spec frozen at the §4.1 whitelist (~15 methods). **Caveat
  surfaced later in section F**: the whitelist is far too narrow for
  real-world Strudel patterns.
- **T3 BootTidal.hs + sample patterns** — vendored Tidal 1.9.5 boot file
  (GHC 9.6.6 via Stack lts-22.28). Fixed `LineBuffering` import syntax,
  added `hSetBuffering stdout LineBuffering`, reduced `cVerbose` to False.
- **T4 TidalManager Python class** — `src/strudel_gen/tidal_manager.py`.
  Uses `stack ghci --no-load` + `:script BootTidal.hs` (the obvious
  `stack ghci BootTidal.hs` invocation crashes because Stack tries to
  compile the `.hs` as a Haskell module and chokes on `:set`). Reader
  thread uses `select` + `os.read` for byte-level prompt detection.
  Flushes the `tidal>` prompt with a `1+1\n` no-op (GHCi block-buffers
  stdout when piped).
- **T5 SuperDirt-headless SC startup** — `src/supercollider/headless.scd`
  written for direct sclang invocation; *however the production path
  ended up using the system `~/Library/Application Support/SuperCollider/
  startup.scd` instead* (see section D). The `argv.size > 0` guard in
  that file means render-mode (sclang+script) loads SuperDirt fully.
- **T6 render orchestrator (script form)** — `scripts/render_tidal.py`.
  Wires SCManager + TidalManager + recorder + normalize. Not yet a
  `strudel-gen render --engine tidal` subcommand; that's open work.

### C. Silent-WAV blocker (T6.5) and root cause

- First end-to-end run produced a 10 s WAV at −91 dBFS — digital silence,
  not "quiet but real". Initial suspicion: OSC routing between Tidal and
  SuperDirt. Initial fix: bumped recording delay from 2 s to 45 s "to
  overlap with Tidal startup (~30 s)".
- That didn't help. Real diagnosis (timing-of-the-bug table in
  [redesign §5.5.1](docs/redesign-tidal.md#551-the-wrong-pattern-do-not-use)):

  | t (s) | event |
  | --- | --- |
  | 0 | sclang launched |
  | 10 | scsynth booted, `s.waitForBoot` callbacks fire |
  | 10 | `fork { 45.wait; ... }` starts counting |
  | 10–130 | SuperDirt `loadSoundFiles` runs (218 banks, ~450 MB RAM) |
  | **55** | **`s.record` begins** — bus 0–1 still silent |
  | **85** | **30 s recording window ends** — WAV final, silent |
  | 117 | fork's tail wait ends, sclang `0.exit` |
  | 130 | SuperDirt prints "listening" — sclang already gone |
  | 130 | Python sees "listening", starts ghci |
  | 160 | ghci ready, pattern sent — nothing left to hear it |

- **Fix** (binding contract): replace the pre-set timer with a
  filesystem-flag trigger. sclang's `fork` polls
  `File.exists(flagPath)` every 250 ms (10-min safety cap). Python sends
  the Tidal pattern, sleeps 2 s for OSC settle, `Path(flag).touch()`s.
  Documented in [redesign §5.5.2](docs/redesign-tidal.md#552-the-correct-pattern-binding)
  with a mechanism-comparison table (stdin/timer/OSC/flag/TCP) and a
  verification recipe (`mean_volume > −60 dB`).
- Side fixes: extended SuperDirt-ready wait 120 → 180 s; TidalManager
  start timeout 60 → 90 s; added `ffmpeg volumedetect` sanity check
  that prints a visible warning when `mean_volume < −70 dB`.
- T6.5 closed at audible kick-drum WAV from `src/tidal/sample.tidal`.

### D. Musical pipeline — first real soundscape

- First multi-layer render: 3-layer Dr. Who pattern in
  `src/tidal/dr-who-inspired.tidal` v1 (supersaw bass, superpiano lead,
  superpiano pad). Produced 16 MB / 60 s audible WAV at `mean_volume
  −33 dB`. User feedback: "buzzing, broken washing machine".
- Iterated through v2/v3/v4 with the user listening at each stage. Key
  evolutions:
  - v2: introduced motif-with-variations melody structure
  - v3: added rhythmic drums (kick + ping), removed harsh hi-hat
  - v4 (latest, working): 4 layers — supersaw bass, supersaw atmospheric
    strings, **superhammond theremin**, supermandolin koto.
    Final mean −26 dB, max −14.6 dB. Trimmed middle 20 s → `~/Desktop/dr-who-mid20.wav`.

### E. Synth registry — supersine is a mirage

- v3 used `s "supersine"` for theremin; rendered to digital silence on
  that layer. After binary-search isolation (theremin-only pattern with
  `supersaw` works → `supersine` does NOT), wrote a one-shot diagnostic
  script that polls `SynthDescLib.global.synthDescs` until SuperDirt
  finishes loading and dumps everything starting with `super`.
- **The 28 registered super-synths** (this SuperDirt 1.7.x install):
  ```
  super808 superchip superclap supercomparator superfm superfork
  supergong supergrind superhammond superhat superhex superhoover
  superkick supermandolin supernoise superpiano superprimes superpwm
  superreese supersaw supersiren supersnare supersquare superstatic
  supertron supervibe superwavemechanics superzow
  ```
- **Not registered (despite intuitive names): `supersine`, `supertri`**.
  Sending events to them produces digital silence, not a fallback.
- Also discovered: **`# vib N` silently drops events for synths that
  don't have a `vib` SynthDef input.** Even synths that do exist will
  produce silence if you decorate with `# vib`. Use `superhammond`
  (built-in Leslie tremolo) for theremin-adjacent sound — no `vib`
  parameter needed.
- Also discovered: **`numWireBufs = 1024` is required** in
  `~/Library/Application Support/SuperCollider/startup.scd` to fit the
  full SuperDirt default-synths.scd. Default 64 silently drops several
  super-synths and prints `exception in GraphDef_Recv: exceeded number
  of interconnect buffers`. Deployed.

### F. Skill registration audit — not actually wired up

- User asked "can I say in Claude 'make me 30 seconds of Dr Who
  music'?" — checked, **no**. Three gaps documented in chat:
  1. `skill/SKILL.md` still describes Phase 1's Strudel-bridge path
  2. Not installed at `~/.claude/skills/ambient-render/`
  3. `strudel-gen` CLI doesn't dispatch `--engine tidal`
- These are now the headline open work.

### G. Grimes "Music 4 Machines" torture test

- Saved at `src/patterns/grimes-music4machines.js` with a
  `.url` sidecar pointing at the Strudel REPL link (base64-encoded
  source in the URL fragment for live editing).
- Transpiler **fails at the lexer** on offset 381 (the `=` in
  `let cpm = 135/4`). Even if we fix the lexer, the pattern uses ~30
  unsupported features: `let`/variable refs, `cat()`,
  `arrange([n, section], ...)`, `.bank()`, `.mask()`, `.begin()`/`.end()`,
  `.lpenv`/`.lpa`/`.lps`/`.lpd`/`.lpr`, `.rsize()`,
  `.decay()`/`.attack()`/`.release()`, remote `samples({}, url)`, and
  uses GM samples (`gm_synth_bass_1`, `gm_pad_poly`, `gm_pad_metallic`)
  that SuperDirt does not have.
- This is the right benchmark to expand the transpiler against.

### H. Process hygiene

- A `ghc` subprocess from a failed render survived `TidalManager.stop()`
  and ran at 100 % CPU + 12.6 GB RAM for ~2 hours before being manually
  `kill -9`'d. `stack ghci` was killed but its grandchild `ghc` was not.
- Tooling fix needed: TidalManager.stop() should walk the child tree
  (psutil or `ps -o pid,ppid`) and kill the actual `ghc` PID, not just
  the wrapper.
- Also: `render_tidal.py` `break`s out of the SC-stdout-read loop the
  moment it sees "SuperDirt: listening". Our `DIAG_SYNTH` lines added
  to startup.scd execute *after* that string, so Python never sees
  them. Either re-order (DIAG before "listening") or keep draining the
  pipe in a background thread.

### Net state at end of session

- Pipeline works: Tidal pattern → audible WAV. Reproducible:
  `.venv/bin/python scripts/render_tidal.py src/tidal/dr-who-inspired.tidal 70 /tmp/x.wav`
- Audible WAVs on disk: `~/Desktop/dr-who-mid20.wav`,
  `dr-who-tidal-test.wav`, `tidal-demo.wav`.
- Working pattern committed: `src/tidal/dr-who-inspired.tidal` (4-layer v4).
- No orphan processes. No zombie WAVs.
- Nothing committed to git (~30 modified files). Up to next session to
  decide what to land vs. stash.

---

## 2026-05-24 — Phase 1 foundations (Strudel-bridge architecture)

- Initialized repo layout: `README.md`, `CLAUDE.md`, `AGENTS.md`, `TODO.md`, `HISTORY.md`, `docs/`, `src/patterns/`, `src/supercollider/`, `scripts/`.
- Imported the master production guide as `docs/guide.md`.
- Added SC startup file (`src/supercollider/startup.scd`) per guide Part 2.1.
- Added CLI wrappers: `scripts/bridge.sh`, `scripts/repl.sh`, `scripts/record.sh`, `scripts/env.sh`.
- Wrote `SWED.md` — binding engineering rules (git/GitHub, Python+mypy+ruff, pydantic, pytest+pytest-bdd, structlog-style file logging, cross-platform incl. WSL, doc-in-PR).
- Wrote `PLAN.md` — 8-milestone roadmap M0–M8 (later superseded by T-series in Phase 2).
- Resolved blocking decisions: MIT license, skill name `ambient-render`, pin Strudel to `8a8ae9ac9659`, allow Dirt-Samples with license doc.
- M0: pyproject.toml, requirements.txt, .nvmrc, .pre-commit-config.yaml, .github/workflows/ci.yml, Makefile.
- M1: `src/strudel_gen/` package with `detect.py`, `cli.py` (doctor + render-pattern), `logging_setup.py`.
- M2: `patterns/model.py`, `patterns/render.py`, Jinja templates.
- M3: `bridge.py` OSC bridge context manager, `sc.py` SuperCollider lifecycle, `session --dry-run` CLI.
- M4: `recorder.py`, `normalize.py` (ffmpeg loudnorm to −6 dBFS), `render` CLI command.
- M5: `skill/SKILL.md`, `docs/skill-usage.md` — see Phase 2 §F for the audit finding that this wasn't actually wired up.
- Tests: 74 passing, 96-98% line coverage, ruff/mypy strict clean.
- P0.1–P0.5 audit findings (broken docs, dishonest milestone status, coverage gap, CI gaps, missing ergonomics) all closed against `main`.
- P0.6 F1–F5 CI-red fixes: markdownlint 202→0, ruff pinned 0.14.10, shellcheck pinned 2.0.0, mypy --strict extended to tests/, pre-commit clean. WSL job pinned to Ubuntu-22.04.
