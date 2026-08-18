#!/usr/bin/env bash
set -euo pipefail
WORKTREES="${1:-worktrees}"
VROOT="${2:-.finishline-venvs}"
EVIDENCE="${3:-evidence/native}"
mkdir -p "$EVIDENCE"
WORKTREES="$(cd "$WORKTREES" && pwd)"
VROOT="$(cd "$VROOT" && pwd)"
EVIDENCE="$(mkdir -p "$EVIDENCE" && cd "$EVIDENCE" && pwd)"

run_one() {
  local r="$1" dir="$WORKTREES/$1" py="$VROOT/$1/bin/python"
  echo "===== $r ====="
  set +e
  (cd "$dir" && "$py" -m compileall -q .) >"$EVIDENCE/$r.compile.stdout" 2>"$EVIDENCE/$r.compile.stderr"
  local crc=$?
  (cd "$dir" && "$py" -m pytest --collect-only -q) >"$EVIDENCE/$r.collect.stdout" 2>"$EVIDENCE/$r.collect.stderr"
  local krc=$?
  (cd "$dir" && "$py" -m pytest -q) >"$EVIDENCE/$r.pytest.stdout" 2>"$EVIDENCE/$r.pytest.stderr"
  local trc=$?
  set -e
  python - "$r" "$crc" "$krc" "$trc" "$dir" >"$EVIDENCE/$r.receipt.json" <<'PY'
import json,subprocess,sys
name,crc,krc,trc,repo=sys.argv[1:]
def git(*a):
    p=subprocess.run(["git",*a],cwd=repo,text=True,capture_output=True)
    return p.stdout.strip()
print(json.dumps({
 "repo":name,"sha":git("rev-parse","HEAD"),"dirty":bool(git("status","--porcelain")),
 "compile_exit":int(crc),"collect_exit":int(krc),"pytest_exit":int(trc)
},indent=2))
PY
  if (( crc != 0 || krc != 0 || trc != 0 )); then
    echo "$r FAILED; inspect $EVIDENCE/$r.*" >&2
    return 1
  fi
}
failed=0
for r in qdw qdw-forge qdw-sandbox gitgoblin dell; do run_one "$r" || failed=1; done
exit "$failed"
