#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-worktrees}"

echo "=== QDW federation ==="
(cd "$ROOT/qdw" && python -m pytest tests/federation -q)

echo "=== Forge federation contract ==="
(cd "$ROOT/qdw-forge" && python -m pytest tests/test_federation_contract.py -q)

echo "=== GitGoblin federation export ==="
(cd "$ROOT/gitgoblin" && python -m pytest tests/test_qdw_federation_export.py -q)

echo "=== Dell federation ==="
(cd "$ROOT/dell" && python -m pytest tests/test_federation_contract.py -q)

echo "=== Sandbox graduation ==="
(cd "$ROOT/qdw-sandbox" && python -m pytest tests/test_federation_graduation.py -q)
