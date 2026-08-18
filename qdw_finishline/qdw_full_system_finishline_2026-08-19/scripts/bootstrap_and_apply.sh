#!/usr/bin/env bash
set -euo pipefail
WORKTREES="${1:-worktrees}"
VROOT="${2:-.finishline-venvs}"

bash scripts/clone_reviewed_heads.sh "$WORKTREES"
python scripts/verify_reviewed_heads.py --root "$WORKTREES"
bash lab/scripts/create_envs.sh "$WORKTREES" "$VROOT" .
bash lab/scripts/run_reference.sh "$VROOT" evidence/reference
bash lab/scripts/run_native_suites.sh "$WORKTREES" "$VROOT" evidence/baseline-native
bash lab/scripts/capture_expected_red.sh "$WORKTREES" "$VROOT" evidence/expected-red

bash scripts/create_finishline_branches.sh "$WORKTREES"
python scripts/apply_overlays.py --pack-root . --worktrees "$WORKTREES"
python scripts/apply_overlays.py --pack-root . --worktrees "$WORKTREES" --apply
python scripts/apply_semantic_edits.py --root "$WORKTREES"

echo "Overlays applied. Review git diffs in all five repos before running final gates."
