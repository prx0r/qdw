#!/usr/bin/env bash
set -euo pipefail
VROOT="${1:-.finishline-venvs}"
STATE="${2:-.finishline-stack}"
OUT="${3:-evidence/v11}"
mkdir -p "$OUT"
source "$STATE/urls.env"
PY="$(cd "$VROOT" && pwd)/lab/bin/python"
"$PY" -m pytest lab/tests/contract -q >"$OUT/contracts.stdout" 2>"$OUT/contracts.stderr"
"$PY" -m pytest lab/tests/e2e -q >"$OUT/e2e.stdout" 2>"$OUT/e2e.stderr"
