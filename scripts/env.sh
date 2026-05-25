# shellcheck shell=bash
# Source this from other scripts. Edit STRUDEL_DIR to point at your local Strudel clone.

: "${STRUDEL_DIR:=$HOME/devel/strudel}"
: "${OSC_PORT:=57120}"
: "${OUT_DIR:=$HOME/Desktop}"

export STRUDEL_DIR OSC_PORT OUT_DIR
