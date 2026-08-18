#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "${1:-worktrees}" && pwd)"
VROOT="${2:-.integration-venvs}"
mkdir -p "$VROOT"
VROOT="$(cd "$VROOT" && pwd)"

run_repo() {
  local name="$1" dir="$ROOT/$1" venv="$VROOT/$1"
  echo "===== $name ====="
  test -d "$dir"
  python -m venv "$venv"
  "$venv/bin/python" -m pip install -U pip wheel setuptools >/dev/null
  (
    cd "$dir"
    if [[ -f pyproject.toml ]]; then
      "$venv/bin/python" -m pip install -e ".[dev]" || "$venv/bin/python" -m pip install -e .
    elif [[ -f requirements.txt ]]; then
      "$venv/bin/python" -m pip install -r requirements.txt
      "$venv/bin/python" -m pip install pytest
    else
      "$venv/bin/python" -m pip install pytest
    fi
    "$venv/bin/python" -m compileall -q .
    if [[ -d tests ]]; then "$venv/bin/python" -m pytest -q; fi
  )
}

run_repo qdw
run_repo qdw-forge
run_repo qdw-sandbox
run_repo gitgoblin
run_repo dell
