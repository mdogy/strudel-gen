# PLAN.md

> **READ FIRST if you're picking this up cold:**
>
> - **[TODO.md "RESUME HERE"](TODO.md#-resume-here-next-session)** — what to do today, R1–R8 in priority order.
> - **[§12 "State of the world"](docs/redesign-tidal.md#12-state-of-the-world-verified-2026-05-25)** — what works now, what doesn't, smoke-test command.
> - **[§13 Synth registry](docs/redesign-tidal.md#13-superdirt-synth-registry-verified-2026-05-25)** — 28 synths; avoid `supersine`/`supertri`.
>
> This file (PLAN.md) is the strategic / architectural plan: goal, non-goals,
> the 5-stage pipeline, the phase history, the path to a v1 ship.
> [docs/redesign-tidal.md](docs/redesign-tidal.md) is the implementation recipe.
> [TODO.md](TODO.md) is the priority queue.
> [HISTORY.md](HISTORY.md) is what happened.

---

## 1. Goal

Deliver a Claude Code **Skill** named `ambient-render` that:

- **Triggers** when a user asks for background music, ambient audio, a
  soundscape for a video, generative drone, sci-fi / underwater / forest /
  etc. atmospheric audio bed.
- **Inputs**: mood description, duration, optional output path. All other
  parameters (cpm, key/scale, layer count) inferred by the LLM authoring step.
- **Outputs**: a 24-bit / 48 kHz WAV at the requested path, normalized to
  −6 dBFS, plus an optional MP3 sidecar and a JSON sidecar describing the
  source pattern, transpile diff, orbit→layer map, and render settings (for
  reproducibility).
- **Works locally** on macOS, Linux, and Windows-via-WSL2. Native Windows
  gets `--engine sc-native` only (no Tidal).
- **Is honest about prerequisites**: `strudel-gen doctor` detects missing
  `sclang` / `ghci` / `tidal` package / `ffmpeg` and surfaces actionable
  install hints.

## 2. Non-goals (v1)

- No cloud rendering. Everything runs on the user's machine.
- No real-time interactive editing — the skill produces a finished file,
  not a live session.
- No DAW integration, MIDI input, or video processing.
- No model-side audio generation (no Suno, no MusicGen). This skill is a
  Strudel/Tidal/SuperDirt orchestrator, not a generative-audio backend.
- No Strudel-browser-REPL automation. That path is fundamentally manual; it
  is the reason Phase 2 exists.

## 3. The five-stage pipeline (architecture)

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 1 — Prompt + Skill                                                   │
│    User:        "make me 3 min of cold underwater ambience"                 │
│    Claude Code: matches `ambient-render` skill description                  │
│    Skill body:  parses mood, duration; produces a CLI invocation            │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 2 — LLM-authored Strudel  (Claude is GENUINELY good at this)         │
│    Claude writes src/patterns/<mood-slug>.js                                │
│    Constraints: setcpm + stack, every layer .slow(≥4) and .room(≥0.7),      │
│                 .orbit(0..5), only methods on the §4.1 whitelist            │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 3 — Strudel → Tidal  (deterministic Python transpiler)               │
│    strudel-gen transpile reads .js, emits src/tidal/<mood-slug>.tidal       │
│    Validator rejects features outside the whitelist with a source-line      │
│    error pointing at the exact column                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 4 — Tidal → SuperDirt audio  (ghci subprocess → OSC → sclang)        │
│    TidalManager spawns ghci with stack, loads BootTidal.hs                  │
│    Sends .tidal pattern via stdin; Tidal streams OSC to port 57120          │
│    SuperDirt (running inside sclang) synthesizes to scsynth bus 0–1         │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 5 — Audio → WAV/MP3                                                  │
│    Filesystem-flag trigger (see redesign §5.5) starts s.record AFTER OSC    │
│    is verified flowing. 24-bit / 48 kHz / stereo WAV.                       │
│    ffmpeg loudnorm → −6 dBFS WAV. Optional MP3 320 kbps. JSON sidecar.      │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                  ~/Desktop/<mood-slug>.wav  +  .mp3  +  .json
```

### Why this stack

| Choice | Why | Alternative considered |
|---|---|---|
| Tidal Cycles in `ghci` (not Strudel in browser) | ghci is scriptable over stdin; Strudel needs a human + browser. **Same OSC, same SuperDirt, same orbits.** | Strudel headless browser (Puppeteer/Playwright) — adds JS runtime + browser deps, less robust than stdin. |
| Python orchestration | matches Claude Code skill conventions; rich subprocess + path libs; cross-platform | Bash — too fragile for the timing/process work; Node — adds runtime, no advantage. |
| Typer CLI | Pydantic-native, generates `--help`, good for both human and skill use | Click — fine but no Pydantic integration. |
| `subprocess.Popen` with explicit child-tree kill | reliable cleanup including grandchildren (ghc spawned by stack ghci) | `subprocess.run` — doesn't handle long-running processes; bare `Popen` — leaks grandchildren (see redesign §14 P13). |
| Hand-written Strudel→Tidal transpiler | deterministic, no LLM in the hot path; the languages differ by ~30 mechanical rules | Run Strudel via Node and capture OSC — adds Strudel runtime, more failure modes. |
| Filesystem-flag recording trigger | zero deps, robust against SuperDirt cold-boot variability | Pre-set timer in `.scd` (was the silent-WAV bug); OSC trigger from Python (adds OSC client dep). |
| 24-bit 48 kHz stereo WAV + optional MP3 | video-editor friendly, lossless master + compressed share | int16 / 44.1 kHz — lossier and not video-pipeline standard. |

## 4. Repo shape (current, 2026-05-25)

```text
strudel-gen/
├── README.md, CLAUDE.md, AGENTS.md, SWED.md
├── PLAN.md           ← you are here
├── TODO.md           ← priority queue, RESUME HERE block at top
├── HISTORY.md        ← session log
├── pyproject.toml, requirements.txt, .pre-commit-config.yaml
├── .github/workflows/ci.yml
├── docs/
│   ├── redesign-tidal.md ★ binding implementation recipe (1700+ lines)
│   ├── guide.md          (Phase-1 production guide, partly historical)
│   ├── quick-start.md    (needs Phase-2 update — TODO T9)
│   └── skill-usage.md
├── src/
│   ├── strudel_gen/                  Python package
│   │   ├── cli.py                    Typer entrypoint
│   │   ├── detect.py                 sclang/ghci/tidal/ffmpeg detection
│   │   ├── tidal_manager.py          ★ ghci subprocess driver
│   │   ├── transpiler/               ★ lexer / parser / validator / emitter
│   │   ├── sc.py                     sclang lifecycle, "SuperDirt ready" detection
│   │   ├── bridge.py                 (legacy: Strudel OSC bridge — deprecated)
│   │   ├── recorder.py               s.record routine generator
│   │   ├── normalize.py              ffmpeg loudnorm + to_mp3
│   │   ├── patterns/                 Pydantic models + Jinja templates (Phase-1 path)
│   │   └── logging_setup.py
│   ├── patterns/                     Strudel .js files (Stage-2 inputs)
│   │   ├── dr-who-inspired.js        dev fixture — pipeline smoke test only
│   │   ├── example-drone.js
│   │   └── grimes-music4machines.js  ★ transpiler torture-test reference
│   ├── tidal/                        Tidal .tidal files (Stage-3 outputs / hand-written)
│   │   ├── BootTidal.hs              ★ vendored Tidal 1.9.5 preamble
│   │   ├── dr-who-inspired.tidal     dev fixture — 4-layer pipeline smoke test
│   │   ├── sample.tidal              minimal smoke-test pattern
│   │   ├── theremin-only.tidal       single-layer isolation diagnostic
│   │   ├── Main.hs, package.yaml, stack.yaml*   stack project for tidal-runner
│   │   └── tidal-runner.cabal
│   └── supercollider/
│       ├── startup.scd               ★ DEPLOYED to ~/Library/Application Support/SuperCollider/
│       │                               (numWireBufs=1024, argv-guard, DIAG_SYNTH lines)
│       ├── headless.scd              SCManager-only variant
│       ├── dr-who-render.scd         sc-native fast-path render script
│       └── record.scd
├── scripts/
│   ├── render_tidal.py               ★ working Tidal-engine orchestrator (Stage 4+5)
│   ├── render-tidal.sh               older shell version (likely deprecate)
│   └── bridge.sh, repl.sh, record.sh, env.sh   (legacy Phase-1 wrappers)
├── skill/
│   └── SKILL.md                      ★ NEEDS REWRITE to Phase-2 (TODO R3)
└── tests/
    ├── conftest.py
    ├── unit/                         transpiler unit + golden tests (27 + 12)
    ├── integration/                  SC / ghci lifecycle (gated on binaries)
    └── features/                     pytest-bdd .feature files
```

★ = primary Phase-2 file. Legacy items are kept for backward-compat tests but
not part of the active code path.

## 5. Phase history

| Phase | Pipeline | Status | Notes |
|---|---|---|---|
| **Phase 1** | `Strudel .js (browser REPL) → OSC bridge → SuperDirt → WAV` | M0–M4 done; **M5 proved infeasible** | Strudel REPL needs a human in `localhost:4321` to press Ctrl+Enter; cannot be automated from a subprocess. The bridge starts but emits no OSC without REPL evaluation. |
| **Phase 1.5** | `.scd self-contained → sclang → WAV` | **Working today** (`make dr-who`) | Native SC SynthDefs, no SuperDirt sample dependency. Retained as `--engine sc-native` for samples-free moods. ~45 s wall-clock for a 30 s render. |
| **Phase 2** | `skill+prompt → Strudel .js → Tidal .tidal → ghci → SuperDirt → WAV/MP3` | **Active** — T0–T6 mostly done, T7–T10 + R1–R8 open | Audible 4-layer Dr. Who reference renders. Skill not yet installed. Transpiler scope too narrow for real-world Strudel. |

### What Phase 1 left behind that Phase 2 reuses verbatim

- `src/strudel_gen/detect.py` — sclang autodiscovery, especially the macOS
  `.app` bundle probe that finds `/Applications/SuperCollider.app/Contents/MacOS/sclang`.
- `src/strudel_gen/sc.py` `SCManager` — spawns sclang, greps stdout for
  "SuperDirt: listening on port 57120", exposes start/stop context manager.
- `src/strudel_gen/recorder.py` — generates the SC Routine that calls
  `s.record(path:, duration:)`.
- `src/strudel_gen/normalize.py` — `ffmpeg -filter:a loudnorm` to −6 dBFS
  with sidecar JSON (loudnorm parse bug open — TODO R7).
- `~/Library/Application Support/SuperCollider/sclang_conf.yaml` — overrides
  the empty `Contents/MacOS/SCClassLibrary` path that breaks the SC 3.14.1
  universal build.
- 74-test pytest suite, ruff/mypy --strict config, CI matrix.

## 6. Architectural decisions (binding — change here with a HISTORY note)

| Decision | Current choice | Rationale | Open? |
|---|---|---|---|
| Orchestration language | **Python 3.11+** | matches Claude skill conventions; subprocess + path libs | locked |
| CLI framework | **Typer** | Pydantic-native, auto-`--help` | locked |
| Audio engine | **SuperDirt** inside **sclang** | mature, OSC-driven, available for both `--engine tidal` and `--engine sc-native` | locked |
| Pattern host (headless) | **Tidal Cycles 1.9.5** inside **`stack ghci`** | scriptable over stdin; same OSC protocol as Strudel | locked |
| Pattern-author language | **Strudel .js** (transpiled), `.tidal` accepted directly | Claude has a huge Strudel training corpus on GitHub; the LLM-author step is the value-add | locked |
| Recording trigger | **Filesystem flag** (sclang's `fork` polls `File.exists(flagPath)`) | robust against SuperDirt boot-time variability; zero deps | locked |
| Output format | 24-bit / 48 kHz / stereo WAV; optional MP3 320 kbps | video-pipeline standard; lossless master + compressed share | locked |
| State / log dirs | `platformdirs` | XDG on Linux, `~/Library/Application Support` on macOS, `%LOCALAPPDATA%` on Windows | locked |
| Tidal version pin | **1.9.5** (was 1.10.1 in plan; reconcile in T9) | what's actually installed via Stack lts-22.28 | reconcile |
| GHC install path | **`ghcup` recommended; Stack also works** | currently using Stack lts-22.28 → GHC 9.6.6 | documented |
| MP3 bitrate default | **320 kbps** (T7 default) | proposed; not yet implemented | open |
| Windows support strategy | **WSL2 required for `--engine tidal`; native Windows gets `--engine sc-native` only** | GHCi install on Windows native is finicky | proposed |
| Where transpiled `.tidal` lives | **committed at `src/tidal/<slug>.tidal`** | cache + reproducibility; no fresh transpile per render | proposed |

## 7. Success criteria (binding before we call this v1)

1. **The acceptance prompt:** a fresh Claude Code session with the
   `ambient-render` skill installed responds to "make me 60 seconds of
   cold underwater ambience for a video background" by writing a Strudel
   .js, transpiling, rendering, and reporting the WAV path — **with zero
   follow-up questions**. The specific mood is arbitrary; the skill must
   work for any mood description a user provides.
2. **The smoke test** (`docs/redesign-tidal.md §12.2`) passes from a clean
   shell on macOS arm64, Linux x86_64, and WSL2 Ubuntu — three consecutive
   days of automated nightly runs.
3. **A new user** can clone the repo, run `make setup` + `make doctor` +
   `make smoke-render` and hear audio within **30 minutes** on a supported
   platform. (Most of those 30 min is GHC/Tidal install on first use;
   `make doctor` must give them clear install commands per-OS.)
4. **CI green for two consecutive weeks** on all configured platforms
   including a `tidal-smoke` nightly job.
5. **Coverage ≥ 85 %** maintained across `src/`, including the transpiler
   package.

## 8. Path to v1 — concrete milestones in priority order

Phase 2 is in progress. The work queue is in [TODO.md "RESUME HERE"](TODO.md#-resume-here-next-session)
as R1–R8. Mapped to milestones:

| ID | Milestone | What ships |
|---|---|---|
| **R1** | TidalManager process cleanup | psutil child-tree kill on `stop()`; no orphan ghc |
| **R2** | Promote `render_tidal.py` to CLI subcommand | `strudel-gen render --engine tidal --pattern X --duration N --out P` works |
| **R3** | Skill registration | `skill/SKILL.md` rewritten to Phase 2; `make install-skill` symlinks to `~/.claude/skills/ambient-render/` |
| **R4** | Validator pre-flight synth check | `s "supersine"` rejected at transpile time with "closest match" hint from the §13.1 registry |
| **R5** | Transpiler scope expansion | Grimes torture test transpiles cleanly; whitelist expands from ~15 to ~40 methods |
| **R6** | DIAG_SYNTH capture | render orchestrator no longer breaks out of SC-stdout early; pipe-drain thread |
| **R7** | normalize.py loudnorm parse fix | `mean_volume` parsing works on real ffmpeg output |
| **R8** | Sample-name bridge | `gm_*` and remote `samples({}, url)` mapped or rejected with hint |
| **T7** | MP3 + sidecar JSON | `--mp3 320` produces MP3 alongside WAV; JSON sidecar describes the render |
| **T8** | Doctor extensions | `make doctor` shows rows for ghci, tidal package, ffmpeg with install hints |
| **T9** | Documentation pass | README diagram + `docs/quick-start.md` rewrite + `docs/tidal-guide.md` new |
| **T10** | E2E acceptance | `make smoke-render` from clean shell; CI `tidal-smoke` job |

After R1–R8 and T7–T10 land, we're at v1 candidate. Then two weeks of green
nightly CI on macOS + Linux + WSL2 before tagging v1.

## 9. Risks & mitigations (current)

| Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|
| SuperDirt cold-boot is 120 s per render | High | Med | Already accepted as one-time cost; future T11 warm-server daemon mode |
| GHC/Tidal install pain on Linux/Windows | High | Med | T8 doctor surfaces install commands per-OS; WSL2-required documented |
| Transpiler too narrow → "no real Strudel pattern works" | High | High | R5 expansion to ~40 methods + the Grimes torture-test benchmark |
| Synth-name typos → silent WAV (§14 P10) | High | Med | R4 validator pre-flight; §13.1 registry baked into validator |
| Process zombies (§14 P13) | High | Med | R1 child-tree kill in TidalManager.stop() |
| sc3-plugins fails to load on default `numWireBufs=64` | High | High | Already mitigated: deployed `numWireBufs=1024` in startup.scd |
| Skill description fires too eagerly (any "music") | Medium | Low | Description includes `Do NOT use for...` list; R3 + Stage-1 smoke test |
| LLM-generated Strudel uses forbidden constructs | High | Low | Validator (§4.3) rejects with source-line error; skill body can iterate |
| Copyright on Dirt-Samples for distributed output | Low | Low | Document license; `--engine sc-native` default uses synth-only |
| Tidal API changes | Low | Med | Vendored BootTidal.hs at pinned version |
| GHCi prompt detection brittle across ghc versions | Med | High | Mitigated: `:set prompt ""` + sentinel string + reader-thread |

## 10. Out-of-band decisions still needed

These block specific R-tasks or T-milestones:

- [ ] **Tidal version pin** — `1.9.5` deployed vs `1.10.1` in plan. Reconcile in T9.
- [ ] **MP3 default bitrate** — `320` proposed; needs sign-off for T7.
- [ ] **Windows-native Tidal?** — proposal: WSL2-only for `--engine tidal`. Confirm.
- [ ] **Committed `.tidal` files?** — proposal: yes, treat as cache + reproducibility artifact. Confirm.
- [ ] **Skill rename?** — current: `ambient-render`. Phase-1 considered `soundscape-gen`. Stick with `ambient-render`.

## 11. How to extend or modify this plan

Per SWED: this plan is **binding**. Deviations need a HISTORY.md note. If
you (human or model) want to change a decision in §6 or a success criterion
in §7, the workflow is:

1. Open a section in HISTORY.md with the date and a short rationale.
2. Edit the relevant cell in §6 / §7.
3. Cascade the change into [docs/redesign-tidal.md](docs/redesign-tidal.md)
   if it affects the implementation recipe.
4. Update [TODO.md "RESUME HERE"](TODO.md) if priorities shift.

## 12. Appendix — Phase 1 milestones (historical)

The original M0–M8 milestone definitions for the (now-superseded)
Strudel-bridge architecture are preserved in
[git history](https://github.com/mdogy/strudel-gen) and chronologically
in [HISTORY.md → 2026-05-24](HISTORY.md). Outcomes:

- **M0** Repo hygiene — done; CI matrix on macOS/Ubuntu/Windows.
- **M1** Python skeleton + `doctor` — done; `detect.py` reused in Phase 2.
- **M2** Pattern model + Jinja renderer — done but Phase 2 doesn't use the
  template-renderer path (Claude authors directly).
- **M3** OSC bridge + SC lifecycle — bridge.py done (deprecated); SCManager
  reused in Phase 2.
- **M4** Record orchestration — recorder + normalize reused in Phase 2.
- **M5** Skill packaging — **SKILL.md exists but uses obsolete pipeline**;
  rewrite in R3.
- **M6** Cross-platform validation — partially done (macOS arm64 verified);
  Linux/WSL2 verification deferred to Phase 2 T10.
- **M7** Multi-stem rendering — deferred to Phase 3.
- **M8** Pattern library + presets — deferred to Phase 3.

The full P0/P0.6/P0.7 audit findings from May 25 are also in HISTORY; all
closed against `main` before the Phase 2 pivot.
