#!/usr/bin/env bash
set -euo pipefail

QDW="${1:-.}"
PACK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$QDW"
test -f pyproject.toml
test -d src/qdw

mkdir -p tools/qdw-review
cp -R "$PACK/reference/src/qdw_review" tools/qdw-review/
cp "$PACK/integration/migrations/0003_review_system.sql" migrations/0003_review_system.sql.example
mkdir -p manifests/reviewers manifests/formulas prompts/review
cp "$PACK"/manifests/reviewers/*.json manifests/reviewers/
cp "$PACK"/manifests/formulas/*.json manifests/formulas/
cp "$PACK"/prompts/*.md prompts/review/

mkdir -p tests/review_adversarial
cp "$PACK"/overlay/tests/review_adversarial/*.py tests/review_adversarial/
cp "$PACK"/overlay/tests/review_adversarial/README.md tests/review_adversarial/

echo "Copied reviewer assets and adversarial regressions."
echo "DO NOT apply the 0003 example until current migration drift is repaired."
echo "Read $PACK/agent/MASTER_IMPLEMENTATION_PROMPT.md"
