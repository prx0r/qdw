#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-worktrees}"
for repo in qdw qdw-forge qdw-sandbox gitgoblin dell; do
  git -C "$ROOT/$repo" switch -c "qdw-finishline-2026-08-19/$repo"
done
