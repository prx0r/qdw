#!/usr/bin/env bash
set -euo pipefail
WORKTREES="${1:-worktrees}"
VROOT="${2:-.finishline-venvs}"
PACK_ROOT="${3:-.}"
mkdir -p "$VROOT"
WORKTREES="$(cd "$WORKTREES" && pwd)"
VROOT="$(mkdir -p "$VROOT" && cd "$VROOT" && pwd)"
PACK_ROOT="$(cd "$PACK_ROOT" && pwd)"

create_repo_env() {
  local name="$1" dir="$WORKTREES/$1" v="$VROOT/$1"
  echo "=== env $name ==="
  python -m venv "$v"
  "$v/bin/python" -m pip install -U pip wheel setuptools >/dev/null
  if [[ -f "$dir/pyproject.toml" ]]; then
    "$v/bin/python" -m pip install -e "$dir[dev]" || "$v/bin/python" -m pip install -e "$dir"
  elif [[ -f "$dir/requirements.txt" ]]; then
    "$v/bin/python" -m pip install -r "$dir/requirements.txt"
    "$v/bin/python" -m pip install pytest
  else
    "$v/bin/python" -m pip install pytest
    "$v/bin/python" -m pip install -e "$dir"
  fi
}
for r in qdw qdw-forge qdw-sandbox gitgoblin dell; do create_repo_env "$r"; done

python -m venv "$VROOT/lab"
"$VROOT/lab/bin/python" -m pip install -U pip wheel setuptools >/dev/null
"$VROOT/lab/bin/python" -m pip install -e "$PACK_ROOT/lab"

python -m venv "$VROOT/reference"
"$VROOT/reference/bin/python" -m pip install -U pip wheel setuptools >/dev/null
"$VROOT/reference/bin/python" -m pip install -e "$PACK_ROOT/reference_finishline[dev]"

echo "$VROOT" > "$PACK_ROOT/.finishline-venv-root"
echo "Finish-line environments ready: $VROOT"
