#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-worktrees}"
mkdir -p "$ROOT"
clone_one() {
  local name="$1" repo="$2" sha="$3"
  local dst="$ROOT/$name"
  if [[ ! -d "$dst/.git" ]]; then git clone "https://github.com/$repo.git" "$dst"; fi
  git -C "$dst" fetch --all --tags --prune
  git -C "$dst" checkout --detach "$sha"
  test "$(git -C "$dst" rev-parse HEAD)" = "$sha"
  test -z "$(git -C "$dst" status --porcelain)"
  printf '%-12s %s\n' "$name" "$sha"
}
clone_one qdw         prx0r/qdw         46920f2547e552b7f1c0e019169a350fe44cb4c1
clone_one qdw-forge   prx0r/qdw-forge   2037cdb93458278bdc4807be8e84111cce72fb10
clone_one qdw-sandbox prx0r/qdw-sandbox 5e4278c8eeed008bcf11deff288b19110379ece0
clone_one gitgoblin   prx0r/gitgoblin   c129f801b601af8e088d6fe908f01f769a62b0ee
clone_one dell        prx0r/dell        f29ed2a9621d307d301c628aa6f00de9d356d5ce
