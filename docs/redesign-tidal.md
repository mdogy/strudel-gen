# Redesign: Tidal Cycles Pipeline (Phase 2)

> **READ FIRST if you are picking this up cold:**
> 1. **[§12 State of the world](#12-state-of-the-world-verified-2026-05-25)** — what works today, smoke-test command, what doesn't work yet.
> 2. **[§13 SuperDirt synth registry](#13-superdirt-synth-registry-verified-2026-05-25)** — only use synth names from this list; `supersine`/`supertri` produce silence.
> 3. **[§14 Pitfalls catalog](#14-pitfalls-catalog-expanded-with-2026-05-25-findings)** — the 13 specific failure modes already debugged.
> 4. **[TODO.md "RESUME HERE"](../TODO.md#-resume-here-next-session)** — the prioritized R1–R8 work queue.
>
> Then read the rest of this doc top-to-bottom only if you need to.
>
> ---
>
> **This is an implementer's recipe, not an architecture essay.**
> Every milestone below has: (1) files to create, (2) exact commands to run,
> (3) exact expected output, (4) what to do if it fails.
> A less-capable model should be able to ship each milestone by copying the
> skeletons and following the verification steps. If a step lacks a concrete
> command, that is a bug — file an issue.

---

## 0. The full cycle (TL;DR)

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 1 — Prompt + Skill                                                   │
│    User: "make me 3 min of cold underwater ambience"                        │
│    Claude Code: matches `ambient-render` skill                              │
│    Skill instructions: parse mood, duration, output path                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 2 — LLM-authored Strudel  (this is what Claude is GOOD at)           │
│    Claude writes a Strudel .js into src/patterns/<mood-slug>.js             │
│    Constraints: setcpm + stack, every layer .slow(>=4) and .room(>=0.7),    │
│                 .orbit(0..5), no JS arrow modifiers beyond v1 spec          │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 3 — Strudel → Tidal  (Python transpiler, deterministic)              │
│    strudel-gen transpile reads .js, writes a .tidal of equivalent layers    │
│    Validator rejects anything the transpiler can't safely handle            │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 4 — Tidal → SuperDirt audio  (ghci subprocess → OSC → sclang)        │
│    Python TidalManager spawns ghci, feeds BootTidal.hs, then the .tidal     │
│    Tidal streams OSC to SuperDirt running inside sclang on port 57120       │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 5 — Audio → WAV/MP3                                                  │
│    SC records to WAV via s.record (24-bit, 48 kHz, stereo)                  │
│    ffmpeg loudnorm to −6 dBFS; optional MP3 320 kbps; sidecar JSON          │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                       ~/Desktop/<mood>.wav  +  .mp3  +  .json
```

**Five Python files do the new work**, none of them larger than ~250 lines:

1. `src/strudel_gen/transpiler/lexer.py`
2. `src/strudel_gen/transpiler/parser.py`
3. `src/strudel_gen/transpiler/emitter.py`
4. `src/strudel_gen/transpiler/validator.py`
5. `src/strudel_gen/tidal.py`

Plus three SC/Haskell artefacts:

1. `src/tidal/BootTidal.hs` (vendored upstream)
2. `src/supercollider/startup-superdirt.scd`
3. `src/tidal/dr-who-inspired.tidal` (reference port)

And one orchestrator + CLI edit:

1. `src/strudel_gen/render_orchestrator.py`
2. `src/strudel_gen/cli.py` (add subcommands)

That's the entire delivery. Everything else in this document is recipe and
verification for those ten files.

---

## 1. Why we are doing this

Long form in [redesign-tidal.md@v1](redesign-tidal.md) (this doc's prior
revision in git history). Compressed reasons:

- **Strudel needs a browser**; cannot be automated.
- **SuperDirt sample loading is 120 s / 450 MB** — accepted as a one-time per
  render cost. Native-SC `.scd` fast path remains for samples-free moods.
- **Tidal Cycles is Strudel's parent project** — same OSC, same orbits, same
  mini-notation, runs in `ghci` which IS scriptable.
- **Claude is good at Strudel** because GitHub has thousands of working
  examples in Strudel syntax. Asking Claude to write Tidal directly is worse
  (smaller training corpus, Haskell unfamiliarity). So: keep the LLM author in
  Strudel, transpile to Tidal mechanically.

---

## 2. Stage 1 — The skill (prompt → CLI invocation)

### 2.1 SKILL.md (exact contents)

Replace `skill/SKILL.md` with the file below. The description IS the trigger;
do not rewrite it without testing trigger sensitivity.

~~~markdown
---
name: ambient-render
description: |
  Use this skill when the user asks for ambient background music,
  a soundscape for a video, generative drone audio, or a sci-fi /
  underwater / forest / etc. audio bed. Produces a rendered WAV file
  on the user's machine. Triggers on phrases like
  "background music for", "ambient soundscape", "drone audio",
  "make a soundtrack", "Dr. Who-style theme", "underwater ambience".
  Do NOT use for vocal music, songs with lyrics, pop tracks, beat-driven
  EDM, or any request that names a copyrighted artist.
allowed-tools: Bash
---

# ambient-render

You are about to produce a rendered ambient soundscape WAV file by writing
a short Strudel `.js` pattern and running the project's render pipeline.

## Inputs you need (ask if missing)

- **Mood description**: 1-2 sentences ("cold underwater", "alien forest at dawn").
- **Duration**: seconds. Default 120 if unspecified.
- **Output path**: default `~/Desktop/<mood-slug>.wav`.

## Steps

1. Generate a slug from the mood (kebab-case, ≤ 32 chars). Call it `<slug>`.
2. Write a Strudel `.js` file to `src/patterns/<slug>.js` following the
   conventions in [CLAUDE.md](../../CLAUDE.md) and the templates in
   [docs/redesign-tidal.md §6](../../docs/redesign-tidal.md#6-llm-author-cheat-sheet).
3. Run:

       strudel-gen render \
         --engine tidal \
         --pattern src/patterns/<slug>.js \
         --duration <seconds> \
         --out <output_path> \
         --mp3 320

4. Report the output paths back to the user (WAV + MP3 + sidecar JSON).

## Constraints (binding)

- Use only Strudel functions listed in §4 of the cheat sheet.
- Every layer must have `.slow(>=4)` and `.room(>=0.7)`.
- Use `.orbit(N)` for layer separation, N ∈ {0..5}.
- No arrow-function modifiers beyond single-call: `x => x.<method>(<args>)`.
~~~

### 2.2 Smoke-test the skill description

```bash
# Manual: open a fresh Claude Code session, paste:
#   "Can you make me 90 seconds of background music for a forest meditation video?"
# Expected: the `ambient-render` skill fires (you'll see it in the skill picker).
#
# Negative case:
#   "Can you write me a pop song about my dog?"
# Expected: skill does NOT fire.
```

If it fires too eagerly (or not at all), tighten the description; rerun the
test. **Do not** edit the skill body until the description is right.

---

## 3. Stage 2 — LLM-authored Strudel

This stage is **a Claude API/CLI call**, not Python code. The skill body
in §2.1 contains the entire prompt template. Claude reads the constraints,
looks at the templates in §6, and emits a `.js` file.

A minimal `src/patterns/<slug>.js` looks exactly like this (copy/edit):

```javascript
// src/patterns/cold-underwater.js
setcpm(20)
stack(
  note("c2 g2 d3 a2").s("sawtooth").lpf(280).room(0.92).slow(8).orbit(0),
  note("eb4 ~ ~ bb4 ~ c5 ~ ~").s("sine").room(0.88).delay(0.4).slow(6).orbit(1),
  note("c3,eb3,g3").s("sine").room(0.9).gain(0.15).slow(12).orbit(2)
)
```

That's it. Three layers, every constraint satisfied. If Claude produces
something outside §4's whitelist, the validator (Stage 3) will fail loudly with
the offending source line.

---

## 4. Stage 3 — Strudel → Tidal transpiler

### 4.1 The complete mapping table

This is the **whitelist**. Anything not in this table is rejected by the
validator.

| # | Strudel | Tidal | Notes |
| --- | --- | --- | --- |
| 1 | `setcpm(N)` (top-level) | `setcps (N/60/4)` (emit as first line) | Convert cpm → cps |
| 2 | `stack(L1, L2, …)` | emit `d1 $ L1`, `d2 $ L2`, … or follow `.orbit()` | Each layer gets its own `dN` |
| 3 | `note("…")` | `note "…"` | Strip parens, keep string |
| 4 | `s("…")` (head) | `s "…"` | Strip parens, keep string |
| 5 | `n("…")` | `n "…"` | Same |
| 6 | `.s("…")` (chained) | `# s "…"` | `#` is Tidal's param combinator |
| 7 | `.n("…")` | `# n "…"` | Same |
| 8 | `.room(0.9)` | `# room 0.9` | Numeric literal |
| 9 | `.room("0.7 0.9")` | `# room "0.7 0.9"` | Pattern literal stays quoted |
| 10 | `.lpf(280)` | `# lpf 280` | |
| 11 | `.gain(0.5)` | `# gain 0.5` | |
| 12 | `.delay(0.4)` | `# delay 0.4` | |
| 13 | `.delayt(0.5)` | `# delaytime 0.5` | **renamed** |
| 14 | `.delayfb(0.6)` | `# delayfeedback 0.6` | **renamed** |
| 15 | `.vib(4)` | `# vib 4` | |
| 16 | `.vibdepth(0.01)` | `# vibdepth 0.01` | |
| 17 | `.speed(2)` | `# speed 2` | |
| 18 | `.pan(0.5)` | `# pan 0.5` | |
| 19 | `.crush(8)` | `# crush 8` | |
| 20 | `.shape(0.4)` | `# shape 0.4` | |
| 21 | `.slow(4)` | `# slow 4` | |
| 22 | `.fast(2)` | `# fast 2` | |
| 23 | `.rev()` | `# rev` | No args in Tidal |
| 24 | `.orbit(N)` | dispatches to `d{N+1} $ …` | Layer routing; not emitted in chain |
| 25 | `.every(N, x => x.rev())` | `every N rev` | Single-call arrow only |
| 26 | `.sometimes(x => x.speed("2"))` | `sometimes (\|+ speed "2")` | Single-call arrow only |
| 27 | `// comment` | `-- comment` | Line comment |

### 4.2 Worked examples

**Example A — bare layer:**

```javascript
// Strudel
note("c2 g2").s("sine").room(0.9).slow(4).orbit(0)
```

```haskell
-- Tidal (after transpile)
d1 $ note "c2 g2" # s "sine" # room 0.9 # slow 4
```

**Example B — stack with orbits:**

```javascript
// Strudel
setcpm(40)
stack(
  note("c2 g2").s("sawtooth").room(0.9).slow(4).orbit(0),
  note("c5 ~ g4").s("sine").room(0.85).slow(6).orbit(1)
)
```

```haskell
-- Tidal
setcps (40/60/4)

d1 $ note "c2 g2" # s "sawtooth" # room 0.9 # slow 4
d2 $ note "c5 ~ g4" # s "sine" # room 0.85 # slow 6
```

**Example C — `every` modifier:**

```javascript
// Strudel
note("c2 g2").s("sine").every(4, x => x.rev()).slow(4).orbit(0)
```

```haskell
-- Tidal
d1 $ every 4 rev $ note "c2 g2" # s "sine" # slow 4
```

### 4.3 Skeleton code for the transpiler package

Create `src/strudel_gen/transpiler/__init__.py`:

```python
"""Strudel JS → Tidal Cycles .tidal transpiler.

Public API:
    transpile(src: str) -> str
    transpile_file(in_path: Path, out_path: Path) -> None
"""
from pathlib import Path

from .lexer import tokenize
from .parser import parse
from .validator import validate
from .emitter import emit


def transpile(src: str) -> str:
    """Strudel source → Tidal source."""
    tokens = tokenize(src)
    tree = parse(tokens)
    validate(tree)
    return emit(tree)


def transpile_file(in_path: Path, out_path: Path) -> None:
    out_path.write_text(transpile(in_path.read_text()))
```

Create `src/strudel_gen/transpiler/lexer.py` (skeleton — fill in the bodies):

```python
"""Tokenize Strudel source into a flat stream.

We only need to recognize: identifiers, numbers, strings ('…' or "…"),
`(`, `)`, `,`, `.`, `=>`, `//` comments, `/* */` comments, and whitespace.
"""
from __future__ import annotations
import re
from dataclasses import dataclass


@dataclass
class Token:
    kind: str   # IDENT | NUMBER | STRING | LPAREN | RPAREN | DOT | COMMA | ARROW | COMMENT
    value: str


_TOKEN_RE = re.compile(
    r"""
    (?P<COMMENT_LINE> //[^\n]*           )|
    (?P<COMMENT_BLOCK>/\*.*?\*/          )|
    (?P<WS>           \s+                )|
    (?P<STRING>       "[^"]*"|'[^']*'    )|
    (?P<NUMBER>       -?\d+(\.\d+)?      )|
    (?P<ARROW>        =>                 )|
    (?P<IDENT>        [A-Za-z_][A-Za-z0-9_]* )|
    (?P<LPAREN>       \(                 )|
    (?P<RPAREN>       \)                 )|
    (?P<DOT>          \.                 )|
    (?P<COMMA>        ,                  )
    """,
    re.VERBOSE | re.DOTALL,
)


def tokenize(src: str) -> list[Token]:
    out: list[Token] = []
    pos = 0
    while pos < len(src):
        m = _TOKEN_RE.match(src, pos)
        if not m:
            raise SyntaxError(f"unexpected char at offset {pos}: {src[pos]!r}")
        kind = m.lastgroup
        value = m.group()
        pos = m.end()
        if kind in {"WS", "COMMENT_LINE", "COMMENT_BLOCK"}:
            continue
        out.append(Token(kind=kind, value=value))
    return out
```

Create `src/strudel_gen/transpiler/parser.py` (skeleton):

```python
"""Parse a token stream into a PatternFile AST."""
from __future__ import annotations
from dataclasses import dataclass, field

from .lexer import Token


@dataclass
class Arg:
    kind: str        # NUMBER | STRING | LAMBDA_CALL
    value: object    # float | str | tuple(method_name, args)


@dataclass
class ChainCall:
    name: str            # "room", "lpf", "slow", "every", "sometimes", "orbit"...
    args: list[Arg]


@dataclass
class Layer:
    head: str            # "note" | "s" | "n"
    head_arg: str        # the inner string (without quotes)
    chain: list[ChainCall] = field(default_factory=list)


@dataclass
class PatternFile:
    cpm: int | None
    layers: list[Layer] = field(default_factory=list)


def parse(tokens: list[Token]) -> PatternFile:
    """Implement a small recursive-descent parser.

    Top-level production:
      File   := SetCPM? Stack
      SetCPM := 'setcpm' '(' NUMBER ')'
      Stack  := 'stack' '(' Layer (',' Layer)* ')'
              | Layer                              -- single-layer shorthand
      Layer  := Head Chain*
      Head   := ('note' | 's' | 'n') '(' STRING ')'
      Chain  := '.' IDENT '(' Args? ')'
      Args   := Arg (',' Arg)*
      Arg    := NUMBER | STRING | Lambda
      Lambda := IDENT '=>' IDENT '.' IDENT '(' Arg? ')'   -- single-call only
    """
    raise NotImplementedError  # FILL IN
```

Create `src/strudel_gen/transpiler/validator.py`:

```python
"""Reject unsupported Strudel constructs with a clear error."""
from __future__ import annotations

from .parser import PatternFile

_ALLOWED_CHAIN_CALLS = frozenset({
    "s", "n", "room", "lpf", "hpf", "gain", "delay", "delayt", "delayfb",
    "vib", "vibdepth", "speed", "pan", "crush", "shape",
    "slow", "fast", "rev", "orbit", "every", "sometimes", "often", "rarely",
})


class UnsupportedConstruct(ValueError):
    """Raised when the AST contains something the transpiler cannot handle."""


def validate(tree: PatternFile) -> None:
    if tree.cpm is None:
        raise UnsupportedConstruct("missing setcpm(N) at top level")
    for layer in tree.layers:
        for call in layer.chain:
            if call.name not in _ALLOWED_CHAIN_CALLS:
                raise UnsupportedConstruct(
                    f"unsupported method .{call.name}() — see redesign-tidal.md §4.1"
                )
    # Caller may add more checks (e.g. slow >= 4, room >= 0.7).
```

Create `src/strudel_gen/transpiler/emitter.py`:

```python
"""AST → .tidal source."""
from __future__ import annotations

from .parser import PatternFile, Layer, ChainCall, Arg

# Strudel → Tidal name renames (table §4.1 col-3 differences)
_RENAME = {
    "delayt":  "delaytime",
    "delayfb": "delayfeedback",
}


def _emit_arg(a: Arg) -> str:
    if a.kind == "NUMBER":
        return str(a.value)
    if a.kind == "STRING":
        return f"\"{a.value}\""
    if a.kind == "LAMBDA_CALL":
        method, sub_args = a.value
        sub = " ".join(_emit_arg(x) for x in sub_args) if sub_args else ""
        return f"{method}" if not sub else f"(|+ {method} {sub})"
    raise ValueError(a.kind)


def _emit_chain_call(c: ChainCall) -> str:
    name = _RENAME.get(c.name, c.name)
    args = " ".join(_emit_arg(a) for a in c.args)
    return f"# {name} {args}".rstrip()


def _emit_layer(layer: Layer, orbit_idx: int) -> str:
    head = f'{layer.head} "{layer.head_arg}"'
    # Pull out modifier-style chain calls (every, sometimes) — Tidal expects
    # them as wrappers, not `# ...`. Everything else uses `# name value`.
    prefix_calls: list[ChainCall] = []
    param_calls: list[ChainCall] = []
    for c in layer.chain:
        if c.name == "orbit":
            continue                # routing only; not in the chain
        if c.name in {"every", "sometimes", "often", "rarely", "rev", "slow", "fast"}:
            prefix_calls.append(c)
        else:
            param_calls.append(c)

    params = " ".join(_emit_chain_call(c) for c in param_calls)
    body = f"{head} {params}".strip()

    # Wrap with prefix modifiers from innermost out
    for c in reversed(prefix_calls):
        name = _RENAME.get(c.name, c.name)
        args = " ".join(_emit_arg(a) for a in c.args)
        body = f"{name} {args} $ {body}".strip()

    return f"d{orbit_idx + 1} $ {body}"


def emit(tree: PatternFile) -> str:
    lines: list[str] = []
    lines.append(f"setcps ({tree.cpm}/60/4)")
    lines.append("")
    for i, layer in enumerate(tree.layers):
        # Use explicit .orbit() if present, otherwise fall back to position.
        orbit = next((c for c in layer.chain if c.name == "orbit"), None)
        idx = int(orbit.args[0].value) if orbit else i
        lines.append(_emit_layer(layer, idx))
    return "\n".join(lines) + "\n"
```

### 4.4 Golden-file tests

Create `tests/unit/test_transpiler.py`:

```python
"""Golden-file tests: each .js fixture has an expected .tidal fixture."""
from pathlib import Path
import pytest
from strudel_gen.transpiler import transpile

FIXTURES = Path(__file__).parent / "fixtures" / "transpiler"


@pytest.mark.parametrize("name", [
    "bare_layer",
    "stack_two",
    "stack_three_with_orbits",
    "every_rev",
    "sometimes_speed",
    "delaytime_rename",
    "comment_line",
    "single_layer_no_stack",
    "fractional_room",
    "pattern_value",
    "slow_fast_combo",
    "dr_who",
])
def test_golden(name: str) -> None:
    src = (FIXTURES / f"{name}.js").read_text()
    expected = (FIXTURES / f"{name}.tidal").read_text()
    assert transpile(src) == expected


def test_unknown_method_rejected() -> None:
    from strudel_gen.transpiler.validator import UnsupportedConstruct
    with pytest.raises(UnsupportedConstruct, match="csound"):
        transpile('setcpm(20)\nnote("c").csound("foo").slow(4).room(0.8)')


def test_missing_cpm_rejected() -> None:
    from strudel_gen.transpiler.validator import UnsupportedConstruct
    with pytest.raises(UnsupportedConstruct, match="setcpm"):
        transpile('note("c").s("sine").slow(4).room(0.8)')
```

Pair each `<name>.js` with a hand-written `<name>.tidal` under
`tests/unit/fixtures/transpiler/`. Twelve pairs is the T2 done-criterion.

---

## 5. Stage 4 — TidalManager + ghci subprocess

### 5.1 BootTidal.hs (vendored, exact contents)

Create `src/tidal/BootTidal.hs`. The block below is the **upstream-canonical**
boot file from Tidal 1.10.x with a single addition: the sentinel line
`putStrLn "tidal-ready"` at the very end so our Python wrapper can detect that
GHCi finished loading.

```haskell
:set -XOverloadedStrings
:set prompt ""
:set prompt-cont ""

import Sound.Tidal.Context

tidal <- startTidal (superdirtTarget {oLatency = 0.1, oAddress = "127.0.0.1", oPort = 57120}) (defaultConfig {cFrameTimespan = 1/20})

let p = streamReplace tidal
let hush = streamHush tidal
let list = streamList tidal
let mute = streamMute tidal
let unmute = streamUnmute tidal
let solo = streamSolo tidal
let unsolo = streamUnsolo tidal
let once = streamOnce tidal
let asap = once
let nudgeAll = streamNudgeAll tidal
let all = streamAll tidal
let resetCycles = streamResetCycles tidal
let setcps = asap . cps

let d1  = p 1  . (|< orbit 0)
let d2  = p 2  . (|< orbit 1)
let d3  = p 3  . (|< orbit 2)
let d4  = p 4  . (|< orbit 3)
let d5  = p 5  . (|< orbit 4)
let d6  = p 6  . (|< orbit 5)
let d7  = p 7  . (|< orbit 6)
let d8  = p 8  . (|< orbit 7)
let d9  = p 9  . (|< orbit 8)
let d10 = p 10 . (|< orbit 9)
let d11 = p 11 . (|< orbit 10)
let d12 = p 12 . (|< orbit 11)

:set prompt "tidal> "
putStrLn "tidal-ready"
```

**Verify by hand once before T4:**

```bash
# In one terminal: start SC with SuperDirt
sclang src/supercollider/startup-superdirt.scd
# (wait ~120 s for "SuperDirt: listening on port 57120")

# In another terminal:
ghci
> :load src/tidal/BootTidal.hs
# Expected: prints "tidal-ready" and gives you a `tidal>` prompt

> d1 $ s "bd*4"
# Expected: kick drum starts playing through your speakers

> hush
# Expected: silence
> :quit
```

If `tidal-ready` doesn't print, the import line failed — see §8 pitfalls.

### 5.2 TidalManager skeleton

Create `src/strudel_gen/tidal.py`:

```python
"""Manage a ghci subprocess running Tidal Cycles."""
from __future__ import annotations
import logging
import re
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_READY_RE = re.compile(r"^tidal-ready$", re.MULTILINE)


class TidalError(RuntimeError):
    pass


class TidalManager:
    """Spawns ghci, loads BootTidal.hs, exposes send()/hush()/stop().

    Public API mirrors BridgeManager so the orchestrator can use either.

    Args:
        boot_file: Path to BootTidal.hs.
        ghci:      Path to the ghci binary. Defaults to 'ghci' on PATH.
        timeout:   Seconds to wait for the 'tidal-ready' sentinel.
    """

    def __init__(
        self,
        boot_file: Path | None = None,
        ghci: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        if boot_file is None:
            boot_file = Path(__file__).resolve().parent.parent / "tidal" / "BootTidal.hs"
        if not boot_file.exists():
            raise TidalError(f"BootTidal.hs not found at {boot_file}")
        if ghci is None:
            import shutil
            ghci = shutil.which("ghci")
        if ghci is None:
            raise TidalError(
                "ghci not found on PATH. Install Haskell via ghcup "
                "(https://www.haskell.org/ghcup/) then `cabal install tidal`."
            )
        self._ghci = ghci
        self._boot = boot_file
        self._timeout = timeout
        self._proc: subprocess.Popen[str] | None = None

    def start(self) -> None:
        logger.info("Starting ghci (%s) with %s", self._ghci, self._boot)
        self._proc = subprocess.Popen(
            [self._ghci, "-ghci-script", str(self._boot)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            assert self._proc.stdout is not None
            line = self._proc.stdout.readline()
            if not line:
                break
            logger.debug("[ghci] %s", line.rstrip())
            if _READY_RE.search(line):
                logger.info("Tidal ready")
                return
        self.stop()
        raise TidalError(f"Tidal did not become ready within {self._timeout}s")

    def send(self, code: str) -> None:
        """Send a block of Haskell/Tidal code to ghci stdin."""
        if not self._proc or not self._proc.stdin:
            raise TidalError("Tidal not running")
        logger.debug("[tidal send] %s", code)
        self._proc.stdin.write(code if code.endswith("\n") else code + "\n")
        self._proc.stdin.flush()

    def hush(self) -> None:
        self.send("hush")

    def stop(self) -> None:
        if self._proc is None:
            return
        try:
            self.hush()
            time.sleep(0.5)
            self.send(":quit")
            self._proc.wait(timeout=5)
        except Exception as exc:
            logger.warning("Tidal stop hit %s; killing", exc)
            self._proc.kill()
            self._proc.wait(timeout=5)
        finally:
            self._proc = None

    def __enter__(self) -> "TidalManager":
        self.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.stop()
```

### 5.3 Verification command

```bash
# After installing ghci + tidal and writing the skeleton above:
.venv/bin/python -c "
from strudel_gen.tidal import TidalManager
with TidalManager(timeout=30) as t:
    print('Tidal up')
    t.send('-- noop')
print('Stopped cleanly')
"
```

Expected output:

```text
Tidal up
Stopped cleanly
```

If you see `Tidal did not become ready within 30s`, increase timeout, then
read the captured stdout from the logger to see what ghci printed.

---

## 5.5 Stage 5 — Synchronized recording trigger (silent-WAV fix)

> **2026-05-25 finding.** The first end-to-end Tidal render produced a 10 s WAV
> at −91 dBFS (digital silence) despite SuperDirt loading 218 sample banks
> and ghci accepting the pattern without errors. Diagnosis below; binding
> contract for any future render orchestrator.

### 5.5.1 The wrong pattern (do not use)

```supercollider
s.waitForBoot {
    fork {
        45.wait;                        // ← fires from server-boot
        s.record(path, duration: 30);
        0.exit;
    };
};
```

Why this fails: the `45.wait` measures from scsynth boot. But the audible
stack only comes up much later — `~dirt.loadSoundFiles` runs ~120 s, then
Python starts `ghci` (~30 s) and sends the pattern. Recording therefore
captures bus 0–1 during a window when nothing is yet on those buses.

Timeline of the bug (numbers from the 2026-05-25 measurement):

| Wall-clock | Event |
|---|---|
| t=0 | `sclang` launched |
| t=10 | scsynth booted, `s.waitForBoot` callbacks fire |
| t=10 | `fork { 45.wait; ... }` starts counting |
| t=10–130 | SuperDirt `loadSoundFiles` runs (218 banks, ~450 MB RAM) |
| **t=55** | **`s.record` begins recording** (bus 0–1 is silent) |
| **t=85** | **recording duration (30 s) ends; WAV is final** |
| t=117 | fork exits; sclang `0.exit` |
| t=130 | SuperDirt finally prints "listening on port 57120" (sclang already gone) |
| t=130 | Python sees `listening`, starts ghci |
| t=160 | ghci ready, BootTidal.hs loaded |
| t=160 | Python sends the Tidal pattern — but sclang+SuperDirt are dead, OSC goes nowhere |

The WAV file exists. It is 30 s of silence.

### 5.5.2 The correct pattern (binding)

Recording must start **after** Python has verified Tidal is producing OSC.
The simplest reliable mechanism is a filesystem flag:

```supercollider
s.waitForBoot {
    s.recHeaderFormat = "WAV";
    s.recSampleFormat = "int24";
    s.recChannels = 2;
    fork {
        var flagPath = "<absolute path Python will touch>";
        var waited = 0;
        while { File.exists(flagPath).not and: { waited < 600 } } {
            0.25.wait;
            waited = waited + 0.25;
        };
        s.record(path: "<out.wav>", duration: <dur>);
        (<dur> + 2).wait;
        0.exit;
    };
};
```

Python side (the only changes from the previous orchestrator):

```python
# 1. start sclang with the temp .scd above
# 2. wait for "SuperDirt: listening"
# 3. start TidalManager, wait for ready
# 4. send the Tidal pattern (tidal.eval per line)

time.sleep(2.0)        # let OSC events start landing on bus 0-1
Path(flag).touch()     # ← this is the trigger

sc_proc.wait(timeout=duration + 60)
tidal.hush(); tidal.stop()
```

The 2-second settle is empirical: it's roughly two cycles at `cps=1.0`, enough
for the first events to clear `oLatency` and reach scsynth.

### 5.5.3 Why a flag file (vs. OSC, vs. stdin)

| Mechanism | Verdict | Reason |
|---|---|---|
| `sclang -` stdin | ❌ doesn't work | sclang ignores stdin when invoked as `sclang -`; confirmed empirically. |
| Pre-set timer (`N.wait`) | ❌ unreliable | breaks when SuperDirt load time changes; this is the bug we just hit |
| OSC from Python to sclang | ⚠️ feasible | adds dependency on a Python OSC library, more moving parts |
| Filesystem flag (chosen) | ✅ robust | zero deps, fork polls with `File.exists`, Python touches the path |
| TCP from Python to sclang | ⚠️ feasible | overkill for a single trigger event |

### 5.5.4 Verification

After applying the fix:

```bash
.venv/bin/python scripts/render_tidal.py src/tidal/sample.tidal 10 /tmp/x.wav
# Expected output (key lines):
#   1. Starting SuperCollider with recording-trigger script...
#      [sc] SuperDirt: listening on port 57120
#   2. Starting Tidal ghci...
#   3. Evaluating pattern...
#      > setcps 1.0
#      > d1 $ sound "bd" # gain 0.8 # orbit 0
#   4. Letting pattern settle (2 s)...
#   5. Triggering recording (touching /tmp/tidal-render-.../start-record.flag)...
#   6. Waiting for sclang to finish recording (~15 s)...
#      [sc] Trigger received; recording 10s to /tmp/x.wav
#   …
#   9. Output: /tmp/x.wav (1900.0 KB)
#      Audio: max_volume: -3.4 dB
#      Audio: mean_volume: -23.8 dB

ffmpeg -i /tmp/x.wav -af volumedetect -f null /dev/null 2>&1 | grep mean_volume
# Expected: mean_volume > -60 dB  (anything < -70 dB means the bug is back)
```

If `mean_volume` is still < −70 dB even with the flag mechanism, the next
suspect is OSC routing — confirm with:

```supercollider
// In sclang IDE while SuperDirt is running:
n = NetAddr("127.0.0.1", 57120);
n.sendMsg("/dirt/play", "s", "bd", "gain", 1.0);
// Expected: kick drum audible immediately. If silent, SuperDirt itself
// is not receiving — port mismatch or oAddress mismatch in BootTidal.hs.
```

---

## 6. LLM-author cheat sheet (what Claude should produce)

When the skill body in §2.1 fires, Claude writes a `.js` file. Templates by
mood family:

### 6.1 Drone (slow, low, dark)

```javascript
setcpm(14)
stack(
  note("c2 ~ g2 ~").s("sawtooth").lpf(180).room(0.95).slow(8).orbit(0),
  note("c5 ~ ~ eb5 ~ ~ g5 ~").s("sine").room(0.9).gain(0.18).slow(12).orbit(1),
  note("c3,g3,c4").s("sine").room(0.95).gain(0.12).slow(16).orbit(2)
)
```

### 6.2 Sci-fi / theme (motivic, rhythmic, eerie)

```javascript
setcpm(80)
stack(
  note("e1 d1 e1 d1 e1 d1 c1 d1").s("sine").lpf(220).room(0.9).slow(4).orbit(0),
  note("b4 d5 e5 d5 b4 e4 g4 a4").s("sine").vib(4).vibdepth(0.01).room(0.88).slow(4).orbit(1),
  note("e3,g3,b3").s("sine").room(0.92).gain(0.14).slow(8).orbit(2)
)
```

### 6.3 Organic / forest (textural, breathy)

```javascript
setcpm(24)
stack(
  s("wind:0 ~ wind:1 ~").gain(0.3).room(0.9).slow(8).orbit(0),
  note("a4 ~ c5 ~ e5 ~").s("sine").room(0.85).delay(0.5).slow(6).orbit(1),
  note("a3,c4,e4").s("sine").room(0.92).gain(0.13).slow(10).orbit(2)
)
```

### 6.4 What NOT to produce (anti-examples)

```javascript
// BAD: uses csound (rejected by validator)
note("c").s("sine").csound("foo").slow(4).room(0.8)

// BAD: multi-statement arrow function (rejected)
note("c").every(4, x => { x.rev(); x.gain(0.5); }).slow(4).room(0.8)

// BAD: missing setcpm
note("c").s("sine").slow(4).room(0.8)

// BAD: layer has slow < 4 (validator can enforce)
note("c").s("sine").slow(2).room(0.8)

// BAD: layer has room < 0.7
note("c").s("sine").slow(4).room(0.4)
```

The validator (§4.3) catches the first three. Slow/room minima are checked by
a structural-validator pass (already exists in `patterns/model.py`; extend it).

---

## 7. Milestone recipes

Each T-milestone is split into **atomic sub-milestones**. A sub-milestone is
small enough to land in one focused PR with all tests green.

### T0 — Pre-flight (½ day) ─ verify host machine

**Goal:** confirm everything Phase 2 needs is on disk *before* writing code.

**Commands:**

```bash
make doctor            # existing — verifies sclang, node, pnpm, strudel-clone
which ghci             # should be /usr/local/bin/ghci or similar
ghci --version         # should say 9.x
ghc-pkg list tidal     # should list e.g. tidal-1.10.1
which ffmpeg           # should be present
```

**Expected output:** every command resolves; nothing says "not found".

**If it fails:**

- `ghci` missing → install GHC via [ghcup.haskell.org](https://www.haskell.org/ghcup/).
- `tidal` missing → `cabal update && cabal install --lib tidal`.
- `ffmpeg` missing → `brew install ffmpeg` (macOS) / `apt install ffmpeg` (Linux).

**Deliverable:** a HISTORY.md line: "T0 host-machine pre-flight green on macOS arm64 / Ubuntu 22.04 / WSL2 Ubuntu / Windows native (sc-native only)".

---

### T1 — Lock the plan in docs (already mostly done)

- [x] `docs/redesign-tidal.md` (this file).
- [x] `HISTORY.md` entry.
- [x] `TODO.md` T-block.
- [ ] Update `CLAUDE.md` — replace "writing Strudel pattern code … pasting into Strudel REPL"
  with the new instruction: "writing Strudel `.js` patterns that will be transpiled to Tidal
  and rendered headlessly".
- [ ] Update `PLAN.md` callout to point at T-series.

**Verification:**

```bash
grep -q "pasting into the Strudel REPL" CLAUDE.md && echo "STILL WRONG" || echo "OK"
```

Expected: `OK`.

---

### T2 — Strudel → Tidal transpiler (split into 4 PRs)

#### T2.1 — Lexer + tests (½ day)

**Files:**

- `src/strudel_gen/transpiler/__init__.py` (just the public API stub)
- `src/strudel_gen/transpiler/lexer.py` (copy §4.3 skeleton)
- `tests/unit/test_transpiler_lexer.py` — 8 unit tests covering each token kind

**Commands:**

```bash
pytest tests/unit/test_transpiler_lexer.py -v
ruff check src/strudel_gen/transpiler/
mypy --strict src/strudel_gen/transpiler/
```

Expected: 8 tests pass, ruff clean, mypy clean.

#### T2.2 — Parser + tests (½ day)

**Files:**

- `src/strudel_gen/transpiler/parser.py` (fill in §4.3 skeleton)
- `tests/unit/test_transpiler_parser.py` — parse 6 representative inputs, assert AST shape

**Commands:**

```bash
pytest tests/unit/test_transpiler_parser.py -v
```

#### T2.3 — Validator + tests (¼ day)

**Files:**

- `src/strudel_gen/transpiler/validator.py` (copy §4.3 skeleton)
- `tests/unit/test_transpiler_validator.py` — assert each forbidden construct raises `UnsupportedConstruct` with the expected message

#### T2.4 — Emitter + golden tests (¾ day)

**Files:**

- `src/strudel_gen/transpiler/emitter.py` (copy §4.3 skeleton)
- `tests/unit/fixtures/transpiler/<12 .js/.tidal pairs>`
- `tests/unit/test_transpiler.py` (the §4.4 test file)

**Commands:**

```bash
pytest tests/unit/test_transpiler.py -v
pytest tests/unit/test_transpiler*.py --cov=src/strudel_gen/transpiler --cov-fail-under=90
```

Expected: 12 golden tests pass, branch coverage ≥ 90 %.

---

### T3 — Tidal boot file + reference patterns (½ day)

**Files:**

- `src/tidal/BootTidal.hs` (paste §5.1 exactly)
- `src/tidal/dr-who-inspired.tidal` (run T2 transpiler on `src/patterns/dr-who-inspired.js`, save the output, commit it)
- `src/tidal/example-drone.tidal` (likewise)

**Commands:**

```bash
.venv/bin/python -c "
from pathlib import Path
from strudel_gen.transpiler import transpile_file
transpile_file(
    Path('src/patterns/dr-who-inspired.js'),
    Path('src/tidal/dr-who-inspired.tidal'),
)
print('Wrote src/tidal/dr-who-inspired.tidal')
"
# Then manual: start SC (T5), then ghci with BootTidal.hs, then :load the .tidal
```

Expected: the .tidal file plays an audibly-similar pattern to the .js when run
through the manual ghci flow in §5.1.

---

### T4 — TidalManager Python class (¾ day)

**Files:**

- `src/strudel_gen/tidal.py` (copy §5.2 skeleton; fill anything left)
- `tests/unit/test_tidal.py` — mock `subprocess.Popen`, assert stdin sequence and `_READY_RE` match
- `tests/integration/test_tidal_lifecycle.py` — only runs if `shutil.which('ghci')` and tidal-pkg-installed; spawns real ghci

**Commands:**

```bash
pytest tests/unit/test_tidal.py -v
pytest tests/integration/test_tidal_lifecycle.py -v   # skipped if ghci absent
.venv/bin/python -c "
from strudel_gen.tidal import TidalManager
with TidalManager(timeout=30) as t:
    print('OK')
"
```

---

### T5 — Headless SuperDirt startup (¼ day)

**File:** `src/supercollider/startup-superdirt.scd` (exact content):

```supercollider
// startup-superdirt.scd — ALWAYS load SuperDirt.
// Used by the Tidal render pipeline (T6).
// Prints "SuperDirt: listening on port 57120" when ready.
// SCManager greps for that string.

(
s.reboot {
    s.options.numBuffers           = 1024 * 256;
    s.options.memSize              = 8192 * 32;
    s.options.numWireBufs          = 128;
    s.options.maxNodes             = 1024 * 32;
    s.options.numOutputBusChannels = 2;
    s.options.numInputBusChannels  = 0;
    s.options.sampleRate           = 48000;

    s.waitForBoot {
        ~dirt = SuperDirt(2, s);
        ~dirt.loadSoundFiles;
        s.sync;
        ~dirt.start(57120, 0 ! 12);
        ~d1 = ~dirt.orbits[0]; ~d2 = ~dirt.orbits[1];
        ~d3 = ~dirt.orbits[2]; ~d4 = ~dirt.orbits[3];
        ~d5 = ~dirt.orbits[4]; ~d6 = ~dirt.orbits[5];
        // The sentinel SCManager looks for.
        "SuperDirt: listening on port 57120".postln;
    };
    s.latency = 0.3;
};
)
```

**Commands:**

```bash
# Direct run (expect ~120s before the sentinel prints):
/Users/michael/.local/bin/sclang src/supercollider/startup-superdirt.scd 2>&1 | tee /tmp/sd_boot.log
# Then in another terminal:
grep -q "SuperDirt: listening on port 57120" /tmp/sd_boot.log && echo OK || echo FAIL
```

Expected: `OK` within 180 s.

Also extend `SCManager.__init__` default `timeout` to 180.

---

### T6 — Render orchestrator + CLI (1 day)

**Files:**

- `src/strudel_gen/render_orchestrator.py` (new — see skeleton below)
- `src/strudel_gen/cli.py` (extend with `--engine` flag and `transpile` subcommand)
- `Makefile` add target `tidal-dr-who`

**Skeleton — `render_orchestrator.py`:**

```python
"""Top-level glue for `strudel-gen render --engine tidal`."""
from __future__ import annotations
import logging
import time
from pathlib import Path

from strudel_gen.sc import SCManager
from strudel_gen.tidal import TidalManager
from strudel_gen.transpiler import transpile_file
from strudel_gen.normalize import normalize_to_dbfs, to_mp3
from strudel_gen.recorder import RecorderScript

logger = logging.getLogger(__name__)


def render_via_tidal(
    pattern_path: Path,
    duration: float,
    out_path: Path,
    *,
    mp3_bitrate: int | None = None,
    sc_timeout: float = 180.0,
    tidal_timeout: float = 60.0,
) -> Path:
    """Run the full Stage-1-to-5 cycle. Returns the WAV path."""
    # Transpile if it's a .js
    if pattern_path.suffix == ".js":
        tidal_path = pattern_path.with_suffix(".tidal")
        transpile_file(pattern_path, tidal_path)
        logger.info("Transpiled %s → %s", pattern_path, tidal_path)
    else:
        tidal_path = pattern_path

    sc_startup = Path(__file__).resolve().parent.parent / "supercollider" / "startup-superdirt.scd"
    with SCManager(startup_file=sc_startup, timeout=sc_timeout) as sc:
        with TidalManager(timeout=tidal_timeout) as tidal:
            # Arm recording
            rec = RecorderScript(output_path=out_path, duration=duration + 8)
            sc.send_eval(rec.generate())   # NB: extend SCManager to expose this
            time.sleep(0.5)

            # Start the pattern
            tidal.send(tidal_path.read_text())
            logger.info("Pattern playing; waiting %ss", duration)
            time.sleep(duration)

            # Stop pattern; let reverb tail decay
            tidal.hush()
            time.sleep(7)
            # Recording auto-stops at `duration + 8` via the s.record duration arg.

    # Post-process
    normalize_to_dbfs(out_path, target=-6.0)
    if mp3_bitrate:
        to_mp3(out_path, bitrate=mp3_bitrate)

    return out_path
```

**CLI flag:**

```python
# in cli.py — add `--engine` to `render`
engine: Annotated[
    str,
    typer.Option("--engine", help="tidal | sc-native | strudel-bridge"),
] = "tidal",
mp3: Annotated[
    int | None,
    typer.Option("--mp3", help="Also emit MP3 at the given bitrate (e.g. 320)"),
] = None,
```

Dispatch table inside `render`:

```python
if engine == "tidal":
    from strudel_gen.render_orchestrator import render_via_tidal
    render_via_tidal(pattern_file, duration, out_path, mp3_bitrate=mp3)
elif engine == "sc-native":
    _render_via_sc_script(pattern_file, out_path, duration)
elif engine == "strudel-bridge":
    # legacy path, unchanged
    ...
else:
    raise typer.BadParameter(f"unknown engine: {engine}")
```

**Verification:**

```bash
make tidal-dr-who
# Expected output (paraphrased):
#   Transpiling src/patterns/dr-who-inspired.js → src/tidal/dr-who-inspired.tidal
#   Booting SC + SuperDirt … (this takes ~120 s)
#   SuperDirt ready
#   Starting Tidal …
#   Tidal ready
#   Pattern playing; waiting 30s
#   Recording complete.
#   Normalized to -6 dBFS
#   Output: ~/Desktop/dr-who-tidal.wav
ls -lh ~/Desktop/dr-who-tidal.wav
# Expected: ≥ 5 MB
```

---

### T7 — MP3 + sidecar JSON (½ day)

**Files:**

- Extend `src/strudel_gen/normalize.py` with `to_mp3(path, bitrate)`:

```python
def to_mp3(wav_path: Path, bitrate: int = 320) -> Path:
    mp3_path = wav_path.with_suffix(".mp3")
    cmd = [
        "ffmpeg", "-y", "-i", str(wav_path),
        "-b:a", f"{bitrate}k", "-codec:a", "libmp3lame",
        str(mp3_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return mp3_path
```

- Sidecar JSON writer in `render_orchestrator.py`:

```python
import json
sidecar = out_path.with_suffix(".json")
sidecar.write_text(json.dumps({
    "engine": "tidal",
    "source": str(pattern_path),
    "duration_s": duration,
    "cpm": _peek_cpm(pattern_path),
    "wav": str(out_path),
    "mp3": str(out_path.with_suffix(".mp3")) if mp3_bitrate else None,
    "render_time_iso": datetime.now(timezone.utc).isoformat(),
}, indent=2))
```

**Verification:**

```bash
strudel-gen render --engine tidal \
  --pattern src/patterns/dr-who-inspired.js \
  --duration 20 --out /tmp/dr.wav --mp3 320
ls -lh /tmp/dr.wav /tmp/dr.mp3 /tmp/dr.json
```

Expected: all three exist; WAV ~10 MB; MP3 ~1 MB; JSON parseable.

---

### T8 — Doctor + detection updates (¼ day)

**Files:** extend `src/strudel_gen/detect.py`.

```python
@dataclass(frozen=True)
class DetectionResult:
    sclang: str | None
    node: str | None
    pnpm: str | None
    strudel_dir: Path | None
    ghci: str | None              # NEW
    tidal_version: str | None     # NEW
    ffmpeg: str | None            # NEW
    os_name: str
    is_wsl: bool


def _find_ghci() -> str | None:
    return shutil.which("ghci")


def _find_tidal_version() -> str | None:
    ghci = _find_ghci()
    if not ghci:
        return None
    try:
        r = subprocess.run(
            ["ghc-pkg", "list", "tidal"],
            capture_output=True, text=True, timeout=10,
        )
        m = re.search(r"tidal-(\d+\.\d+\.\d+)", r.stdout)
        return m.group(1) if m else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
```

Then update `cli.py:doctor` to show two new rows.

**Verification:**

```bash
strudel-gen doctor --verbose
```

Expected: table now has rows for `ghci (Haskell)`, `tidal (Cabal pkg)`,
`ffmpeg`. Verbose mode includes install hints.

---

### T9 — Documentation pass (1 day)

- [ ] README.md: replace the leading diagram with §0 of this doc.
- [ ] `docs/quick-start.md`: rewrite as a two-path quick-start (sc-native fast path, Tidal full path).
- [ ] `docs/tidal-guide.md`: new file; BootTidal.hs internals, mini-notation cheatsheet, the §4 mapping table.
- [ ] CLAUDE.md: replace Strudel-REPL guidance with "write .js patterns; will be transpiled".
- [ ] AGENTS.md: add a "Transpile reviewer" role; the existing "Pattern author" role keeps writing Strudel.
- [ ] `scripts/bridge.sh`, `scripts/repl.sh`: move to `docs/legacy/` with a stub explaining the deprecation.

---

### T10 — E2E acceptance (½ day, human-in-the-loop)

```bash
# In a clean shell on macOS:
cd ~/devel/strudel-gen
source .venv/bin/activate
make doctor                        # all four+ rows ✓
make tidal-dr-who                  # ~3 min wall clock
afplay ~/Desktop/dr-who-tidal.wav  # listen
```

**Acceptance criteria:**

1. WAV exists and plays.
2. Phrases are intact (the Dr. Who motif is recognizable; no truncated notes).
3. No static / noise floor above −60 dBFS during the reverb tail.
4. MP3 + sidecar JSON also exist.

Open a "Phase 2 complete" PR with the HISTORY.md entry citing wall-clock times
and file sizes.

---

## 8. Pitfalls catalog (everything we hit today, with fixes)

These are all real, all encountered in this codebase during the Dr. Who
debugging session. Treat this as a pre-flight inspection.

### P1 — `sclang not found` even though SuperCollider is installed

- **Symptom:** `make doctor` shows `sclang ✗`. `which sclang` returns nothing.
- **Root cause:** On macOS, sclang lives inside the app bundle at
  `/Applications/SuperCollider.app/Contents/MacOS/sclang`, not on `PATH`.
- **Fix:** `detect.py:_find_sclang` already probes the bundle. If still
  failing, symlink: `mkdir -p ~/.local/bin && ln -sf /Applications/SuperCollider.app/Contents/MacOS/sclang ~/.local/bin/sclang`.
  Also: the `Makefile` exports `~/.local/bin` to PATH for sub-shells.

### P2 — sclang compiles only 82 classes ("Library has not been compiled successfully")

- **Symptom:** sclang prints `numClassDeps 0   gNumClasses 82  ERROR: Library has not been compiled successfully` and exits.
- **Root cause:** `Contents/MacOS/SCClassLibrary` is empty in the SC 3.14.1 macOS universal build; the real library is in `Contents/Resources/SCClassLibrary`.
- **Fix:** create `~/Library/Application Support/SuperCollider/sclang_conf.yaml`:

  ```yaml
  includePaths:
    - /Applications/SuperCollider.app/Contents/Resources/SCClassLibrary
  excludePaths:
    - /Applications/SuperCollider.app/Contents/MacOS/SCClassLibrary
  ```

  This is auto-loaded by sclang on every run.

### P3 — SC render times out after ~210 s

- **Symptom:** `TimeoutExpired` on a 30 s render. sclang process is alive but produces no output after "Welcome to SuperCollider".
- **Root cause:** a parse error in the .scd file → sclang silently aborts script execution but doesn't exit because async actions are pending.
- **Fix:** capture sclang stdout/stderr to a file and grep for `ERROR:`. Common parse error:
  `var` declaration after executable statements. SC 3.x requires ALL `var` declarations at the
  top of a block.

### P4 — `var` declaration after statement = silent hang

- **Symptom:** Sclang prints `ERROR: syntax error, unexpected VAR, expecting '}'` and your render hangs the full timeout.
- **Root cause:** mixing executable statements with `var` declarations in a block.
- **Fix:** ALL `var` declarations at the top of a block, before any other statement. See `src/supercollider/dr-who-render.scd` for the canonical layout.

### P5 — SuperDirt sample-loading dominates render time

- **Symptom:** A 30 s render takes 150+ s wall-clock.
- **Root cause:** SuperDirt's `~dirt.loadSoundFiles` reads 218 sample banks (~450 MB) into memory.
- **Fix:** For Tidal-path renders, this is intrinsic — accepted cost. For
  samples-free renders, use `--engine sc-native` with a `.scd` script that
  skips SuperDirt entirely (see `src/supercollider/dr-who-render.scd`).
- **Future:** T11 warm-daemon mode pays the cost once across many renders.

### P6 — Note synth holds forever at end of render

- **Symptom:** Last 5+ s of a render is a single sustained note.
- **Root cause:** A `gate=1` ADSR synth is in its sustain phase when its Routine is `.stop`'d — `gate` never goes to 0.
- **Fix:** Track the current synth in a shared variable; before stopping the routine, send `currentLead.set(\gate, 0)`. See `dr-who-render.scd` melody routine.

### P7 — Recording ends in silence (melody enters inter-phrase gap)

- **Symptom:** Last 5-10 s of audio has no melody, just bass+pad reverb tail.
- **Root cause:** The melody Routine is in an 8-beat gap (silence between phrases) when `duration.wait` completes.
- **Fix:** keep the melody running into the reverb tail (`5.0.wait` after `duration.wait` before stopping melRout); cap max gap at 4 beats.

### P8 — `ghci` prompt detection is brittle

- **Symptom:** Tests pass but the real ghci subprocess returns garbled prompt strings; `_READY_RE` never matches.
- **Root cause:** ghci's default prompt varies by version + shell-state.
- **Fix:** force the prompt off in BootTidal.hs: `:set prompt ""` and `:set prompt-cont ""`.
  Print a known sentinel string (`putStrLn "tidal-ready"`) at the end of the boot file and
  grep for that.

### P9 — Tidal pattern silent but `d1` "succeeded"

- **Symptom:** ghci prints no error; SuperDirt is running; no sound.
- **Root cause:** Tidal couldn't reach SuperDirt — wrong port, or SC server isn't booted yet, or `Conf` mismatch.
- **Fix:** verify the BootTidal.hs `superdirtTarget { oPort = 57120 }`. Verify SuperDirt
  actually printed `SuperDirt: listening on port 57120`. Try `d1 $ s "bd*4"` first — the
  simplest possible test.

### P10 — Strudel REPL can't be automated (the original blocker)

- **Symptom:** the `pnpm run osc` bridge prints "OSC bridge listening" but nothing plays.
- **Root cause:** Strudel needs a human in `http://localhost:4321` pressing Ctrl-Enter.
- **Fix:** this is the entire reason for Phase 2. Stop using Strudel-bridge for renders.

---

## 9. Risk register (unchanged from v1, with severity tags)

| # | Risk | Likelihood | Severity | Mitigation |
| --- | --- | --- | --- | --- |
| R1 | GHCi prompt brittleness across ghc versions | M | H | Force prompts off + sentinel string (see §5.1) |
| R2 | Tidal-package API changes | L | M | Pin `tidal-1.10.1`; BootTidal vendored at that version |
| R3 | `cabal install tidal` first-run takes 5–10 min | M | L | Document; cache in CI |
| R4 | Haskell install on Windows is finicky | H | M | Require WSL2 for Tidal on Windows; document |
| R5 | SuperDirt 120 s boot per render | H | M | Accepted for v2; warm-daemon in T11 |
| R6 | Transpiler scope creep | H | M | Strict whitelist (§4.1); validator rejects everything else |
| R7 | Same Tidal source produces different audio across SuperDirt versions | L | H | Pin SuperDirt quark to v1.7.2 (already done) |
| R8 | The `bridge.py` coverage drops as it's deprecated | M | L | Keep tests; mark `@pytest.mark.legacy`; remove only via a dedicated PR |
| R9 | LLM-authored Strudel produces unsupported constructs | H | L | Validator catches; clear error message; retry loop in skill body |

---

## 10. Deprecation plan

| Component | Status | When to remove |
| --- | --- | --- |
| `src/strudel_gen/bridge.py` | Deprecated | One full release after T6 ships |
| `scripts/bridge.sh`, `scripts/repl.sh` | Moved to `docs/legacy/` | T9 |
| CLI `--engine strudel-bridge` | Kept with warning | Until v3.0 |
| Phase-1 `make session` | Renamed `make session-strudel` (deprecated) | T9 |
| `M5/M6/M7/M8` in TODO.md | Marked SUPERSEDED | Done in TODO.md already |

---

## 11. Open decisions (need user input before T2.4)

- [ ] **Tidal version pin** → recommend `tidal-1.10.1`. CONFIRM.
- [ ] **GHC installer** → recommend `ghcup`. CONFIRM.
- [ ] **MP3 default bitrate** → recommend 320. CONFIRM.
- [ ] **Windows-native Tidal?** → recommend WSL2 only. CONFIRM.
- [ ] **Where do transpiled `.tidal` files live?** → recommend
      `src/tidal/<same-slug>.tidal` (committed; treated as cache).
      Alternative: keep them out of git, regenerate every render. CONFIRM.

---

## 12. State of the world (verified 2026-05-25)

> Everything in this section is ground truth, not aspiration. A
> less-capable model should treat the file paths, commands, and expected
> outputs as binding.

### 12.1 What works today

| Component | Location | Verification command |
|---|---|---|
| Strudel→Tidal transpiler (limited scope) | `src/strudel_gen/transpiler/` | `python -c "from strudel_gen.transpiler import transpile; print(transpile(open('src/patterns/dr-who-inspired.js').read()))"` (rejects `.size()` etc.) |
| TidalManager (ghci subprocess driver) | `src/strudel_gen/tidal_manager.py` | `python -c "from strudel_gen.tidal_manager import TidalManager; t=TidalManager(timeout=90); t.start(); t.eval('-- noop'); t.stop()"` |
| SC + SuperDirt headless boot | `~/Library/Application Support/SuperCollider/startup.scd` | `sclang /dev/null 2>&1 \| grep "SuperDirt: listening on port 57120"` (~120 s wall-clock) |
| End-to-end render orchestrator | `scripts/render_tidal.py` | smoke command in §13.2 |
| Hand-written 4-layer Dr. Who pattern | `src/tidal/dr-who-inspired.tidal` | renders to `~/Desktop/dr-who-mid20.wav` at mean −26 dBFS |

### 12.2 Smoke test — copy/paste, takes ~3 minutes

```bash
cd /path/to/strudel-gen && source .venv/bin/activate
rm -f /tmp/smoke.wav
python scripts/render_tidal.py src/tidal/sample.tidal 10 /tmp/smoke.wav
ffmpeg -i /tmp/smoke.wav -af volumedetect -f null /dev/null 2>&1 | grep mean_volume
# Expected output line:    [Parsed_volumedetect_0 @ ...] mean_volume: -3X.X dB
# Pass criterion:          mean_volume > -60 dB (anything < -70 dB is silence,
#                          go to §15 pitfall P10/P11)
```

### 12.3 What does NOT work today

- `strudel-gen render --engine tidal` as a CLI subcommand. Only the
  standalone `scripts/render_tidal.py` does. Open work — see TODO R2.
- The `ambient-render` skill firing from a Claude Code prompt. `SKILL.md`
  references the obsolete Strudel-bridge pipeline and isn't installed at
  `~/.claude/skills/ambient-render/`. Open work — see TODO R3.
- Real-world Strudel patterns. The transpiler whitelist (§4.1) is far
  too narrow; rejects `src/patterns/grimes-music4machines.js` at the
  lexer. Open work — see TODO R5.
- Process cleanup on `TidalManager.stop()`. The `ghc` grandchild
  survives, lock 12+ GB RAM until manually killed. Open work — TODO R1.
- `gm_*` GM samples, `samples({}, url)` remote loads. SuperDirt doesn't
  have these. Open work — TODO R8.

### 12.4 Where to look first when a render fails

1. Did `mean_volume < −70 dB`? → §15 pitfall P10 (synth doesn't exist) or P11 (vib param).
2. Did the script time out after 210 s? → §5.5 (silent-WAV / timing fix), shouldn't recur but check anyway.
3. Did sclang print "exception in GraphDef_Recv"? → §14 pitfall P12 (numWireBufs).
4. Did `ghc` show up at top of `top` after a failed render? → §14 pitfall P13 (zombie ghc).

---

## 13. SuperDirt synth registry (verified 2026-05-25)

> Captured by `SynthDescLib.global.synthDescs` dump after a fresh SuperDirt
> boot. Use ONLY synth names from §14.1 when writing `.tidal` patterns
> (or, after R4 lands, the validator will reject anything else).

### 13.1 The 28 registered super-synths

```text
super808           supersnare         superhammond
superchip          supersquare        superhex
superclap          superstatic        superhoover
supercomparator    supertron          superkick
superfm            supervibe          supermandolin
superfork          superwavemechanics supernoise
supergong          superzow           superpiano
supergrind                            superprimes
superhat                              superpwm
                                      superreese
                                      supersaw
                                      supersiren
```

### 13.2 Recommended synth-to-mood map

| Sonic role | Try this | Avoid (silently silent) |
|---|---|---|
| Sawtooth lead / bass | `supersaw` | — |
| Bowed strings, pads | `supersaw` + `# attack 1.5` + `# release 3` | — |
| Theremin-y sustained lead | `superhammond` (built-in Leslie tremolo, no `# vib` needed) | `supersine` ❌ does not exist |
| Plucked / koto / harp | `supermandolin` | — |
| Bell / gong / chime | `supergong` | — |
| Piano / mallet | `superpiano` | — |
| Sub-bass / FM | `superreese`, `superfm` | — |
| Smooth sweep / hoover | `superhoover` | `supertri` ❌ does not exist |
| Drum machine | `superkick`, `supersnare`, `superhat`, `superclap`, `super808` | — |
| Noise / FX | `supernoise`, `supersiren`, `superstatic`, `supercomparator` | — |
| Square-wave lead | `supersquare` | — |
| Chip-tune | `superchip`, `superzow` | — |

### 13.3 Parameter compatibility caveats

- **`# vib N # vibdepth N`** works for some synths (e.g. `supersaw`,
  `supersquare`) but **silently drops the entire event** on synths that
  don't have a `vib` SynthDef input. Test in isolation before relying.
- **`# attack`, `# release`, `# decay`** work globally via SuperDirt's
  event envelope.
- **`# room`, `# delay`, `# delaytime`, `# delayfeedback`** are
  global SuperDirt effects, not per-synth; always work.
- **`# lpf`, `# hpf`** work globally.

---

## 14. Pitfalls catalog (expanded with 2026-05-25 findings)

> Adds P10–P13 to the original P1–P9 in §8. Each entry is:
> symptom → root cause → exact fix.

### P10 — Pattern renders, file exists, but WAV is digital silence (−91 dBFS)

- **Symptom:** `mean_volume: -91.0 dB`, `max_volume: -91.0 dB`. File is the
  right size, ffmpeg can read it.
- **Root cause:** The `.tidal` pattern names a `s "<name>"` that is NOT a
  registered SuperDirt SynthDef. The events are dropped silently — SuperDirt
  does not fall back or warn. **The 28 registered names are in §13.1.**
- **Fix:** Replace the synth name with a §13.1 entry. Most common
  intuitive-but-wrong names: `supersine` → use `superhammond` or
  `superhoover`; `supertri` → use `superhammond` or `superpiano`.
- **Prevention:** After R4 lands, the transpiler validator rejects
  unknown `s "..."` values at transpile time.

### P11 — One layer of a multi-layer pattern is silent; others audible

- **Symptom:** Multi-layer render produces sound, but a specific orbit
  (e.g. the lead) is missing despite the synth name being correct.
- **Root cause:** The orbit's pattern decorates with `# vib N` or
  `# vibdepth N` and the chosen synth's SynthDef does not declare a
  `vib` input. SuperDirt silently drops events with parameters the
  synth can't bind.
- **Fix:** Either change synth to one that supports `vib` (e.g.
  `supersaw`, `supersquare`), or remove the `# vib` / `# vibdepth` from
  the chain.
- **Verification:** Isolate the layer (`d1 $ note "..." # s "<name>" #
  vib 5 # gain 1.0`) and render alone. If silent → vib incompatibility.

### P12 — Boot log shows "exception in GraphDef_Recv: exceeded number of interconnect buffers"

- **Symptom:** SC boot log emits this line; later layers fail to
  register (P10 cascades from this).
- **Root cause:** `s.options.numWireBufs` too low. SuperDirt's
  `default-synths.scd` defines synths in a single file; if the wire-buf
  budget exhausts partway, all subsequent synths silently fail to
  register.
- **Fix:** Set `s.options.numWireBufs = 1024` (or higher) in
  `~/Library/Application Support/SuperCollider/startup.scd` **before**
  `s.reboot { ... }`. Default 64 is not enough. Already deployed on
  the dev machine as of 2026-05-25.

### P13 — Zombie `ghc` process surviving render shutdown

- **Symptom:** `top` shows a `ghc` (not `ghci`, not `stack`) at 99% CPU
  + several GB RAM after `scripts/render_tidal.py` has exited.
- **Root cause:** `TidalManager.stop()` SIGTERMs the `stack ghci`
  wrapper, but `stack` spawns `ghc` as a grandchild. The grandchild is
  not reparented to init under SIGTERM and continues running.
- **Fix:**
  - **Immediate (manual):** `pkill -9 -f "ghc.*BootTidal"`.
  - **Permanent (TODO R1):** `TidalManager.stop()` walks the child tree
    via `psutil.Process(pid).children(recursive=True)` and SIGKILLs each
    descendant explicitly.

---

## 15. Skill installation contract (Stage 1 plumbing)

> Once R3 lands this section becomes verifiable.

The skill is "installed" when:

1. `skill/SKILL.md` contains the Phase-2 body from §2.1.
2. A symlink exists: `~/.claude/skills/ambient-render/SKILL.md` →
   `<repo>/skill/SKILL.md`.
3. Claude Code at session start logs `Loaded skill: ambient-render`
   (or shows it in the skill picker for matching prompts).
4. The prompt **"Make me 30 seconds of Dr. Who–inspired ambient music"**
   triggers the skill (this is the canonical acceptance test).
5. The skill body's `strudel-gen render --engine tidal ...` invocation
   works end-to-end (depends on R2).

### 15.1 Install command (after R3 ships)

```bash
make install-skill
# Equivalent to:
mkdir -p ~/.claude/skills/ambient-render
ln -sf "$(pwd)/skill/SKILL.md" ~/.claude/skills/ambient-render/SKILL.md
```

### 15.2 Verify install

```bash
ls -la ~/.claude/skills/ambient-render/
# Expected: SKILL.md -> /path/to/repo/skill/SKILL.md
```

Then open a fresh Claude Code session and paste:
"Make me 30 seconds of Dr. Who-inspired ambient music for a desktop background video."

Expected: skill fires, Claude writes a Strudel `.js`, runs
`strudel-gen render --engine tidal ...`, and reports the WAV path.

---

## 16. Glossary

For anyone (human or model) who hasn't lived this stack before.

| Term | Meaning |
| --- | --- |
| **OSC** | Open Sound Control — UDP message protocol for music software interop. Tidal sends, SuperDirt receives, port 57120. |
| **scsynth** | The SuperCollider audio server. Runs as a separate process; spawned by sclang. |
| **sclang** | The SuperCollider language interpreter. Compiles `.scd` files; spawns scsynth; talks OSC to it. |
| **SuperDirt** | An SC quark (library) that listens for OSC on 57120 and converts Tidal-style messages into SC synth events. Ships ~450 MB of samples. |
| **GHCi** | The Glasgow Haskell Compiler's interactive REPL. Runs Haskell code interactively; we drive it over stdin. |
| **Tidal Cycles** | A Haskell library for writing live-coded patterns. Sends OSC to SuperDirt. Strudel's parent project. |
| **Strudel** | The JavaScript port of Tidal Cycles. Runs in a browser. Cannot be automated. |
| **mini-notation** | The string syntax inside `s "bd sd"` or `note "c4 e4 g4"`. Identical between Strudel and Tidal. |
| **Orbit** | A logical bus in SuperDirt. `d1 / d2 / d3` map to orbits 0/1/2 in Tidal. Used to separate layers for mixing or multi-stem export. |
| **CPM / CPS** | Strudel uses Cycles Per Minute (`setcpm(120)`); Tidal uses Cycles Per Second (`setcps (120/60/4)`). One Tidal cycle = 4 beats by convention. |
| **`#`** | Tidal's parameter combinator. `note "c4" # s "sine"` means "this pattern is `note "c4"`, with parameter `s = "sine"`". |
| **`$`** | Haskell's function application operator. `f $ x` = `f(x)`. `d1 $ note "c"` means "set d1 to the pattern `note "c"`". |
| **`hush`** | Tidal command that silences all running patterns. |
| **`s.record`** | An SC method that writes the server output to a WAV file for a given duration. |
| **`s.waitForBoot`** | An SC idiom that runs a block of code once scsynth is ready. |
| **`Routine`** | An SC scheduled coroutine. Yields with `.wait`; runs on a clock (TempoClock for musical time, AppClock for wall time). |
| **`SynthDef`** | A reusable definition of an SC synthesis graph. Sent to scsynth once, then instantiated with `Synth(\name, [...])`. |
