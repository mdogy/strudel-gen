#!/usr/bin/env bash
# Trigger a timed recording via sclang.
# Usage: record.sh <out.wav> <duration_seconds>
#
# Assumes SuperCollider is already running with the project startup file,
# and that a Strudel pattern is already evaluated and playing through SuperDirt.

set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=env.sh
source "$HERE/env.sh"

if [ "$#" -lt 2 ]; then
    echo "usage: $0 <out.wav> <duration_seconds>" >&2
    exit 64
fi

OUT="$1"
DUR="$2"

case "$OUT" in
    /*) ;;
    *)  OUT="$OUT_DIR/$OUT" ;;
esac

read -r -d '' SC_CODE <<EOF || true
(
s.recHeaderFormat = "WAV";
s.recSampleFormat = "int24";
s.recChannels = 2;
Routine({
    0.5.wait;
    s.record(path: "$OUT", duration: $DUR);
}).play;
)
EOF

# sclang runs headless and exits after evaluation. Recording continues
# in the already-running server; if you need the script to block until
# completion, use a long-running sclang session instead.
echo "Triggering recording to: $OUT  (duration ${DUR}s)"
echo "$SC_CODE" | sclang -d "$HERE"
