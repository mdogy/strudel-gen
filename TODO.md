# TODO

Tracking against [docs/redesign-tidal.md](docs/redesign-tidal.md) (Phase 2 — current).
Closed items move to [HISTORY.md](HISTORY.md). All work governed by [SWED.md](SWED.md).

---

## 🔖 RESUME HERE (next session)

**Current state:** R1-R8 all closed. 195 tests, 87% coverage.
`strudel-gen render --engine tidal` works as a CLI command.
`make install-skill` symlinks the Phase-2 skill.
The Grimes torture test transpiles to valid Tidal.

**Headline goal of next session:** Doctor extensions (T8) + E2E acceptance (T10).

### Smoke test that everything still works

```bash
cd /path/to/strudel-gen && source .venv/bin/activate
python -m pytest tests/unit --cov-fail-under=85  # must pass
make smoke-render  # renders src/tidal/sample.tidal → /tmp/smoke-render.wav
```

### Priority queue (do in this order)

1. **T8 — Doctor extensions.** `make doctor` shows rows for ghci, tidal package, ffmpeg with per-OS install hints.

3. **T9 — Documentation pass.** README diagram + `docs/quick-start.md` rewrite + `docs/tidal-guide.md`.

4. **T10 — E2E acceptance.** `make smoke-render` from clean shell; CI `tidal-smoke` nightly job that renders a short pattern end-to-end.

### Closed this session (R1-R8)

See [HISTORY.md §2026-05-26](HISTORY.md) for details.

---

## ⭐ PHASE 2 — Tidal Cycles pipeline (current architecture)

### Open decisions

- [ ] **Tidal version pin** — currently 1.9.5 (was 1.10.1 in plan). Reconcile.
- [ ] **MP3 default bitrate** — 320 kbps proposed.
- [ ] **Windows-native Tidal?** — WSL2-only proposed; native Windows gets `--engine sc-native` only.
- [ ] **Where do transpiled `.tidal` files live?** — currently committed at `src/tidal/<slug>.tidal`. Alternative: regenerate per render.

### T-series milestone status (cleaned)

| ID | Title | State | Notes |
|---|---|---|---|
| T0 | Host pre-flight | ✓ (macOS arm64 only) | Linux/WSL2 unverified |
| T1 | Architectural lock-in | ✓ | All docs written |
| T2.1 | Lexer | ✓ | But too narrow — see R5 |
| T2.2 | Parser | ✓ | But too narrow — see R5 |
| T2.3 | Validator | ✓ | Missing synth-name check — see R4 |
| T2.4 | Emitter + 12 golden tests | ✓ | 27 unit tests passing |
| T3 | BootTidal.hs + reference patterns | ✓ | `dr-who-inspired.tidal`, `theremin-only.tidal`, `sample.tidal` |
| T4 | TidalManager Python class | ✓ except cleanup | See R1 (kills ghc grandchild) |
| T5 | Headless SuperDirt SC startup | ✓ via system startup.scd | `numWireBufs=1024` deployed |
| T6 | Render orchestrator + CLI | partial | Works as script; not yet `--engine tidal` subcommand — see R2 |
| **T6.5** | **Silent-WAV blocker** | **✓ closed** | Flag-file fix landed |
| T7 | MP3 + sidecar JSON | ✓ | `--mp3 320` flag; `<out>.json` sidecar always written |
| T8 | Doctor + detection (ghci, tidal) | open | Add rows to `make doctor` |
| T9 | Documentation pass | partial | redesign-tidal.md is current; README + quick-start still Phase-1 |
| T10 | E2E acceptance | open | `make smoke-render` + CI `tidal-smoke` job; blocked on T7/T8 landing |

### Phase 2 done-gate

R1–R8 closed **AND** `strudel-gen render --engine tidal ...` works as a CLI
command **AND** the skill triggers from a fresh Claude Code session **AND**
the smoke test in "RESUME HERE" passes from a clean shell on macOS, Linux,
and WSL2.

---

## 📦 Phase 1 legacy (Strudel-bridge architecture — superseded)

The complete original M0–M8 milestone list, P0/P0.6/P0.7 audit findings, and
the resolved blocking decisions are kept in
[git history](https://github.com/mdogy/strudel-gen) and chronologically in
[HISTORY.md → 2026-05-24](HISTORY.md). All Phase-1 work was either:

- Folded into Phase 2 (sclang detection, SCManager, recorder, normalize, etc.).
- Made obsolete by the architectural pivot (bridge.py, scripts/bridge.sh, etc.).
- Replaced (skill/SKILL.md — being rewritten in R3).

If you need a specific Phase-1 milestone reference, see HISTORY. **Do not
restart Phase-1 work** without first reading [docs/redesign-tidal.md §1](docs/redesign-tidal.md#1-why-we-are-doing-this).
