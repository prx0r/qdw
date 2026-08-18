#!/usr/bin/env bash
set -euo pipefail
VROOT="${1:-.finishline-venvs}"
OUT="${2:-evidence/reference}"
mkdir -p "$OUT"
PY="$(cd "$VROOT" && pwd)/reference/bin/python"
"$PY" -m compileall -q reference_finishline/src reference_finishline/tests \
  >"$OUT/compile.stdout" 2>"$OUT/compile.stderr"
"$PY" -m pytest reference_finishline/tests --collect-only -q \
  >"$OUT/collect.stdout" 2>"$OUT/collect.stderr"
"$PY" -m pytest reference_finishline/tests -q \
  >"$OUT/pytest.stdout" 2>"$OUT/pytest.stderr"
