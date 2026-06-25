#!/usr/bin/env python3
"""Thin wrapper around render_orchestrator.render_tidal().

Legacy entry point for backward compatibility. The canonical CLI invocation is:

    strudel-gen render --engine tidal --pattern <file>.tidal --duration N --out <file>.wav
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from strudel_gen.render_orchestrator import render_tidal  # noqa: E402

PATTERN = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("src/tidal/sample.tidal")
DURATION = float(sys.argv[2]) if len(sys.argv) > 2 else 15.0
OUT = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("/tmp/tidal-soundscape.wav")
OUT = OUT.expanduser().resolve()

OUT.parent.mkdir(parents=True, exist_ok=True)

print("=== Tidal → WAV (via render_orchestrator) ===")
print(f"Pattern:  {PATTERN}")
print(f"Duration: {DURATION}s")
print(f"Output:   {OUT}")

try:
    render_tidal(
        pattern_path=PATTERN,
        out_path=OUT,
        duration=DURATION,
        no_normalize=False,
    )
    print("\nDone!")
except Exception as e:
    print(f"\nERROR: {e}")
    sys.exit(1)
