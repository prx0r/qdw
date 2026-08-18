#!/usr/bin/env bash
set -euo pipefail
WORKTREES="${1:-worktrees}"
VROOT="${2:-.finishline-venvs}"
STATE="${3:-.finishline-stack}"
WORKTREES="$(cd "$WORKTREES" && pwd)"
VROOT="$(cd "$VROOT" && pwd)"
STATE="$(cd "$STATE" && pwd)"

old="$(awk '$1=="qdw"{print $2}' "$STATE/pids" | tail -1)"
if [[ -n "$old" ]] && kill -0 "$old" 2>/dev/null; then kill "$old"; fi
sleep .3

(
 cd "$STATE/run/qdw"
 exec env QDW_GITGOBLIN_URL=http://127.0.0.1:8912 \
      QDW_DELL_URL=http://127.0.0.1:8913 \
      QDW_FORGE_URL=http://127.0.0.1:8911 \
      QDW_FORGE_CLIENT_KEY=lab-client-key \
      QDW_FEDERATION_LAB_MODE=1 \
 "$VROOT/qdw/bin/python" -m uvicorn qdw.interfaces.api:app --host 127.0.0.1 --port 8910
) >"$STATE/logs/qdw-restart.stdout" 2>"$STATE/logs/qdw-restart.stderr" &
new=$!

python - "$STATE/pids" "$new" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);new=sys.argv[2]
lines=[x for x in p.read_text().splitlines() if not x.startswith("qdw ")]
lines.append("qdw "+new)
p.write_text("\n".join(lines)+"\n")
PY
