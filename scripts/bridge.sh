#!/usr/bin/env bash
# Start the Strudel → SuperDirt OSC bridge. Leave running for the whole session.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=env.sh
source "$HERE/env.sh"

cd "$STRUDEL_DIR"
exec pnpm run osc
