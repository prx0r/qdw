#!/usr/bin/env bash
set -euo pipefail
WORKTREES="${1:-worktrees}"
VROOT="${2:-.finishline-venvs}"
OUT="${3:-evidence/source-gate}"
mkdir -p "$OUT"
export QDW_WORKTREES="$(cd "$WORKTREES" && pwd)"
"$(cd "$VROOT" && pwd)/lab/bin/python" -m pytest lab/tests/source -q \
  >"$OUT/stdout.log" 2>"$OUT/stderr.log"
