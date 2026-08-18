#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-worktrees}"
mkdir -p "$ROOT"

clone_pin() {
  local name="$1" repo="$2" sha="$3"
  local dst="$ROOT/$name"
  if [[ ! -d "$dst/.git" ]]; then
    git clone "https://github.com/${repo}.git" "$dst"
  fi
  git -C "$dst" fetch --all --tags --prune
  git -C "$dst" checkout --detach "$sha"
  test "$(git -C "$dst" rev-parse HEAD)" = "$sha"
  echo "$name  $sha"
}

clone_pin qdw         prx0r/qdw         cccf6e3ca5f4704eb1c047965d3a3716dec8870b
clone_pin qdw-forge   prx0r/qdw-forge   2037cdb93458278bdc4807be8e84111cce72fb10
clone_pin qdw-sandbox prx0r/qdw-sandbox 5e4278c8eeed008bcf11deff288b19110379ece0
clone_pin gitgoblin   prx0r/gitgoblin   f7bf8963ee2600d9377a196ff0fd2f32ce5905b3
clone_pin dell        prx0r/dell        8aacd297fff0f0c7f48b36ac85ac415deaa7bd68

echo "Pinned worktrees ready under $ROOT"
