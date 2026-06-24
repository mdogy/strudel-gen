#!/usr/bin/env bash
# End-to-end Tidal → WAV render
# Usage: ./scripts/render-tidal.sh [pattern.tidal] [duration] [output.wav]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
PATTERN="${1:-$REPO_DIR/src/tidal/sample.tidal}"
DURATION="${2:-30}"
OUT="${3:-/tmp/tidal-soundscape.wav}"

cd "$REPO_DIR"

echo "=== Tidal → WAV Render ==="
echo "Pattern:  $PATTERN"
echo "Duration: ${DURATION}s"
echo "Output:   $OUT"
echo ""

# Step 1: Start SC with SuperDirt (headless)
echo ">>> Booting SuperCollider + SuperDirt..."
.venv/bin/python -c "
from strudel_gen.sc import SCManager
from pathlib import Path
sc = SCManager(startup_file=Path('src/supercollider/headless.scd'), timeout=60)
sc.start()
print('SC_PID=' + str(sc._process.pid))
import json
print(json.dumps({'pid': sc._process.pid}))
# Keep running — user will kill manually
import time
while True:
    time.sleep(1)
" &
SC_PID=$!
sleep 15  # Wait for SC + SuperDirt

# Step 2: Start ghci with BootTidal.hs
echo ">>> Starting Tidal ghci..."
.venv/bin/python -c "
import sys
sys.path.insert(0, 'src')
import subprocess, time
proc = subprocess.Popen(
    ['stack', 'exec', '--', 'ghci', '-XOverloadedStrings', 'src/tidal/BootTidal.hs'],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    text=True, cwd='src/tidal'
)
import os, signal
print(f'GHCI_PID={proc.pid}')
sys.stdout.flush()
# Wait for ready
deadline = time.monotonic() + 30
while time.monotonic() < deadline:
    line = proc.stdout.readline()
    if not line: break
    print('[ghci]', line.rstrip())
    if 'Prelude' in line or 'BootTidal' in line:
        print('GHCI_READY')
        sys.stdout.flush()
        break
# Eval the pattern
pattern = open('$PATTERN').read()
proc.stdin.write(pattern + '\n')
proc.stdin.flush()
print('PATTERN_EVALD')
sys.stdout.flush()
# Wait for recording duration
import time
time.sleep($DURATION + 5)
# Hush
proc.stdin.write('hush\n')
proc.stdin.flush()
time.sleep(1)
os.kill(proc.pid, signal.SIGINT)
proc.wait()
print('GHCI_DONE')
sys.stdout.flush()
" &
GHCI_PID=$!
sleep 10  # Wait for ghci to boot and pattern to play

# Step 3: Record
echo ">>> Recording ${DURATION}s to $OUT..."
.venv/bin/python -c "
from strudel_gen.recorder import RecorderScript
import subprocess, sys
rec = RecorderScript(output_path='$OUT', duration=$DURATION + 5)
script = rec.generate()
result = subprocess.run(['sclang', '-'], input=script, capture_output=True, text=True, timeout=$DURATION + 30)
print('RECORDER_EXIT=' + str(result.returncode))
if result.stderr:
    print('[sclang stderr]', result.stderr[:500])
" || true

# Step 4: Normalize
echo ">>> Normalizing to -6 dBFS..."
.venv/bin/python -c "
from strudel_gen.normalize import normalize_to_dbfs
from pathlib import Path
normalize_to_dbfs(Path('$OUT'), target=-6.0)
print('NORMALIZED')
" || echo "Normalization skipped"

# Cleanup
echo ">>> Cleaning up..."
kill $GHCI_PID 2>/dev/null || true
kill $SC_PID 2>/dev/null || true

echo ""
echo "=== Done ==="
echo "Output: $OUT"
ls -lh "$OUT" 2>/dev/null || echo "Output not found"
