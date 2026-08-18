#!/usr/bin/env bash
set -euo pipefail
WORKTREES="${1:-worktrees}"
VROOT="${2:-.finishline-venvs}"
STATE="${3:-.finishline-stack}"
EVIDENCE="${4:-evidence/final}"

mkdir -p "$EVIDENCE"
export QDW_WORKTREES="$(cd "$WORKTREES" && pwd)"

bash lab/scripts/run_native_suites.sh "$WORKTREES" "$VROOT" "$EVIDENCE/native"
bash lab/scripts/run_source_gate.sh "$WORKTREES" "$VROOT" "$EVIDENCE/source-gate"

python scripts/test_guard.py \
  "$WORKTREES/qdw/tests" "$WORKTREES/qdw-forge/tests" "$WORKTREES/qdw-sandbox/tests" \
  "$WORKTREES/gitgoblin/tests" "$WORKTREES/dell/tests" lab/tests reference_finishline/tests \
  >"$EVIDENCE/test-guard.json"

bash lab/scripts/start_finishline_stack.sh "$WORKTREES" "$VROOT" "$STATE" .
trap 'bash lab/scripts/stop_finishline_stack.sh "$STATE"' EXIT
bash lab/scripts/run_protocol_and_v11.sh "$VROOT" "$STATE" "$EVIDENCE/v11"
bash lab/scripts/run_restart_v11.sh "$WORKTREES" "$VROOT" "$STATE" \
  >"$EVIDENCE/restart.stdout" 2>"$EVIDENCE/restart.stderr"

python scripts/scan_qdw_secrets.py \
  --qdw-db "$STATE/run/qdw/data/qdw.db" \
  --evidence-root "$EVIDENCE" >"$EVIDENCE/secret-scan.json"

echo "Finish-line executable gates passed."
