#!/usr/bin/env bash
set -euo pipefail
STATE="${1:-.finishline-stack}"
if [[ ! -f "$STATE/pids" ]]; then exit 0; fi
tac "$STATE/pids" | while read -r name pid; do
  if kill -0 "$pid" 2>/dev/null; then
    echo "stopping $name ($pid)"
    kill "$pid" 2>/dev/null || true
  fi
done
sleep .5
tac "$STATE/pids" | while read -r _ pid; do
  kill -9 "$pid" 2>/dev/null || true
done
