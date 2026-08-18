#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-worktrees}"
STAMP="${2:-qdw-federation-integration}"

for repo in qdw qdw-forge qdw-sandbox gitgoblin dell; do
  d="$ROOT/$repo"
  git -C "$d" switch -c "$STAMP/$repo"
done
