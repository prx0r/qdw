#!/usr/bin/env bash
set -euo pipefail
WORKTREES="${1:-worktrees}"
VROOT="${2:-.finishline-venvs}"
OUT="${3:-evidence/expected-red}"
mkdir -p "$OUT"
export QDW_WORKTREES="$(cd "$WORKTREES" && pwd)"
set +e
"$(cd "$VROOT" && pwd)/lab/bin/python" -m pytest lab/tests/source -q \
  >"$OUT/stdout.log" 2>"$OUT/stderr.log"
rc=$?
set -e
printf '%s\n' "$rc" > "$OUT/exit_code"
if (( rc == 0 )); then
  echo "Expected current-head source gate to expose reviewed defects, but it was already green." >&2
  exit 1
fi
echo "Expected-red source gate captured (exit $rc)."
