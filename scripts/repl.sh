#!/usr/bin/env bash
# Start the local Strudel REPL at http://localhost:4321.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=env.sh
source "$HERE/env.sh"

cd "$STRUDEL_DIR"
exec pnpm run dev
