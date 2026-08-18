#!/usr/bin/env bash
set -euo pipefail
WORKTREES="${1:-worktrees}"
VROOT="${2:-.finishline-venvs}"
STATE="${3:-.finishline-stack}"
PACK_ROOT="${4:-.}"

WORKTREES="$(cd "$WORKTREES" && pwd)"
VROOT="$(cd "$VROOT" && pwd)"
PACK_ROOT="$(cd "$PACK_ROOT" && pwd)"
mkdir -p "$STATE/logs" "$STATE/run/qdw" "$STATE/run/forge" "$STATE/run/dell" "$STATE/run/gitgoblin"
STATE="$(cd "$STATE" && pwd)"
: > "$STATE/pids"

start() {
  local name="$1" cwd="$2"; shift 2
  echo "starting $name"
  (
    cd "$cwd"
    exec "$@"
  ) >"$STATE/logs/$name.stdout" 2>"$STATE/logs/$name.stderr" &
  local pid=$!
  echo "$name $pid" >> "$STATE/pids"
}

# Deterministic external fixtures.
start echo "$PACK_ROOT/lab" \
  "$VROOT/lab/bin/python" -m uvicorn services.capability_echo:app --host 127.0.0.1 --port 8914
start forgejo "$PACK_ROOT/lab" \
  env FORGEJO_STUB_REPOS=61 "$VROOT/lab/bin/python" -m uvicorn services.forgejo_stub:app --host 127.0.0.1 --port 8915

# Real GitGoblin and Dell patched worktrees.
start gitgoblin "$WORKTREES/gitgoblin" \
  env GITGOBLIN_BUILD_SHA="$(git -C "$WORKTREES/gitgoblin" rev-parse HEAD)" \
  "$VROOT/gitgoblin/bin/python" -m uvicorn gitgoblin.api:app --host 127.0.0.1 --port 8912

start dell "$WORKTREES/dell" \
  "$VROOT/dell/bin/python" -m uvicorn app.api_canonical:app --host 127.0.0.1 --port 8913

# QDW runs from an isolated state cwd so data/qdw.db is not a repo-local test artifact.
start qdw "$STATE/run/qdw" \
  env QDW_GITGOBLIN_URL=http://127.0.0.1:8912 \
      QDW_DELL_URL=http://127.0.0.1:8913 \
      QDW_FORGE_URL=http://127.0.0.1:8911 \
      QDW_FORGE_CLIENT_KEY=lab-client-key \
      QDW_FEDERATION_LAB_MODE=1 \
  "$VROOT/qdw/bin/python" -m uvicorn qdw.interfaces.api:app --host 127.0.0.1 --port 8910

# Real Forge patched worktree, isolated database.
start forge "$STATE/run/forge" \
  env QDW_FORGE_DB="$STATE/run/forge/forge.db" \
      QDW_FORGE_LEASE_SECRET=finish-line-lab-secret-000000000000000000000000 \
      QDW_FORGE_CLIENT_KEYS_JSON='{"lab-client-key":"qdw-lab"}' \
      QDW_FORGE_ADMIN_TOKEN=lab-admin-token \
      QDW_FORGE_LAB_MODE=1 \
      QDW_FORGE_LAB_ECHO_URL=http://127.0.0.1:8914/invoke \
      QDW_CERTIFICATE_BASE_URL=http://127.0.0.1:8910 \
  "$VROOT/qdw-forge/bin/python" -m uvicorn qdw_forge.api:app --host 127.0.0.1 --port 8911

wait_health() {
  local name="$1" url="$2"
  for i in $(seq 1 80); do
    if "$VROOT/lab/bin/python" - "$url" <<'PY' >/dev/null 2>&1
import sys,httpx
r=httpx.get(sys.argv[1],timeout=1)
raise SystemExit(0 if r.status_code==200 else 1)
PY
    then echo "$name healthy"; return 0; fi
    sleep .25
  done
  echo "$name failed health: $url" >&2
  tail -100 "$STATE/logs/$name.stderr" >&2 || true
  return 1
}

wait_health echo http://127.0.0.1:8914/health
wait_health forgejo http://127.0.0.1:8915/health
wait_health gitgoblin http://127.0.0.1:8912/health
wait_health dell http://127.0.0.1:8913/health
wait_health qdw http://127.0.0.1:8910/health
wait_health forge http://127.0.0.1:8911/health

cat > "$STATE/urls.env" <<'EOF'
export QDW_URL=http://127.0.0.1:8910
export FORGE_URL=http://127.0.0.1:8911
export GITGOBLIN_URL=http://127.0.0.1:8912
export DELL_URL=http://127.0.0.1:8913
export FORGEJO_URL=http://127.0.0.1:8915
export QDW_FORGE_CLIENT_KEY=lab-client-key
export FORGE_ADMIN_TOKEN=lab-admin-token
EOF
echo "stack ready; source $STATE/urls.env"
